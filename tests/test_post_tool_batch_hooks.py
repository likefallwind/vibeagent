from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from vibeagent.agent import run_agent
from vibeagent.actions import parse_tool_action
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks


class BatchClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, **_kwargs):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


def approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


def tool_call(call_id: str, path: str) -> ContentBlock:
    return {"type": "tool_call", "id": call_id, "name": "Read", "input": {"file_path": path}}


def write_hook(root: Path, command: str) -> None:
    path = root / ".vibeagent" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"PostToolBatch": [{"matcher": "never", "hooks": [{"type": "command", "command": command}]}]}),
        encoding="utf-8",
    )


class PostToolBatchHookTests(unittest.TestCase):
    def test_event_ignores_matcher_without_disabling_parallel_tools(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-batch-hook-") as base:
            root = Path(base)
            write_hook(root, "python3 -V")
            config = read_project_hooks(create_run_workspace(root))

        self.assertEqual(config.hooks[0].matcher, ".*")
        self.assertFalse(config.requires_sequential_tools)

    def test_batch_input_contains_all_serialized_results_and_injects_context(self) -> None:
        command = (
            'python3 -c "import json,sys; d=json.load(sys.stdin); c=d['"'"'tool_calls'"'"']; '
            "assert [x['tool_use_id'] for x in c]==['a','b']; "
            "assert all('content' in x['tool_response'] for x in c); "
            "print(json.dumps({'hookSpecificOutput':{'hookEventName':'PostToolBatch',"
            "'additionalContext':'Run the combined verification.'}}))\""
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-batch-hook-") as base:
            root = Path(base)
            root.joinpath("a.txt").write_text("a content\n", encoding="utf-8")
            root.joinpath("b.txt").write_text("b content\n", encoding="utf-8")
            write_hook(root, command)
            client = BatchClient(
                [[tool_call("a", "a.txt"), tool_call("b", "b.txt")], [{"type": "text", "text": "Verified."}]]
            )
            result = run_agent("Read both files", client, base_dir=root, max_iterations=2, approval_handler=approve)

        self.assertTrue(result.success)
        self.assertEqual(len(client.messages), 2)
        self.assertIn("Run the combined verification.", str(client.messages[1][-1].content))

    def test_block_stops_before_the_next_model_request(self) -> None:
        command = "python3 -c \"import json; print(json.dumps({'decision':'block','reason':'Batch rejected.'}))\""
        with tempfile.TemporaryDirectory(prefix="vibeagent-batch-hook-") as base:
            root = Path(base)
            root.joinpath("a.txt").write_text("a\n", encoding="utf-8")
            write_hook(root, command)
            client = BatchClient([[tool_call("a", "a.txt")]])
            result = run_agent("Read a file", client, base_dir=root, max_iterations=2, approval_handler=approve)

        self.assertFalse(result.success)
        self.assertEqual(len(client.messages), 1)
        self.assertIn("Batch rejected.", result.message)

    def test_subagent_receives_batch_context_before_its_next_turn(self) -> None:
        command = (
            "python3 -c \"import json; print(json.dumps({'additionalContext':"
            "'Subagent batch context.'}))\""
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-batch-hook-") as base:
            root = Path(base)
            root.joinpath("a.txt").write_text("a\n", encoding="utf-8")
            write_hook(root, command)
            workspace = create_run_workspace(root, "delegate-batch")
            client = BatchClient(
                [[tool_call("a", "a.txt")], [{"type": "text", "text": "Done."}]]
            )
            result = execute_delegate_task_action(
                workspace,
                parse_tool_action("Agent", {"prompt": "Read a.txt"}),
                client,
                parent_iteration=1,
                subagent_id="delegate-1-1",
                max_output_tokens=1024,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=approve,
                hooks=read_project_hooks(workspace),
            )

        self.assertTrue(result.ok)
        self.assertIn("Subagent batch context.", str(client.messages[1][-1].content))


if __name__ == "__main__":
    unittest.main()
