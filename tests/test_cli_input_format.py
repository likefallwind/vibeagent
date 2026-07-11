import json
import unittest

from vibeagent.cli_input_format import TaskInputFormatError, resolve_stream_json_task_input, resolve_stream_json_task_text


class CliInputFormatTests(unittest.TestCase):
    def test_stream_json_extracts_user_messages_from_messages_array(self) -> None:
        raw = "\n".join(
            [
                json.dumps(
                    {
                        "messages": [
                            {"role": "system", "content": "You are terse."},
                            {"role": "assistant", "content": "Previous answer."},
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "fix the failing test"},
                                    {"type": "image", "source": "ignored"},
                                    "then summarize",
                                ],
                            },
                        ]
                    }
                ),
                json.dumps({"role": "user", "content": "run focused checks"}),
            ]
        )

        self.assertEqual(
            resolve_stream_json_task_text(raw),
            "fix the failing test\nthen summarize\nrun focused checks",
        )
        parsed = resolve_stream_json_task_input(raw)
        self.assertEqual(parsed.task, "fix the failing test\nthen summarize\nrun focused checks")
        self.assertEqual(parsed.system_prompt, "You are terse.")
        self.assertEqual(parsed.assistant_context, "Previous answer.")
        self.assertIsNone(parsed.session_id)

    def test_stream_json_ignores_assistant_and_system_direct_records(self) -> None:
        raw = "\n".join(
            [
                json.dumps({"type": "assistant", "text": "old reply"}),
                json.dumps({"type": "system", "text": "old instruction"}),
                json.dumps({"type": "user", "text": "continue the change"}),
            ]
        )

        self.assertEqual(resolve_stream_json_task_text(raw), "continue the change")
        parsed = resolve_stream_json_task_input(raw)
        self.assertEqual(parsed.task, "continue the change")
        self.assertEqual(parsed.system_prompt, "old instruction")
        self.assertEqual(parsed.assistant_context, "old reply")

    def test_stream_json_extracts_session_id_from_records(self) -> None:
        raw = "\n".join(
            [
                json.dumps({"session_id": "run-1", "type": "system", "text": "Use context."}),
                json.dumps({"sessionId": "run-2", "type": "user", "text": "continue"}),
            ]
        )

        parsed = resolve_stream_json_task_input(raw)

        self.assertEqual(parsed.task, "continue")
        self.assertEqual(parsed.session_id, "run-1")

    def test_stream_json_supports_wrapped_role_message(self) -> None:
        raw = json.dumps(
            {
                "type": "message",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "inspect repo"}],
                },
            }
        )

        self.assertEqual(resolve_stream_json_task_text(raw), "inspect repo")

    def test_stream_json_keeps_legacy_text_records_without_roles(self) -> None:
        raw = "\n".join(
            [
                json.dumps({"text": "legacy direct"}),
                json.dumps({"message": {"content": [{"type": "text", "text": "legacy message"}]}}),
            ]
        )

        self.assertEqual(resolve_stream_json_task_text(raw), "legacy direct\nlegacy message")

    def test_stream_json_accepts_prompt_and_input_text_fields(self) -> None:
        raw = "\n".join(
            [
                json.dumps({"prompt": "inspect changed files"}),
                json.dumps({"type": "user", "input": "run focused tests"}),
                json.dumps({"role": "system", "prompt": "Prefer concise output."}),
                json.dumps({"role": "assistant", "input": "I found tests/test_app.py."}),
            ]
        )

        parsed = resolve_stream_json_task_input(raw)

        self.assertEqual(parsed.task, "inspect changed files\nrun focused tests")
        self.assertEqual(parsed.system_prompt, "Prefer concise output.")
        self.assertEqual(parsed.assistant_context, "I found tests/test_app.py.")

    def test_stream_json_accepts_nested_prompt_and_input_message_fields(self) -> None:
        raw = "\n".join(
            [
                json.dumps({"message": {"role": "user", "prompt": "fix lint"}}),
                json.dumps({"message": {"role": "user", "input": "then summarize"}}),
            ]
        )

        self.assertEqual(resolve_stream_json_task_text(raw), "fix lint\nthen summarize")

    def test_stream_json_parse_error_reports_line(self) -> None:
        with self.assertRaisesRegex(TaskInputFormatError, "line 2"):
            resolve_stream_json_task_text("{}\n{not json}\n")


if __name__ == "__main__":
    unittest.main()
