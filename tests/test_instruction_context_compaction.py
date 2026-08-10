from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from vibeagent.actions import parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks
from vibeagent.workspace_project_instructions import read_path_instruction_context


class RecordingClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


def read_payload(client: RecordingClient, call_index: int) -> dict[str, object]:
    block = client.messages[call_index][-1].content[0]
    return json.loads(block["content"])


def session_rows(root: Path, run_id: str) -> list[dict[str, object]]:
    path = root / ".vibeagent" / "sessions" / run_id / "events.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def write_nested_project(root: Path) -> None:
    package = root / "pkg"
    package.mkdir()
    package.joinpath("CLAUDE.md").write_text("Use package-specific validation.\n", encoding="utf-8")
    package.joinpath("large.py").write_text("VALUE = '" + "x" * 110_000 + "'\n", encoding="utf-8")
    package.joinpath("other.py").write_text("OTHER = 1\n", encoding="utf-8")


class InstructionContextCompactionTests(unittest.TestCase):
    def test_subagent_gets_nested_instruction_already_loaded_by_main_consumer(self) -> None:
        client = RecordingClient(
            [
                [{"type": "tool_call", "id": "read-child", "name": "read_file", "input": {"path": "pkg/other.py"}}],
                [{"type": "text", "text": "Inspected the package module."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-subagent-instructions-") as base:
            root = Path(base)
            write_nested_project(root)
            workspace = create_run_workspace(root, run_id="consumer-isolation")
            main_context = read_path_instruction_context(workspace, ["pkg/large.py"])
            hooks_path = root / ".vibeagent" / "hooks.json"
            hooks_path.parent.mkdir(exist_ok=True)
            hooks_path.write_text(
                json.dumps(
                    {
                        "InstructionsLoaded": [
                            {
                                "matcher": "nested_traversal",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": (
                                            'python3 -c "import json,sys; d=json.load(sys.stdin); '
                                            "print('subagent:' + d['load_reason'])\""
                                        ),
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            action = parse_tool_action("delegate_task", {"task": "Inspect pkg/other.py", "max_iterations": 2})

            result = execute_delegate_task_action(
                workspace,
                action,
                client,
                parent_iteration=1,
                subagent_id="delegate-1-1",
                max_output_tokens=2048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=lambda _request: ApprovalDecision(approved=True, message="approved"),
                hooks=read_project_hooks(workspace),
            )
            rows = session_rows(root, workspace.run_id)

        payload = read_payload(client, 1)
        self.assertTrue(result.ok)
        self.assertIn("Use package-specific validation.", main_context["text"])
        self.assertIn("Use package-specific validation.", payload["pathInstructions"]["text"])
        self.assertEqual(payload["hooks"][0]["stdout"].strip(), "subagent:nested_traversal")
        loaded = [row for row in rows if row["type"] == "subagent_instructions_loaded"]
        hook_events = [row for row in rows if row["type"] == "hook_completed" and row["event"] == "InstructionsLoaded"]
        self.assertEqual(len(loaded), 1)
        self.assertEqual(len(hook_events), 1)
        self.assertEqual(loaded[0]["subagent_id"], "delegate-1-1")

    def test_main_agent_reloads_nested_instruction_after_context_compaction(self) -> None:
        client = RecordingClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "read-large",
                        "name": "read_file",
                        "input": {"path": "pkg/large.py", "max_bytes": 120_000},
                    }
                ],
                [{"type": "tool_call", "id": "read-other", "name": "read_file", "input": {"path": "pkg/other.py"}}],
                [{"type": "text", "text": "Inspected both package modules."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-main-instruction-compact-") as base:
            root = Path(base)
            write_nested_project(root)

            result = run_agent("Inspect package files", base_dir=root, client=client, max_iterations=3)
            rows = session_rows(root, result.run_id)

        second_read = read_payload(client, 2)
        loaded = [row for row in rows if row["type"] == "instructions_loaded"]
        compaction = next(row for row in rows if row["type"] == "context_compacted")
        self.assertTrue(result.success)
        self.assertEqual(len(client.messages[1]), 2)
        self.assertIn("Use package-specific validation.", second_read["pathInstructions"]["text"])
        self.assertEqual(len(loaded), 2)
        self.assertEqual(compaction["path_instruction_sources_reset"], 1)
        self.assertIsNone(compaction["path_instruction_reset_error"])

    def test_subagent_reloads_nested_instruction_after_context_compaction(self) -> None:
        client = RecordingClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "read-large",
                        "name": "read_file",
                        "input": {"path": "pkg/large.py", "max_bytes": 120_000},
                    }
                ],
                [{"type": "tool_call", "id": "read-other", "name": "read_file", "input": {"path": "pkg/other.py"}}],
                [{"type": "text", "text": "Inspected both package modules."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-subagent-instruction-compact-") as base:
            root = Path(base)
            write_nested_project(root)
            workspace = create_run_workspace(root, run_id="subagent-compact")
            action = parse_tool_action("delegate_task", {"task": "Inspect package files", "max_iterations": 3})

            result = execute_delegate_task_action(
                workspace,
                action,
                client,
                parent_iteration=1,
                subagent_id="delegate-1-1",
                max_output_tokens=2048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
            )
            rows = session_rows(root, workspace.run_id)

        second_read = read_payload(client, 2)
        loaded = [row for row in rows if row["type"] == "subagent_instructions_loaded"]
        compaction = next(row for row in rows if row["type"] == "subagent_context_compacted")
        self.assertTrue(result.ok)
        self.assertEqual(len(client.messages[1]), 2)
        self.assertIn("Use package-specific validation.", second_read["pathInstructions"]["text"])
        self.assertEqual(len(loaded), 2)
        self.assertEqual(compaction["path_instruction_sources_reset"], 1)
        self.assertIsNone(compaction["path_instruction_reset_error"])


if __name__ == "__main__":
    unittest.main()
