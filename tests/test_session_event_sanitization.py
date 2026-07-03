import unittest

from vibeagent.session_event_sanitization import sanitize_session_event_payload


class SessionEventSanitizationTests(unittest.TestCase):
    def test_sanitizes_model_tool_call_input_bodies(self) -> None:
        content = "secret body\nsecond line\n"

        sanitized = sanitize_session_event_payload(
            "model",
            {
                "content": [
                    {"type": "text", "text": "I'll write it."},
                    {
                        "type": "tool_call",
                        "name": "write_file",
                        "input": {"path": "note.txt", "content": content},
                    },
                ]
            },
        )

        self.assertEqual(sanitized["content"][0]["text"], "I'll write it.")
        self.assertEqual(sanitized["content"][1]["input"]["path"], "note.txt")
        self.assertEqual(
            sanitized["content"][1]["input"]["content"],
            {"redacted": True, "type": "string", "chars": len(content), "lines": 2},
        )

    def test_sanitizes_nested_tool_call_input_bodies(self) -> None:
        sanitized = sanitize_session_event_payload(
            "tool_call",
            {
                "name": "write_files",
                "input": {
                    "files": [
                        {"path": "a.txt", "content": "alpha\n"},
                        {"path": "b.txt", "content": "beta\n"},
                    ]
                },
            },
        )

        files = sanitized["input"]["files"]
        self.assertEqual(files[0]["path"], "a.txt")
        self.assertEqual(files[0]["content"], {"redacted": True, "type": "string", "chars": 6, "lines": 1})
        self.assertEqual(files[1]["path"], "b.txt")
        self.assertEqual(files[1]["content"], {"redacted": True, "type": "string", "chars": 5, "lines": 1})

    def test_sanitizes_nested_tool_result_content_and_diffs(self) -> None:
        content = "private output\n"
        diff = "--- a/app.py\n+++ b/app.py\n@@\n-private\n+public\n"

        sanitized = sanitize_session_event_payload(
            "tool_result",
            {
                "result": {
                    "kind": "read_files",
                    "files": [{"path": "app.py", "content": content, "ok": True}],
                    "diff": diff,
                    "message": "Read files.",
                }
            },
        )

        result = sanitized["result"]
        self.assertEqual(result["kind"], "read_files")
        self.assertEqual(result["message"], "Read files.")
        self.assertEqual(result["files"][0]["path"], "app.py")
        self.assertEqual(
            result["files"][0]["content"],
            {"redacted": True, "type": "string", "chars": len(content), "lines": 1},
        )
        self.assertEqual(
            result["diff"],
            {"redacted": True, "type": "string", "chars": len(diff), "lines": 5},
        )

    def test_leaves_unknown_event_payload_unchanged(self) -> None:
        payload = {"content": "ordinary text", "diff": "not a tool result"}

        self.assertEqual(sanitize_session_event_payload("task", payload), payload)


if __name__ == "__main__":
    unittest.main()
