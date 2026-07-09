import tempfile
import unittest
from pathlib import Path

from vibeagent import edit_commands, edit_exact_commands


class EditExactCommandsTests(unittest.TestCase):
    def test_edit_commands_reexports_exact_edit_helpers(self) -> None:
        self.assertIs(edit_commands.get_check_edit_file_text, edit_exact_commands.get_check_edit_file_text)
        self.assertIs(edit_commands.get_check_edit_file_report, edit_exact_commands.get_check_edit_file_report)
        self.assertIs(edit_commands.get_edit_file_text, edit_exact_commands.get_edit_file_text)
        self.assertIs(edit_commands.get_edit_file_report, edit_exact_commands.get_edit_file_report)
        self.assertIs(edit_commands.get_check_multi_edit_file_text, edit_exact_commands.get_check_multi_edit_file_text)
        self.assertIs(edit_commands.get_check_multi_edit_file_report, edit_exact_commands.get_check_multi_edit_file_report)
        self.assertIs(edit_commands.get_multi_edit_file_text, edit_exact_commands.get_multi_edit_file_text)
        self.assertIs(edit_commands.get_multi_edit_file_report, edit_exact_commands.get_multi_edit_file_report)

    def test_edit_file_and_multi_edit_update_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-edit-exact-") as tmp:
            root = Path(tmp)
            path = root / "app.py"
            path.write_text("old\nprint(value)\n", encoding="utf-8")

            edit = edit_exact_commands.get_edit_file_report(root, path="app.py", old="old", new="new")
            multi = edit_exact_commands.get_multi_edit_file_report(
                root,
                path="app.py",
                edits=["new", "final", "print", "log"],
            )

            self.assertEqual(path.read_text(encoding="utf-8"), "final\nlog(value)\n")

        self.assertTrue(edit["ok"])
        self.assertEqual(edit["kind"], "edit_file")
        self.assertTrue(multi["ok"])
        self.assertEqual(multi["kind"], "multi_edit_file")

    def test_exact_edit_text_reports_usage_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-edit-exact-") as tmp:
            text = edit_exact_commands.get_edit_file_text(tmp, "app.py only-old")
            multi_text = edit_exact_commands.get_multi_edit_file_text(tmp, "app.py old new dangling")

        self.assertIn("Usage: /edit <path> <old> <new>", text)
        self.assertIn("Error:", text)
        self.assertIn("Usage: /multi-edit <path> <old> <new>...", multi_text)
        self.assertIn("Error:", multi_text)


if __name__ == "__main__":
    unittest.main()
