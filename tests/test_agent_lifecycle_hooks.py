from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from vibeagent.agent import run_agent
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks


class HookClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


def write_hooks(root: Path, hooks: dict[str, object]) -> None:
    path = root / ".vibeagent" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(hooks), encoding="utf-8")


def command_hook(command: str, matcher: str = ".*") -> dict[str, object]:
    return {"matcher": matcher, "hooks": [{"type": "command", "command": command, "timeout_ms": 10_000}]}


def approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


class LifecycleHookConfigTests(unittest.TestCase):
    def test_loads_lifecycle_events_and_marks_instruction_hooks_sequential(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            write_hooks(
                root,
                {
                    "SessionStart": [command_hook("python3 -V", "startup")],
                    "SubagentStart": [command_hook("python3 -V", "Explore")],
                    "SubagentStop": [command_hook("python3 -V", "Explore")],
                    "UserPromptSubmit": [command_hook("python3 -V")],
                    "Stop": [command_hook("python3 -V")],
                    "InstructionsLoaded": [command_hook("python3 -V", "session_start|nested_traversal")],
                },
            )

            config = read_project_hooks(create_run_workspace(root))

        self.assertIsNone(config.error)
        self.assertEqual(
            {hook.event for hook in config.hooks},
            {
                "SessionStart",
                "SubagentStart",
                "SubagentStop",
                "UserPromptSubmit",
                "Stop",
                "InstructionsLoaded",
            },
        )
        self.assertTrue(config.requires_sequential_tools)

    def test_context_only_lifecycle_hooks_keep_parallel_tools_enabled(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            write_hooks(
                root,
                {
                    "SessionStart": [command_hook("python3 -V", "startup")],
                    "SubagentStart": [command_hook("python3 -V", "Explore")],
                    "SubagentStop": [command_hook("python3 -V", "Explore")],
                    "UserPromptSubmit": [command_hook("python3 -V")],
                    "Stop": [command_hook("python3 -V")],
                },
            )

            config = read_project_hooks(create_run_workspace(root))

        self.assertTrue(config.enabled)
        self.assertFalse(config.requires_sequential_tools)

    def test_user_prompt_expansion_accepts_model_handlers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            write_hooks(
                root,
                {
                    "UserPromptExpansion": [
                        {
                            "matcher": "release",
                            "hooks": [
                                {"type": "prompt", "prompt": "check expansion"},
                                {"type": "agent", "prompt": "inspect expansion"},
                            ],
                        }
                    ]
                },
            )

            config = read_project_hooks(create_run_workspace(root))

        self.assertIsNone(config.error)
        self.assertEqual(
            [hook.handler_type for hook in config.hooks],
            ["prompt", "agent"],
        )
        self.assertFalse(config.requires_sequential_tools)


class AgentLifecycleHookTests(unittest.TestCase):
    def test_user_prompt_expansion_receives_command_fields_and_adds_context(self) -> None:
        command = (
            'python3 -c "import json,sys; d=json.load(sys.stdin); '
            "print(json.dumps({'additionalContext':json.dumps({k:d[k] for k in "
            "['expansion_type','command_name','command_args','command_source','prompt']},sort_keys=True)}))\""
        )
        client = HookClient([[{"type": "text", "text": "Expanded command processed."}]])
        metadata = {
            "source": "project_command",
            "name": "release",
            "path": ".claude/commands/release.md",
            "arguments": '"candidate one" --check',
        }
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            write_hooks(root, {"UserPromptExpansion": [command_hook(command, "^release$")]})

            result = run_agent(
                "Prepare candidate one",
                base_dir=root,
                client=client,
                max_iterations=1,
                approval_handler=approve,
                task_metadata=metadata,
            )

        initial_user = client.messages[0][1].content
        self.assertTrue(result.success)
        self.assertIsInstance(initial_user, str)
        context = str(initial_user).split("UserPromptExpansion hook context:\n", 1)[1]
        self.assertEqual(
            json.loads(context),
            {
                "command_args": '"candidate one" --check',
                "command_name": "release",
                "command_source": "project",
                "expansion_type": "slash_command",
                "prompt": '/release "candidate one" --check',
            },
        )

    def test_user_prompt_expansion_block_prevents_model_call(self) -> None:
        command = (
            'python3 -c "import json,sys; json.load(sys.stdin); '
            "print(json.dumps({'decision':'block','reason':'Command disabled by policy.'}))\""
        )
        client = HookClient([[{"type": "text", "text": "must not run"}]])
        metadata = {
            "source": "custom_skill",
            "name": "deploy",
            "path": ".claude/skills/deploy/SKILL.md",
            "arguments": "production",
        }
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            write_hooks(root, {"UserPromptExpansion": [command_hook(command, "deploy")]})

            result = run_agent(
                "Deploy production",
                base_dir=root,
                client=client,
                max_iterations=1,
                approval_handler=approve,
                task_metadata=metadata,
            )

        self.assertFalse(result.success)
        self.assertEqual(result.iterations, 0)
        self.assertEqual(result.message, "Command disabled by policy.")
        self.assertEqual(client.messages, [])

    def test_user_prompt_expansion_ignores_plain_prompts_and_nonmatching_commands(self) -> None:
        command = (
            'python3 -c "import json; '
            "print(json.dumps({'decision':'block','reason':'must not run'}))\""
        )
        for metadata in (
            None,
            {
                "source": "project_command",
                "name": "release",
                "path": ".claude/commands/release.md",
                "arguments": "v1",
            },
        ):
            with self.subTest(metadata=metadata), tempfile.TemporaryDirectory(
                prefix="vibeagent-hooks-"
            ) as base:
                root = Path(base)
                write_hooks(
                    root,
                    {"UserPromptExpansion": [command_hook(command, "^deploy$")]},
                )
                client = HookClient([[{"type": "text", "text": "normal response"}]])

                result = run_agent(
                    "normal task",
                    base_dir=root,
                    client=client,
                    max_iterations=1,
                    approval_handler=approve,
                    task_metadata=metadata,
                )

            self.assertTrue(result.success)
            self.assertEqual(len(client.messages), 1)

    def test_session_and_prompt_hooks_receive_json_stdin_and_add_context(self) -> None:
        session_command = (
            'true; python3 -c "import json,sys; d=json.load(sys.stdin); '
            "print('session-source=' + d['source'])\""
        )
        prompt_command = (
            'python3 -c "import json,sys; d=json.load(sys.stdin); '
            "print(json.dumps({'additionalContext': 'submitted=' + d['prompt']}))\""
        )
        client = HookClient([[{"type": "text", "text": "Processed with hook context."}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            write_hooks(
                root,
                {
                    "SessionStart": [command_hook(session_command, "startup")],
                    "UserPromptSubmit": [command_hook(prompt_command)],
                },
            )

            result = run_agent("Inspect context", base_dir=root, client=client, max_iterations=1, approval_handler=approve)

        initial_user = client.messages[0][1].content
        self.assertTrue(result.success)
        self.assertIsInstance(initial_user, str)
        self.assertIn("SessionStart hook context:\nsession-source=startup", initial_user)
        self.assertIn("UserPromptSubmit hook context:\nsubmitted=Inspect context", initial_user)

    def test_user_prompt_submit_exit_two_blocks_before_model_call(self) -> None:
        command = (
            'python3 -c "import json,sys; json.load(sys.stdin); '
            "print('Prompt rejected by policy.', file=sys.stderr); raise SystemExit(2)\""
        )
        client = HookClient([[{"type": "text", "text": "must not run"}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            write_hooks(root, {"UserPromptSubmit": [command_hook(command)]})

            result = run_agent("blocked task", base_dir=root, client=client, max_iterations=1, approval_handler=approve)

        self.assertFalse(result.success)
        self.assertEqual(result.iterations, 0)
        self.assertEqual(result.message, "Prompt rejected by policy.")
        self.assertEqual(client.messages, [])

    def test_stop_hook_can_continue_once_then_allow_completion(self) -> None:
        command = (
            'python3 -c "import json,sys; d=json.load(sys.stdin); '
            "print(json.dumps({'decision':'block','reason':'Run verification first.'}) "
            "if not d['stop_hook_active'] else '{}')\""
        )
        client = HookClient(
            [
                [{"type": "text", "text": "Initial answer."}],
                [{"type": "text", "text": "Verified answer."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            write_hooks(root, {"Stop": [command_hook(command)]})

            result = run_agent("finish carefully", base_dir=root, client=client, max_iterations=2, approval_handler=approve)

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Verified answer.")
        self.assertIn("Stop hook feedback:\nRun verification first.", client.messages[1][-1].content)

    def test_instructions_loaded_hooks_fire_for_startup_and_lazy_sources(self) -> None:
        command = (
            'python3 -c "import json,sys; d=json.load(sys.stdin); '
            "print(d['load_reason'] + ':' + d['file_path'] + ':' + str(d.get('trigger_file_path', '')))\""
        )
        client = HookClient(
            [
                [{"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": "pkg/module.py"}}],
                [{"type": "text", "text": "Read with scoped instructions."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            root.joinpath("CLAUDE.md").write_text("Root instruction.\n", encoding="utf-8")
            root.joinpath("pkg").mkdir()
            root.joinpath("pkg/CLAUDE.md").write_text("Package instruction.\n", encoding="utf-8")
            root.joinpath("pkg/module.py").write_text("VALUE = 1\n", encoding="utf-8")
            write_hooks(root, {"InstructionsLoaded": [command_hook(command, "session_start|nested_traversal")]})

            result = run_agent("read module", base_dir=root, client=client, max_iterations=2, approval_handler=approve)
            rows = [
                json.loads(line)
                for line in (root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        completed = [row for row in rows if row["type"] == "hook_completed" and row["event"] == "InstructionsLoaded"]
        stdout = [row["result"]["stdout"] for row in completed]
        self.assertTrue(result.success)
        self.assertEqual(len(completed), 2)
        self.assertTrue(any(value.startswith("session_start:") and value.rstrip().endswith("CLAUDE.md:") for value in stdout))
        self.assertTrue(any(value.startswith("nested_traversal:") and value.rstrip().endswith("pkg/module.py") for value in stdout))

    def test_instructions_loaded_hook_reports_import_parent(self) -> None:
        command = (
            'python3 -c "import json,sys; d=json.load(sys.stdin); '
            "print(d['load_reason'] + ':' + d['file_path'] + ':' + str(d.get('parent_file_path', '')))\""
        )
        client = HookClient([[{"type": "text", "text": "Ready."}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            root.joinpath("CLAUDE.md").write_text("@shared.md\n", encoding="utf-8")
            root.joinpath("shared.md").write_text("Shared instruction.\n", encoding="utf-8")
            write_hooks(root, {"InstructionsLoaded": [command_hook(command, "include")]})

            result = run_agent("load instructions", base_dir=root, client=client, max_iterations=1, approval_handler=approve)
            rows = [
                json.loads(line)
                for line in (root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        stdout = [
            row["result"]["stdout"].strip()
            for row in rows
            if row["type"] == "hook_completed" and row["event"] == "InstructionsLoaded"
        ]
        self.assertTrue(result.success)
        self.assertEqual(len(stdout), 1)
        self.assertIn("include:", stdout[0])
        self.assertIn("shared.md:", stdout[0])
        self.assertTrue(stdout[0].endswith("CLAUDE.md"))

    def test_batch_instruction_hooks_report_each_matching_trigger_file(self) -> None:
        command = (
            'python3 -c "import json,sys; d=json.load(sys.stdin); '
            "print(d['file_path'] + ':' + d['trigger_file_path'])\""
        )
        client = HookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "read-many",
                        "name": "read_files",
                        "input": {"paths": ["api/a.py", "web/a.py"]},
                    }
                ],
                [{"type": "text", "text": "Read both modules."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hooks-") as base:
            root = Path(base)
            for directory in ("api", "web"):
                root.joinpath(directory).mkdir()
                root.joinpath(directory, "CLAUDE.md").write_text(f"{directory} instruction.\n", encoding="utf-8")
                root.joinpath(directory, "a.py").write_text("VALUE = 1\n", encoding="utf-8")
            write_hooks(root, {"InstructionsLoaded": [command_hook(command, "nested_traversal")]})

            result = run_agent("read modules", base_dir=root, client=client, max_iterations=2, approval_handler=approve)
            rows = [
                json.loads(line)
                for line in (root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        stdout = [
            row["result"]["stdout"].strip()
            for row in rows
            if row["type"] == "hook_completed" and row["event"] == "InstructionsLoaded"
        ]
        self.assertTrue(result.success)
        self.assertEqual(len(stdout), 2)
        self.assertTrue(any("api/CLAUDE.md:" in value and value.endswith("api/a.py") for value in stdout))
        self.assertTrue(any("web/CLAUDE.md:" in value and value.endswith("web/a.py") for value in stdout))


if __name__ == "__main__":
    unittest.main()
