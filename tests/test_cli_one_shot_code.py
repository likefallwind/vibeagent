from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.agent_result import AgentResult
from vibeagent.cli_one_shot_code import run_one_shot_code
from vibeagent.cli_output_mode import CliOutputMode
from vibeagent.config import ExecutionConfig
from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.session_branching import read_session_branch_info
from vibeagent.session_names import read_session_name
from vibeagent.session_conversation import checkpoint_session_conversation
from vibeagent.types import ChatMessage
from vibeagent.structured_output import StructuredOutputResult
from vibeagent.workspace_core import create_local_workspace
from vibeagent.deferred_tool_state import DeferredToolState, write_deferred_tool_state


class CliOneShotCodeTests(unittest.TestCase):
    def test_resume_passes_persisted_deferred_tool_state_to_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-one-shot-deferred-") as base:
            root = Path(base)
            workspace = create_local_workspace(root, "run-old")
            state = DeferredToolState(
                (
                    {
                        "type": "tool_call",
                        "id": "tool-1",
                        "name": "read_file",
                        "input": {"path": "README.md"},
                    },
                ),
                (),
                0,
            )
            write_deferred_tool_state(workspace, state)
            calls: list[dict[str, object]] = []

            def run_agent(task, **kwargs):
                calls.append(kwargs)
                return AgentResult(True, "done", root, "run-old", 1, [], [])

            with (
                patch("vibeagent.cli_one_shot_code.emit_one_shot_code_payload"),
                patch(
                    "vibeagent.cli_one_shot_code.run_session_end_hooks"
                ) as session_end,
            ):
                exit_code, _ = run_one_shot_code(
                    "continue",
                    project_root=root,
                    execution_config=ExecutionConfig(),
                    provider_env={},
                    approval_policy="allow",
                    trust_project_permissions=True,
                    permission_overrides=None,
                    resolved_mcp_config_paths=(),
                    strict_mcp_config=False,
                    output_mode=CliOutputMode(format="json", machine=True, stream_json=False),
                    output_json=True,
                    print_mode=True,
                    elapsed_ms=1,
                    stream=None,
                    input_prior_context=None,
                    system_prompt=None,
                    append_system_prompt=None,
                    task_metadata=None,
                    resume_arg="run-old",
                    compact_arg=None,
                    auto_compact=False,
                    create_chat_client_func=lambda env: object(),
                    run_agent_func=run_agent,
                    get_resume_context_func=lambda *args, **kwargs: (
                        "run-old",
                        "prior context",
                        "ok",
                    ),
                    get_compact_context_func=lambda *args, **kwargs: (
                        None,
                        None,
                        "unused",
                    ),
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls[0]["deferred_tool_state"], state)
        self.assertTrue(calls[0]["defer_tool_calls"])
        self.assertTrue(calls[0]["close_async_hooks_on_finish"])
        self.assertEqual(session_end.call_args.args[1], "other")
        self.assertEqual(session_end.call_args.kwargs["approval_policy"], "allow")

    def test_run_one_shot_code_generates_structured_output_after_completed_workflow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-one-shot-structured-") as base:
            root = Path(base)
            session_dir = root / ".vibeagent" / "sessions" / "run-1"
            session_dir.mkdir(parents=True)
            calls: list[tuple[object, ...]] = []

            def generate(*args, **kwargs):
                calls.append(args)
                self.assertEqual(kwargs["session_dir"], session_dir)
                return StructuredOutputResult(value={"summary": "done"}, error=None, attempts=1)

            with patch("vibeagent.cli_one_shot_code.emit_one_shot_code_payload") as emit_payload:
                exit_code, _ = run_one_shot_code(
                    "fix tests",
                    project_root=root,
                    execution_config=ExecutionConfig(),
                    provider_env={},
                    approval_policy="allow",
                    trust_project_permissions=True,
                    permission_overrides=None,
                    resolved_mcp_config_paths=(),
                    strict_mcp_config=False,
                    output_mode=CliOutputMode(format="text", machine=False, stream_json=False),
                    output_json=False,
                    print_mode=True,
                    structured_output_schema={"type": "object"},
                    elapsed_ms=1,
                    stream=None,
                    input_prior_context=None,
                    system_prompt=None,
                    append_system_prompt=None,
                    task_metadata=None,
                    resume_arg=None,
                    compact_arg=None,
                    auto_compact=False,
                    create_chat_client_func=lambda env: "client",
                    run_agent_func=lambda *args, **kwargs: AgentResult(
                        True,
                        "done",
                        root,
                        "run-1",
                        1,
                        [],
                        [],
                        conversation=[ChatMessage(role="assistant", content="done")],
                    ),
                    get_resume_context_func=lambda *args, **kwargs: (None, None, "unused"),
                    get_compact_context_func=lambda *args, **kwargs: (None, None, "unused"),
                    generate_structured_output_func=generate,
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls[0][0], "client")
        self.assertEqual(calls[0][2], {"type": "object"})
        self.assertEqual(emit_payload.call_args.args[1]["structured_output"], {"summary": "done"})

    def test_run_one_shot_code_names_forced_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-one-shot-name-") as base:
            root = Path(base)
            calls: list[dict[str, object]] = []

            def run_agent(task, **kwargs):
                calls.append(kwargs)
                workspace = kwargs["workspace"]
                return AgentResult(True, "done", root, workspace.run_id, 1, [], [])

            with patch("vibeagent.cli_one_shot_code.emit_one_shot_code_payload") as emit_payload:
                exit_code, _ = run_one_shot_code(
                    "fix tests",
                    project_root=root,
                    execution_config=ExecutionConfig(),
                    provider_env={},
                    approval_policy="allow",
                    session_name="release-check",
                    trust_project_permissions=True,
                    permission_overrides=None,
                    resolved_mcp_config_paths=(),
                    strict_mcp_config=False,
                    output_mode=CliOutputMode(format="text", machine=False, stream_json=False),
                    output_json=False,
                    print_mode=False,
                    elapsed_ms=1,
                    stream=None,
                    input_prior_context=None,
                    system_prompt=None,
                    append_system_prompt=None,
                    task_metadata=None,
                    resume_arg=None,
                    compact_arg=None,
                    auto_compact=False,
                    create_chat_client_func=lambda env: object(),
                    run_agent_func=run_agent,
                    get_resume_context_func=lambda *args, **kwargs: (None, None, "unused"),
                    get_compact_context_func=lambda *args, **kwargs: (None, None, "unused"),
                )

            workspace = calls[0]["workspace"]
            self.assertEqual(exit_code, 0)
            self.assertEqual(read_session_name(root, workspace.run_id), "release-check")
            self.assertEqual(emit_payload.call_args.args[1]["sessionName"], "release-check")

    def test_run_one_shot_code_runs_agent_and_emits_result(self) -> None:
        project_root = Path("/tmp/vibeagent-code")
        provider_env: dict[str, str | None] = {"VIBEAGENT_PROVIDER": "minimax"}
        clients: list[dict[str, str | None]] = []
        agent_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        emitted: list[tuple[AgentResult, dict[str, object]]] = []

        def create_client(env: dict[str, str | None]) -> object:
            clients.append(env)
            return "client"

        def run_agent(*args, **kwargs) -> AgentResult:
            agent_calls.append((args, kwargs))
            return AgentResult(True, "done", project_root, "run-1", 1, [], [])

        def get_resume_context(run_id, root, **kwargs):
            return "run-0", "previous context", "ok"

        def get_compact_context(run_id, root, **kwargs):
            return None, None, "not used"

        with patch("vibeagent.cli_one_shot_code.emit_one_shot_code_payload") as emit_payload:
            emit_payload.side_effect = lambda result, payload, **kwargs: emitted.append((result, payload))
            exit_code, prior_context = run_one_shot_code(
                "fix tests",
                project_root=project_root,
                execution_config=ExecutionConfig(max_iterations=3, command_timeout_ms=100),
                provider_env=provider_env,
                approval_policy="allow",
                trust_project_permissions=True,
                permission_overrides=None,
                resolved_mcp_config_paths=(project_root / ".mcp.json",),
                strict_mcp_config=True,
                output_mode=CliOutputMode(format="text", machine=False, stream_json=False),
                output_json=False,
                print_mode=False,
                elapsed_ms=42,
                stream=None,
                input_prior_context="input context",
                system_prompt="system",
                append_system_prompt="append",
                append_subagent_system_prompt="Cite exact paths.",
                task_metadata={"source": "project_command"},
                resume_arg="run-0",
                compact_arg=None,
                auto_compact=True,
                resume_max_files=2,
                create_chat_client_func=create_client,
                run_agent_func=run_agent,
                get_resume_context_func=get_resume_context,
                get_compact_context_func=get_compact_context,
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(prior_context.context, "previous context")
        self.assertEqual(clients, [provider_env])
        self.assertEqual(agent_calls[0][0], ("fix tests",))
        self.assertEqual(agent_calls[0][1]["client"], "client")
        self.assertEqual(agent_calls[0][1]["prior_context"], "previous context\n\ninput context")
        self.assertEqual(agent_calls[0][1]["system_prompt"], "system")
        self.assertEqual(agent_calls[0][1]["append_system_prompt"], "append")
        self.assertEqual(
            agent_calls[0][1]["append_subagent_system_prompt"],
            "Cite exact paths.",
        )
        self.assertEqual(agent_calls[0][1]["task_metadata"], {"source": "project_command"})
        self.assertEqual(agent_calls[0][1]["mcp_config_paths"], (project_root / ".mcp.json",))
        self.assertTrue(agent_calls[0][1]["strict_mcp_config"])
        self.assertEqual(emitted[0][1]["kind"], "code")
        self.assertEqual(emitted[0][1]["message"], "done")

    def test_run_one_shot_code_returns_prior_context_error_without_agent_run(self) -> None:
        calls: list[str] = []

        def get_resume_context(run_id, root, **kwargs):
            calls.append("resume")
            return "missing", None, "No matching session."

        def get_compact_context(run_id, root, **kwargs):
            calls.append("compact")
            return None, None, "not used"

        exit_code, prior_context = run_one_shot_code(
            "fix tests",
            project_root=Path("/tmp/vibeagent-code"),
            execution_config=ExecutionConfig(),
            provider_env={},
            approval_policy="allow",
            trust_project_permissions=True,
            permission_overrides=None,
            resolved_mcp_config_paths=(),
            strict_mcp_config=False,
            output_mode=CliOutputMode(format="text", machine=False, stream_json=False),
            output_json=False,
            print_mode=False,
            elapsed_ms=42,
            stream=None,
            input_prior_context=None,
            system_prompt=None,
            append_system_prompt=None,
            task_metadata=None,
            resume_arg="missing",
            compact_arg=None,
            auto_compact=True,
            create_chat_client_func=lambda env: calls.append("client"),
            run_agent_func=lambda *args, **kwargs: calls.append("agent"),
            get_resume_context_func=get_resume_context,
            get_compact_context_func=get_compact_context,
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(prior_context.error, "No matching session.")
        self.assertEqual(calls, ["resume"])

    def test_run_one_shot_code_restores_additional_directories_from_resumed_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-one-shot-dirs-") as base:
            root = Path(base) / "project"
            shared = Path(base) / "shared"
            root.mkdir()
            shared.mkdir()
            append_session_event(
                root / ".vibeagent" / "sessions" / "run-old",
                "task",
                {"task": "inspect", "additional_directories": [str(shared.resolve())]},
            )
            checkpoint_session_conversation(
                create_local_workspace(root, "run-old"),
                [
                    ChatMessage(role="user", content="User task:\ninspect"),
                    ChatMessage(role="assistant", content="durable one-shot marker"),
                ],
                "inspect",
            )
            calls: list[dict[str, object]] = []

            def run_agent(task, **kwargs):
                calls.append(kwargs)
                return AgentResult(True, "done", root, kwargs["workspace"].run_id, 1, [], [])

            with patch("vibeagent.cli_one_shot_code.emit_one_shot_code_payload") as emit_payload:
                exit_code, _ = run_one_shot_code(
                    "continue",
                    project_root=root,
                    execution_config=ExecutionConfig(),
                    provider_env={},
                    approval_policy="allow",
                    trust_project_permissions=True,
                    permission_overrides=None,
                    resolved_mcp_config_paths=(),
                    strict_mcp_config=False,
                    output_mode=CliOutputMode(format="text", machine=False, stream_json=False),
                    output_json=False,
                    print_mode=False,
                    elapsed_ms=1,
                    stream=None,
                    input_prior_context=None,
                    system_prompt=None,
                    append_system_prompt=None,
                    task_metadata=None,
                    resume_arg="run-old",
                    compact_arg=None,
                    auto_compact=False,
                    create_chat_client_func=lambda env: object(),
                    run_agent_func=run_agent,
                    get_resume_context_func=lambda run_id, project_root, **kwargs: (
                        "run-old",
                        "prior context",
                        "ok",
                    ),
                    get_compact_context_func=lambda run_id, project_root, **kwargs: (None, None, "unused"),
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls[0]["workspace"].run_id, "run-old")
        self.assertNotIn("task_source_run_id", calls[0])
        self.assertEqual(calls[0]["additional_directories"], (shared.resolve(),))
        self.assertEqual(calls[0]["prior_messages"][-1].content, "durable one-shot marker")

    def test_run_one_shot_code_forks_resumed_session_into_forced_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-one-shot-branch-") as base:
            root = Path(base)
            source_dir = root / ".vibeagent" / "sessions" / "source-run"
            append_session_event(source_dir, "task", {"task": "source task"})
            source_events = source_dir.joinpath("events.jsonl").read_bytes()
            calls: list[dict[str, object]] = []

            def run_agent(task, **kwargs):
                calls.append(kwargs)
                workspace = kwargs["workspace"]
                return AgentResult(True, "done", root, workspace.run_id, 1, [], [])

            with patch("vibeagent.cli_one_shot_code.emit_one_shot_code_payload") as emit_payload:
                exit_code, _ = run_one_shot_code(
                    "try alternative",
                    project_root=root,
                    execution_config=ExecutionConfig(),
                    provider_env={},
                    approval_policy="allow",
                    trust_project_permissions=True,
                    permission_overrides=None,
                    resolved_mcp_config_paths=(),
                    strict_mcp_config=False,
                    output_mode=CliOutputMode(format="text", machine=False, stream_json=False),
                    output_json=False,
                    print_mode=False,
                    elapsed_ms=1,
                    stream=None,
                    input_prior_context=None,
                    system_prompt=None,
                    append_system_prompt=None,
                    task_metadata=None,
                    resume_arg="source-run",
                    compact_arg=None,
                    auto_compact=False,
                    fork_session=True,
                    create_chat_client_func=lambda env: object(),
                    run_agent_func=run_agent,
                    get_resume_context_func=lambda run_id, project_root, **kwargs: (
                        "source-run",
                        "source context",
                        "Loaded source.",
                    ),
                    get_compact_context_func=lambda run_id, project_root, **kwargs: (None, None, "unused"),
                )

            branch_workspace = calls[0]["workspace"]
            branch_info = read_session_branch_info(root, branch_workspace.run_id)

            self.assertEqual(exit_code, 0)
            self.assertEqual(calls[0]["task_source_run_id"], "source-run")
            self.assertEqual(branch_info.source_run_id, "source-run")  # type: ignore[union-attr]
            self.assertEqual(source_dir.joinpath("events.jsonl").read_bytes(), source_events)
            self.assertEqual(
                emit_payload.call_args.args[1]["sessionBranch"],
                {"runId": branch_workspace.run_id, "sourceRunId": "source-run"},
            )


if __name__ == "__main__":
    unittest.main()
