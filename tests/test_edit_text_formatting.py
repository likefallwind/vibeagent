import unittest

from vibeagent import edit_commands, edit_text_commands, edit_text_formatting


class EditTextFormattingTests(unittest.TestCase):
    def test_edit_text_commands_reexports_formatting_helpers(self) -> None:
        self.assertIs(edit_text_commands.format_line_edit_observation, edit_text_formatting.format_line_edit_observation)
        self.assertIs(edit_text_commands.format_line_edit_report_text, edit_text_formatting.format_line_edit_report_text)
        self.assertIs(edit_text_commands.serialize_line_edit_report, edit_text_formatting.serialize_line_edit_report)
        self.assertIs(edit_text_commands.format_write_files_observation, edit_text_formatting.format_write_files_observation)
        self.assertIs(edit_text_commands.format_write_files_report_text, edit_text_formatting.format_write_files_report_text)
        self.assertIs(edit_text_commands.serialize_write_files_report, edit_text_formatting.serialize_write_files_report)

    def test_edit_commands_reexports_text_formatting_helpers(self) -> None:
        self.assertIs(edit_commands.format_line_edit_report_text, edit_text_formatting.format_line_edit_report_text)
        self.assertIs(edit_commands.format_write_files_report_text, edit_text_formatting.format_write_files_report_text)
        self.assertIs(edit_commands.serialize_write_files_report, edit_text_formatting.serialize_write_files_report)

    def test_line_edit_formatting_preserves_usage_and_diff_output(self) -> None:
        usage = {"message": "Usage: /write <path> <text>\nError: missing path"}
        report = {
            "projectRoot": "/tmp/project",
            "ok": True,
            "path": "app.py",
            "message": "Updated app.py.",
            "diff": {"text": "--- app.py\n+++ app.py\n@@\n-old\n+new"},
            "startLine": 1,
            "endLine": 1,
        }

        self.assertEqual(
            edit_text_formatting.format_line_edit_report_text("Write:", usage),
            "Usage: /write <path> <text>\nError: missing path",
        )
        self.assertEqual(
            edit_text_formatting.format_line_edit_report_text("Replace lines:", report),
            "\n".join(
                [
                    "Replace lines:",
                    "  projectRoot: /tmp/project",
                    "  ok: yes",
                    "  path: app.py",
                    "  range: 1-1",
                    "  message: Updated app.py.",
                    "  diff:",
                    "    --- app.py",
                    "    +++ app.py",
                    "    @@",
                    "    -old",
                    "    +new",
                ]
            ),
        )

    def test_write_files_formatting_preserves_item_diff_output(self) -> None:
        report = {
            "projectRoot": "/tmp/project",
            "ok": False,
            "files": {
                "total": 1,
                "items": [
                    {
                        "path": "app.py",
                        "ok": False,
                        "message": "Would overwrite app.py.",
                        "diff": {"text": "--- app.py\n+++ app.py"},
                    }
                ],
            },
            "message": "One file failed.",
        }

        self.assertEqual(
            edit_text_formatting.format_write_files_report_text("Write files:", report),
            "\n".join(
                [
                    "Write files:",
                    "  projectRoot: /tmp/project",
                    "  ok: no",
                    "  files: 1",
                    "  message: One file failed.",
                    "  items:",
                    "    - app.py: failed - Would overwrite app.py.",
                    "      diff:",
                    "        --- app.py",
                    "        +++ app.py",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
