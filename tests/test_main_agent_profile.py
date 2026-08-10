from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent.agent import run_agent
from vibeagent.agent_run_setup import prepare_agent_run
from vibeagent.agent_tool_registry import activate_tools_from_observations
from vibeagent.cli import parse_args
from vibeagent.cli_permission_overrides import build_permission_overrides
from vibeagent.cli_one_shot_agent_kwargs import build_one_shot_agent_kwargs
from vibeagent.cli_validation import validate_cli_args
from vibeagent.config import ExecutionConfig
from vibeagent.types import AssistantResponse, ContentBlock, ToolSearchObservation
from vibeagent.workspace_core import create_run_workspace


def _write_agent(
    root: Path,
    name: str,
    body: str,
    *,
    mode: str = "code",
    tools: str | None = None,
    max_turns: int | None = None,
    memory: str | None = None,
    isolation: str | None = None,
) -> None:
    path = root / ".claude/agents" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = [
        f"name: {name}",
        f"description: {name} main profile",
        f"mode: {mode}",
    ]
    if tools is not None:
        metadata.append(f"tools: {tools}")
    if max_turns is not None:
        metadata.append(f"maxTurns: {max_turns}")
    if memory is not None:
        metadata.append(f"memory: {memory}")
    if isolation is not None:
        metadata.append(f"isolation: {isolation}")
    path.write_text(
        "---\n" + "\n".join(metadata) + f"\n---\n\n{body}\n",
        encoding="utf-8",
    )


class ScriptedClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.calls = 0
        self.messages: list[list[object]] = []
        self.tool_names: list[list[str]] = []

    def complete(self, messages, tools=None, **kwargs):
        self.messages.append(list(messages))
        self.tool_names.append([str(tool["name"]) for tool in tools or []])
        response = self.responses[self.calls]
        self.calls += 1
        return AssistantResponse(content=response, raw={"content": response})


class MainAgentProfileTests(unittest.TestCase):
    def test_cli_tool_ceiling_hides_and_blocks_unlisted_main_tools(self) -> None:
        client = ScriptedClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "Write",
                        "input": {"file_path": "blocked.txt", "content": "blocked\n"},
                    }
                ],
                [{"type": "text", "text": "The restricted review is complete."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-tools-") as base:
            root = Path(base)
            result = run_agent(
                "Review only",
                client,
                base_dir=root,
                tool_names=frozenset({"Read", "read_file"}),
                max_iterations=2,
                model_retries=0,
                approval_policy="allow",
            )
            events = (root / ".vibeagent/sessions" / result.run_id / "events.jsonl").read_text(
                encoding="utf-8"
            )

            self.assertFalse(root.joinpath("blocked.txt").exists())
        self.assertTrue(result.success)
        self.assertEqual(set(client.tool_names[0]), {"Read", "read_file"})
        self.assertEqual(result.observations[0].kind, "tool_error")
        self.assertIn("active tool restrictions", result.observations[0].message)
        self.assertIn('"type": "tool_restrictions_loaded"', events)

    def test_cli_tool_ceiling_intersects_selected_main_profile(self) -> None:
        client = ScriptedClient([[{"type": "text", "text": "Done."}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-profile-tools-") as base:
            root = Path(base)
            _write_agent(root, "reviewer", "REVIEW", tools="Read,Edit")

            result = run_agent(
                "Review",
                client,
                base_dir=root,
                agent="reviewer",
                tool_names=frozenset({"Read", "read_file"}),
                max_iterations=1,
                model_retries=0,
            )

        self.assertTrue(result.success)
        self.assertEqual(set(client.tool_names[0]), {"Read", "read_file"})

    def test_profile_prompt_allowlist_and_hidden_alias_are_enforced(self) -> None:
        client = ScriptedClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "Write",
                        "input": {"file_path": "blocked.txt", "content": "blocked\n"},
                    }
                ],
                [{"type": "text", "text": "The write was blocked."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-main-profile-") as base:
            root = Path(base)
            _write_agent(root, "reviewer", "MAIN_REVIEW_INSTRUCTION", tools="Read")

            result = run_agent(
                "Review only",
                client,
                base_dir=root,
                agent="reviewer",
                max_iterations=2,
                model_retries=0,
                approval_policy="allow",
            )

            self.assertFalse(root.joinpath("blocked.txt").exists())
        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "tool_error")
        self.assertIn("active tool restrictions", result.observations[0].message)
        self.assertEqual(set(client.tool_names[0]), {"Read", "finish", "read_file"})
        self.assertIn("MAIN_REVIEW_INSTRUCTION", str(client.messages[0][0].content))

    def test_explore_profile_hides_and_blocks_mutating_tools(self) -> None:
        client = ScriptedClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "Write",
                        "input": {"file_path": "blocked.txt", "content": "blocked\n"},
                    }
                ],
                [{"type": "text", "text": "Read-only review complete."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-main-explore-") as base:
            root = Path(base)
            _write_agent(root, "explorer", "EXPLORE_ONLY", mode="explore")

            result = run_agent(
                "Inspect only",
                client,
                base_dir=root,
                agent="explorer",
                max_iterations=2,
                model_retries=0,
                approval_policy="allow",
            )

            self.assertFalse(root.joinpath("blocked.txt").exists())
        self.assertTrue(result.success)
        self.assertNotIn("Write", client.tool_names[0])
        self.assertNotIn("Bash", client.tool_names[0])
        self.assertEqual(result.observations[0].kind, "tool_error")

    def test_unconditional_permission_deny_hides_alias_family_and_blocks_calls(self) -> None:
        client = ScriptedClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "Write",
                        "input": {"file_path": "blocked.txt", "content": "blocked\n"},
                    }
                ],
                [{"type": "text", "text": "The denied write was unavailable."}],
            ]
        )
        permissions = build_permission_overrides(
            parse_args(["--disallowed-tools", "Edit", "inspect"])
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-denied-tools-") as base:
            root = Path(base)
            result = run_agent(
                "Inspect without editing",
                client,
                base_dir=root,
                permission_overrides=permissions,
                max_iterations=2,
                model_retries=0,
                approval_policy="allow",
            )
            events = (root / ".vibeagent/sessions" / result.run_id / "events.jsonl").read_text(
                encoding="utf-8"
            )

            self.assertFalse(root.joinpath("blocked.txt").exists())
        advertised = set(client.tool_names[0])
        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "tool_error")
        self.assertNotIn("Edit", advertised)
        self.assertNotIn("Write", advertised)
        self.assertNotIn("edit_file", advertised)
        self.assertNotIn("write_file", advertised)
        self.assertIn('"disallowed_tools"', events)

    def test_profile_max_turns_caps_the_main_loop(self) -> None:
        client = ScriptedClient(
            [[{"type": "tool_call", "id": "read-1", "name": "Read", "input": {"file_path": "note.txt"}}]]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-main-turns-") as base:
            root = Path(base)
            root.joinpath("note.txt").write_text("note\n", encoding="utf-8")
            _write_agent(root, "bounded", "ONE_TURN_ONLY", tools="Read", max_turns=1)

            result = run_agent(
                "Read once",
                client,
                base_dir=root,
                agent="bounded",
                max_iterations=20,
                model_retries=0,
            )

        self.assertFalse(result.success)
        self.assertEqual(result.iterations, 1)
        self.assertIn("iteration limit (1)", result.message)
        self.assertEqual(client.calls, 1)

    def test_profile_memory_is_loaded_once_in_its_namespace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-main-memory-") as base:
            root = Path(base)
            _write_agent(
                root,
                "remembering",
                "MEMORY_AWARE_PROFILE",
                tools="Read",
                memory="project",
            )
            memory = root / ".claude/agent-memory/remembering/MEMORY.md"
            memory.parent.mkdir(parents=True)
            memory.write_text("UNIQUE_PROFILE_MEMORY\n", encoding="utf-8")
            setup = prepare_agent_run(
                "Recall conventions",
                base_dir=root,
                workspace=None,
                prior_context=None,
                approval_policy="ask",
                task_metadata=None,
                trust_project_permissions=False,
                permission_overrides=None,
                mcp_config_paths=(),
                strict_mcp_config=False,
                system_prompt=None,
                append_system_prompt=None,
                agent="remembering",
            )

        prompt = str(setup.messages)
        self.assertEqual(prompt.count("UNIQUE_PROFILE_MEMORY"), 1)
        self.assertEqual(setup.workspace.memory_namespace, "remembering")
        self.assertIn("Persistent agent memory is enabled", prompt)

    def test_missing_and_isolated_profiles_fail_before_model_request(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-main-invalid-") as base:
            root = Path(base)
            _write_agent(root, "isolated", "ISOLATED", isolation="worktree")
            client = ScriptedClient([])
            with self.assertRaisesRegex(ValueError, "not found"):
                run_agent("Inspect", client, base_dir=root, agent="missing")
            with self.assertRaisesRegex(ValueError, "--worktree"):
                run_agent("Inspect", client, base_dir=root, agent="isolated")

        self.assertEqual(client.calls, 0)

    def test_dynamic_tool_activation_cannot_escape_allowlist(self) -> None:
        observation = ToolSearchObservation(
            kind="tool_search",
            ok=True,
            query="dependencies",
            matches=[
                {"name": "python_dependencies"},
                {"name": "code_dependencies"},
            ],
            total=2,
            shown=2,
            truncated=False,
            category=None,
            approval_required=None,
            suggestions=[],
            message="Found tools.",
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-main-tools-") as base:
            workspace = create_run_workspace(base)
            active: set[str] = set()
            activated = activate_tools_from_observations(
                workspace,
                active,
                [observation],
                1,
                allowed_names=frozenset({"code_dependencies"}),
            )

        self.assertEqual(activated, ["code_dependencies"])
        self.assertEqual(active, {"code_dependencies"})

    def test_cli_parses_validates_and_forwards_agent(self) -> None:
        args = parse_args(["--agent", "reviewer", "inspect"])
        self.assertEqual(args.agent, "reviewer")
        self.assertIsNone(validate_cli_args(args))
        self.assertIsNotNone(
            validate_cli_args(parse_args(["--agent", "reviewer", "--chat", "hello"]))
        )
        kwargs = build_one_shot_agent_kwargs(
            client=object(),
            project_root=Path.cwd(),
            execution_config=ExecutionConfig(),
            approval_policy="deny",
            agent="reviewer",
            trust_project_permissions=False,
            permission_overrides=None,
            mcp_config_paths=(),
            strict_mcp_config=False,
            machine_output=True,
            stream_json=False,
            prior_context=None,
            system_prompt=None,
            append_system_prompt=None,
            task_metadata=None,
        )
        self.assertEqual(kwargs["agent"], "reviewer")


if __name__ == "__main__":
    unittest.main()
