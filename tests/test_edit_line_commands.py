import tempfile
import unittest
from pathlib import Path

from vibeagent import edit_commands, edit_line_commands, edit_text_commands


class EditLineCommandsTests(unittest.TestCase):
    def test_edit_text_commands_reexports_line_helpers(self) -> None:
        self.assertIs(edit_text_commands.get_check_replace_lines_text, edit_line_commands.get_check_replace_lines_text)
        self.assertIs(edit_text_commands.get_check_replace_lines_report, edit_line_commands.get_check_replace_lines_report)
        self.assertIs(edit_text_commands.get_replace_lines_text, edit_line_commands.get_replace_lines_text)
        self.assertIs(edit_text_commands.get_replace_lines_report, edit_line_commands.get_replace_lines_report)
        self.assertIs(edit_text_commands.get_check_insert_lines_text, edit_line_commands.get_check_insert_lines_text)
        self.assertIs(edit_text_commands.get_check_insert_lines_report, edit_line_commands.get_check_insert_lines_report)
        self.assertIs(edit_text_commands.get_insert_lines_text, edit_line_commands.get_insert_lines_text)
        self.assertIs(edit_text_commands.get_insert_lines_report, edit_line_commands.get_insert_lines_report)
        self.assertIs(edit_text_commands.get_check_append_file_text, edit_line_commands.get_check_append_file_text)
        self.assertIs(edit_text_commands.get_check_append_file_report, edit_line_commands.get_check_append_file_report)
        self.assertIs(edit_text_commands.get_append_file_text, edit_line_commands.get_append_file_text)
        self.assertIs(edit_text_commands.get_append_file_report, edit_line_commands.get_append_file_report)

    def test_edit_commands_reexports_line_helpers(self) -> None:
        self.assertIs(edit_commands.get_check_replace_lines_text, edit_line_commands.get_check_replace_lines_text)
        self.assertIs(edit_commands.get_replace_lines_report, edit_line_commands.get_replace_lines_report)
        self.assertIs(edit_commands.get_check_insert_lines_text, edit_line_commands.get_check_insert_lines_text)
        self.assertIs(edit_commands.get_insert_lines_report, edit_line_commands.get_insert_lines_report)
        self.assertIs(edit_commands.get_check_append_file_text, edit_line_commands.get_check_append_file_text)
        self.assertIs(edit_commands.get_append_file_report, edit_line_commands.get_append_file_report)

    def test_replace_insert_and_append_update_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-edit-line-") as tmp:
            root = Path(tmp)
            path = root / "app.py"
            path.write_text("one\ntwo\n", encoding="utf-8")

            replace = edit_line_commands.get_replace_lines_report(root, path="app.py", start_line=2, end_line=2, content="TWO\n")
            insert = edit_line_commands.get_insert_lines_report(root, path="app.py", line=2, content="middle\n")
            append = edit_line_commands.get_append_file_report(root, path="app.py", content="three\n")

            self.assertEqual(path.read_text(encoding="utf-8"), "one\nmiddle\nTWO\nthree\n")

        self.assertTrue(replace["ok"])
        self.assertEqual(replace["kind"], "replace_lines")
        self.assertTrue(insert["ok"])
        self.assertEqual(insert["kind"], "insert_lines")
        self.assertTrue(append["ok"])
        self.assertEqual(append["kind"], "append_file")

    def test_line_command_text_reports_usage_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-edit-line-") as tmp:
            text = edit_line_commands.get_replace_lines_text(tmp, "")

        self.assertIn("Usage: /replace-lines <path> <start> <end> <text>", text)
        self.assertIn("Error:", text)


if __name__ == "__main__":
    unittest.main()
