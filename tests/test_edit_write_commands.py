import tempfile
import unittest
from pathlib import Path

from vibeagent import edit_commands, edit_text_commands, edit_write_commands


class EditWriteCommandsTests(unittest.TestCase):
    def test_edit_text_commands_reexports_write_helpers(self) -> None:
        self.assertIs(edit_text_commands.get_check_write_file_text, edit_write_commands.get_check_write_file_text)
        self.assertIs(edit_text_commands.get_check_write_file_report, edit_write_commands.get_check_write_file_report)
        self.assertIs(edit_text_commands.get_write_file_text, edit_write_commands.get_write_file_text)
        self.assertIs(edit_text_commands.get_write_file_report, edit_write_commands.get_write_file_report)
        self.assertIs(edit_text_commands.get_check_write_files_text, edit_write_commands.get_check_write_files_text)
        self.assertIs(edit_text_commands.get_check_write_files_report, edit_write_commands.get_check_write_files_report)
        self.assertIs(edit_text_commands.get_write_files_text, edit_write_commands.get_write_files_text)
        self.assertIs(edit_text_commands.get_write_files_report, edit_write_commands.get_write_files_report)

    def test_edit_commands_reexports_write_helpers(self) -> None:
        self.assertIs(edit_commands.get_check_write_file_text, edit_write_commands.get_check_write_file_text)
        self.assertIs(edit_commands.get_check_write_file_report, edit_write_commands.get_check_write_file_report)
        self.assertIs(edit_commands.get_write_file_text, edit_write_commands.get_write_file_text)
        self.assertIs(edit_commands.get_write_file_report, edit_write_commands.get_write_file_report)
        self.assertIs(edit_commands.get_check_write_files_text, edit_write_commands.get_check_write_files_text)
        self.assertIs(edit_commands.get_check_write_files_report, edit_write_commands.get_check_write_files_report)
        self.assertIs(edit_commands.get_write_files_text, edit_write_commands.get_write_files_text)
        self.assertIs(edit_commands.get_write_files_report, edit_write_commands.get_write_files_report)

    def test_write_file_report_reports_usage_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-edit-write-") as tmp:
            report = edit_write_commands.get_write_file_report(tmp, "")
            text = edit_write_commands.get_write_file_text(tmp, "")

        self.assertFalse(report["ok"])
        self.assertEqual(report["kind"], "write_file")
        self.assertIn("Usage: /write <path> <text>", report["message"])
        self.assertEqual(text, report["message"])

    def test_write_files_text_writes_multiple_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-edit-write-") as tmp:
            root = Path(tmp)
            text = edit_write_commands.get_write_files_text(
                root,
                files=[
                    "src/app.py",
                    "print('ok')\n",
                    "README.md",
                    "hello\n",
                ],
            )

            self.assertEqual((root / "src" / "app.py").read_text(encoding="utf-8"), "print('ok')\n")
            self.assertEqual((root / "README.md").read_text(encoding="utf-8"), "hello\n")

        self.assertIn("Write files:", text)
        self.assertIn("files: 2", text)
        self.assertIn("src/app.py: ok", text)
        self.assertIn("README.md: ok", text)


if __name__ == "__main__":
    unittest.main()
