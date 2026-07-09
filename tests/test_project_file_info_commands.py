from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent import project_commands, project_file_info_commands


class ProjectFileInfoCommandsTests(unittest.TestCase):
    def test_project_commands_keeps_file_info_command_exports(self) -> None:
        self.assertIs(project_commands.get_file_info_text, project_file_info_commands.get_file_info_text)
        self.assertIs(project_commands.get_file_info_report, project_file_info_commands.get_file_info_report)
        self.assertIs(project_commands.format_file_info_report_text, project_file_info_commands.format_file_info_report_text)
        self.assertIs(project_commands.serialize_file_info_result, project_file_info_commands.serialize_file_info_result)
        self.assertIs(project_commands.get_image_info_text, project_file_info_commands.get_image_info_text)
        self.assertIs(project_commands.get_image_info_report, project_file_info_commands.get_image_info_report)
        self.assertIs(project_commands.format_image_info_report_text, project_file_info_commands.format_image_info_report_text)
        self.assertIs(project_commands.serialize_image_info_result, project_file_info_commands.serialize_image_info_result)
        self.assertIs(project_commands.file_type_text, project_file_info_commands.file_type_text)
        self.assertIs(project_commands.yes_no_unknown, project_file_info_commands.yes_no_unknown)

    def test_file_info_report_serializes_file_directory_and_missing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "app.py").write_text("print('hi')\n", encoding="utf-8")
            (root / "pkg").mkdir()

            report = project_file_info_commands.get_file_info_report(root, ["app.py", "pkg", "missing.py"])
            usage = project_file_info_commands.get_file_info_report(root)

        self.assertFalse(report["ok"])
        self.assertEqual(report["paths"]["ok"], 2)
        self.assertEqual(report["paths"]["total"], 3)
        self.assertEqual(report["paths"]["items"][0]["type"], "file")
        self.assertEqual(report["paths"]["items"][0]["lineCount"], 1)
        self.assertEqual(report["paths"]["items"][1]["type"], "directory")
        self.assertEqual(report["paths"]["items"][2]["type"], "missing")
        self.assertFalse(usage["ok"])
        self.assertIn("Usage: /file-info", usage["message"])

    def test_image_info_report_serializes_png_and_usage(self) -> None:
        png = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x02\x00\x00\x00\x03\x08\x02\x00\x00\x00"
            b"\xf9\x1f\x7b\x84"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "logo.png").write_bytes(png)

            report = project_file_info_commands.get_image_info_report(root, "logo.png missing.png")
            text = project_file_info_commands.get_image_info_text(root, "logo.png")
            usage = project_file_info_commands.get_image_info_report(root)

        self.assertFalse(report["ok"])
        self.assertEqual(report["images"]["ok"], 1)
        self.assertEqual(report["images"]["total"], 2)
        self.assertEqual(report["images"]["items"][0]["format"], "png")
        self.assertEqual(report["images"]["items"][0]["width"], 2)
        self.assertEqual(report["images"]["items"][0]["height"], 3)
        self.assertEqual(report["images"]["items"][1]["type"], "missing")
        self.assertIn("Image info:", text)
        self.assertFalse(usage["ok"])
        self.assertIn("Usage: /image-info", usage["message"])


if __name__ == "__main__":
    unittest.main()
