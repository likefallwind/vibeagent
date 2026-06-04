import tempfile
import unittest
import json
from pathlib import Path

from vibeagent.agent import run_agent
from vibeagent.types import ApprovalDecision, ApprovalRequest, AssistantResponse, ChatMessage, ContentBlock


class MockClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.index = 0
        self.messages: list[list[ChatMessage]] = []

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> AssistantResponse:
        self.messages.append(list(messages))
        response = self.responses[self.index]
        self.index += 1
        return AssistantResponse(content=response, raw={"content": response})


def approve_all(_request: ApprovalRequest) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


def deny_all(_request: ApprovalRequest) -> ApprovalDecision:
    return ApprovalDecision(approved=False, message="denied")


class AgentTests(unittest.TestCase):
    def test_run_agent_allows_plain_text_response_without_tool_call(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient([[{"type": "text", "text": "这个问题不需要访问工作区。"}]])

            result = run_agent("解释一下递归", base_dir=Path(base), client=client, max_iterations=1)

        self.assertTrue(result.success)
        self.assertEqual(result.message, "这个问题不需要访问工作区。")
        self.assertEqual(result.observations, [])

    def test_run_agent_repairs_a_failing_script_and_finishes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "write_file", "input": {"path": "sum.py", "content": "print(total)"}}],
                    [{"type": "tool_call", "id": "2", "name": "run_command", "input": {"command": "python3 sum.py"}}],
                    [
                        {
                            "type": "tool_call",
                            "id": "3",
                            "name": "write_file",
                            "input": {"path": "sum.py", "content": "total = sum(range(1, 101))\nprint(total)\n"},
                        }
                    ],
                    [{"type": "tool_call", "id": "4", "name": "run_command", "input": {"command": "python3 sum.py"}}],
                    [
                        {
                            "type": "tool_call",
                            "id": "5",
                            "name": "finish",
                            "input": {"message": "Generated and ran sum.py successfully."},
                        }
                    ],
                ]
            )

            result = run_agent(
                "sum 1 to 100",
                base_dir=Path(base),
                client=client,
                max_iterations=5,
                approval_handler=approve_all,
            )
            event_log_exists = (Path(base) / ".vibeagent" / "sessions" / result.run_id / "events.jsonl").is_file()

        self.assertTrue(result.success)
        self.assertEqual(result.run_dir, Path(base).resolve())
        self.assertTrue(event_log_exists)
        command_observations = [item for item in result.observations if item.kind == "run_command"]
        self.assertEqual(len(command_observations), 2)
        self.assertNotEqual(command_observations[0].result.exit_code, 0)
        self.assertEqual(command_observations[1].result.exit_code, 0)
        self.assertEqual(command_observations[1].result.stdout.strip(), "5050")
        self.assertEqual(client.messages[1][-1].role, "user")
        self.assertEqual(client.messages[1][-1].content[0]["type"], "tool_result")
        self.assertEqual([step.status for step in result.steps], ["completed", "failed", "completed", "completed", "completed"])

    def test_run_agent_executes_multiple_tool_calls_in_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "write_file",
                            "input": {"path": "hello.txt", "content": "hello\n"},
                        },
                        {
                            "type": "tool_call",
                            "id": "2",
                            "name": "run_command",
                            "input": {"command": "cat hello.txt"},
                        },
                    ],
                    [
                        {
                            "type": "tool_call",
                            "id": "3",
                            "name": "finish",
                            "input": {"message": "Wrote and checked hello.txt."},
                        }
                    ],
                ]
            )

            result = run_agent(
                "write hello",
                base_dir=Path(base),
                client=client,
                max_iterations=2,
                approval_handler=approve_all,
            )

        self.assertTrue(result.success)
        self.assertEqual([item.kind for item in result.observations], ["write_file", "run_command", "finish"])
        self.assertEqual(result.observations[1].result.stdout, "hello\n")
        self.assertEqual([step.status for step in result.steps], ["completed", "completed", "completed"])

    def test_run_agent_returns_blocked_command_as_tool_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "run_command",
                            "input": {"command": "sudo reboot"},
                        }
                    ],
                    [
                        {
                            "type": "tool_call",
                            "id": "2",
                            "name": "finish",
                            "input": {"message": "Blocked the dangerous command."},
                        }
                    ],
                ]
            )

            result = run_agent(
                "try dangerous command",
                base_dir=Path(base),
                client=client,
                max_iterations=2,
                approval_handler=approve_all,
            )

        self.assertTrue(result.success)
        self.assertIsNone(result.observations[0].result.exit_code)
        self.assertIn("Command blocked", result.observations[0].result.stderr)
        self.assertIn("Command blocked", client.messages[1][-1].content[0]["content"])
        self.assertEqual(result.steps[0].status, "failed")

    def test_run_agent_guards_repeated_list_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "list_files", "input": {"path": "."}}],
                    [{"type": "tool_call", "id": "2", "name": "list_files", "input": {"path": "."}}],
                    [{"type": "tool_call", "id": "3", "name": "finish", "input": {"message": "Done."}}],
                ]
            )

            result = run_agent("list twice", base_dir=Path(base), client=client, max_iterations=3)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[1].kind, "list_files")
        self.assertIn("Already listed", result.observations[1].message)

    def test_run_agent_reports_malformed_tool_input_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "read_file", "input": {}}],
                    [{"type": "tool_call", "id": "2", "name": "finish", "input": {"message": "Handled error."}}],
                ]
            )

            result = run_agent("read a file", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "tool_error")
        self.assertIn("read_file action requires a string path", result.observations[0].message)
        self.assertIn("tool_error", client.messages[1][-1].content[0]["content"])

    def test_run_agent_allows_plain_text_final_answer_after_tool_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "write_file", "input": {"path": "note.txt", "content": "ok\n"}}],
                    [{"type": "text", "text": "Created note.txt."}],
                ]
            )

            result = run_agent(
                "create note",
                base_dir=Path(base),
                client=client,
                max_iterations=2,
                approval_handler=approve_all,
            )

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Created note.txt.")
        self.assertEqual([item.kind for item in result.observations], ["write_file"])
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_write_file_before_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "write_file", "input": {"path": "note.txt", "content": "ok\n"}}],
                    [
                        {
                            "type": "tool_call",
                            "id": "2",
                            "name": "finish",
                            "input": {"message": "Write was denied."},
                        }
                    ],
                ]
            )

            result = run_agent(
                "create note",
                base_dir=Path(base),
                client=client,
                max_iterations=2,
                approval_handler=deny_all,
            )
            events_path = Path(base) / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

        self.assertTrue(result.success)
        self.assertFalse(Path(base, "note.txt").exists())
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertIn("approval_denied", client.messages[1][-1].content[0]["content"])
        self.assertEqual(result.steps[0].status, "denied")
        self.assertIn("approval_requested", [event["type"] for event in events])
        self.assertIn("approval_decision", [event["type"] for event in events])
        self.assertIn("step_started", [event["type"] for event in events])
        self.assertIn("step_completed", [event["type"] for event in events])

    def test_run_agent_denies_write_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [[{"type": "tool_call", "id": "1", "name": "write_file", "input": {"path": "note.txt", "content": "ok\n"}}]]
            )

            result = run_agent("create note", base_dir=Path(base), client=client, max_iterations=1)

        self.assertFalse(result.success)
        self.assertFalse(Path(base, "note.txt").exists())
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.steps[0].status, "denied")
        self.assertIn("No approval handler", result.observations[0].message)


if __name__ == "__main__":
    unittest.main()
