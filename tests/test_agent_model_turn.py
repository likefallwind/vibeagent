from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_model_turn import handle_no_tool_call_response, record_model_turn
from vibeagent.types import AssistantResponse, ChatMessage, ContentBlock, ModelUsage
from vibeagent.workspace import create_run_workspace


class AgentModelTurnTests(unittest.TestCase):
    def test_record_model_turn_appends_message_event_usage_and_tool_calls(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-model-turn-") as base:
            workspace = create_run_workspace(Path(base))
            messages: list[ChatMessage] = []
            response = AssistantResponse(
                content=[
                    {"type": "text", "text": "Inspecting."},
                    {"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": "app.py"}},
                ],
                raw={},
                usage=ModelUsage(input_tokens=10, output_tokens=5, total_tokens=15),
            )
            turn = record_model_turn(workspace, messages, response, 3)
            event = json.loads((workspace.session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(messages, [ChatMessage(role="assistant", content=response.content)])
        self.assertEqual(turn.assistant_content, response.content)
        self.assertEqual([call["name"] for call in turn.tool_calls], ["read_file"])
        self.assertEqual(event["type"], "model")
        self.assertEqual(event["iteration"], 3)
        self.assertEqual(event["usage"]["total_tokens"], 15)

    def test_handle_no_tool_call_finishes_plain_text_response(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-model-turn-") as base:
            workspace = create_run_workspace(Path(base))
            finished: list[tuple[bool, str, int]] = []

            result = handle_no_tool_call_response(
                workspace,
                [],
                [{"type": "text", "text": "Done."}],
                iteration=2,
                max_iterations=5,
                observations=[],
                steps=[],
                plan=[],
                command_timeout_ms=1000,
                logger=None,
                completion_blocked_feedback_if_needed_func=lambda *args: None,
                finish_agent_run_func=lambda _workspace, success, message, iterations, *_args: finished.append(
                    (success, message, iterations)
                )
                or "finished",
            )

        self.assertTrue(result.handled)
        self.assertFalse(result.should_continue)
        self.assertEqual(result.result, "finished")
        self.assertEqual(finished, [(True, "Done.", 2)])

    def test_handle_no_tool_call_appends_blocker_feedback_and_continues(self) -> None:
        messages: list[ChatMessage] = []
        with tempfile.TemporaryDirectory(prefix="vibeagent-model-turn-") as base:
            workspace = create_run_workspace(Path(base))
            result = handle_no_tool_call_response(
                workspace,
                messages,
                [{"type": "text", "text": "Done too early."}],
                iteration=1,
                max_iterations=5,
                observations=[],
                steps=[],
                plan=[],
                command_timeout_ms=1000,
                logger=None,
                completion_blocked_feedback_if_needed_func=lambda *args: "Run verification first.",
                finish_agent_run_func=lambda *_args: "unexpected",
            )

        self.assertTrue(result.handled)
        self.assertTrue(result.should_continue)
        self.assertIsNone(result.result)
        self.assertEqual(messages, [ChatMessage(role="user", content="Run verification first.")])

    def test_handle_no_tool_call_fails_empty_response(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-model-turn-") as base:
            workspace = create_run_workspace(Path(base))
            finished: list[tuple[bool, str]] = []
            result = handle_no_tool_call_response(
                workspace,
                [],
                [{"type": "text", "text": "   "}],
                iteration=4,
                max_iterations=5,
                observations=[],
                steps=[],
                plan=[],
                command_timeout_ms=1000,
                logger=None,
                completion_blocked_feedback_if_needed_func=lambda *args: None,
                finish_agent_run_func=lambda _workspace, success, message, *_args: finished.append((success, message))
                or "failed",
            )

        self.assertEqual(result.result, "failed")
        self.assertEqual(finished, [(False, "Model response did not include text or a tool call.")])


if __name__ == "__main__":
    unittest.main()
