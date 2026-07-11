import json
import unittest

from vibeagent.cli_input_format import TaskInputFormatError, resolve_stream_json_task_text


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

    def test_stream_json_ignores_assistant_and_system_direct_records(self) -> None:
        raw = "\n".join(
            [
                json.dumps({"type": "assistant", "text": "old reply"}),
                json.dumps({"type": "system", "text": "old instruction"}),
                json.dumps({"type": "user", "text": "continue the change"}),
            ]
        )

        self.assertEqual(resolve_stream_json_task_text(raw), "continue the change")

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

    def test_stream_json_parse_error_reports_line(self) -> None:
        with self.assertRaisesRegex(TaskInputFormatError, "line 2"):
            resolve_stream_json_task_text("{}\n{not json}\n")


if __name__ == "__main__":
    unittest.main()
