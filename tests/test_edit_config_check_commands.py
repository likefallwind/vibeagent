import json
import tempfile
import unittest
from pathlib import Path

from vibeagent import edit_commands, edit_config_check_commands


class EditConfigCheckCommandsTests(unittest.TestCase):
    def test_edit_commands_reexports_config_check_helpers(self) -> None:
        self.assertIs(edit_commands.get_config_check_text, edit_config_check_commands.get_config_check_text)
        self.assertIs(edit_commands.get_config_check_report, edit_config_check_commands.get_config_check_report)
        self.assertIs(edit_commands.format_config_check_report_text, edit_config_check_commands.format_config_check_report_text)
        self.assertIs(edit_commands.format_check_location, edit_config_check_commands.format_check_location)

    def test_config_check_report_reads_valid_and_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-edit-config-check-") as tmp:
            root = Path(tmp)
            (root / "good.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
            (root / "bad.json").write_text("{bad", encoding="utf-8")

            report = edit_config_check_commands.get_config_check_report(root, max_files=10)
            text = edit_config_check_commands.format_config_check_report_text(report)

        self.assertFalse(report["ok"])
        self.assertEqual(report["path"], ".")
        self.assertEqual(report["files"]["shown"], 2)
        self.assertEqual(report["files"]["total"], 2)
        self.assertIn("good.json", text)
        self.assertIn("bad.json", text)
        self.assertIn("failed", text)

    def test_config_check_text_reports_usage_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-edit-config-check-") as tmp:
            text = edit_config_check_commands.get_config_check_text(tmp, "one two")

        self.assertIn("Usage: /config-check [path]", text)
        self.assertIn("Error:", text)

    def test_format_check_location(self) -> None:
        self.assertEqual(edit_config_check_commands.format_check_location(None, 2), "")
        self.assertEqual(edit_config_check_commands.format_check_location(3, None), " at line 3")
        self.assertEqual(edit_config_check_commands.format_check_location(3, 7), " at line 3, column 7")


if __name__ == "__main__":
    unittest.main()
