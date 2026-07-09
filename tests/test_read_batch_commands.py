from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent import read_commands
from vibeagent.read_batch_commands import (
    format_read_files_report_text,
    format_read_ranges_report_text,
    get_read_files_report,
    get_read_files_text,
    get_read_ranges_report,
    get_read_ranges_text,
)


class ReadBatchCommandModuleTests(unittest.TestCase):
    def test_read_commands_reexports_batch_helpers(self) -> None:
        self.assertIs(read_commands.get_read_files_report, get_read_files_report)
        self.assertIs(read_commands.get_read_files_text, get_read_files_text)
        self.assertIs(read_commands.format_read_files_report_text, format_read_files_report_text)
        self.assertIs(read_commands.get_read_ranges_report, get_read_ranges_report)
        self.assertIs(read_commands.get_read_ranges_text, get_read_ranges_text)
        self.assertIs(read_commands.format_read_ranges_report_text, format_read_ranges_report_text)

    def test_text_helpers_resolve_compatibility_patch_targets(self) -> None:
        root = Path(".").resolve()
        files_report = {"ok": True, "message": "files"}
        ranges_report = {"ok": True, "message": "ranges"}
        with (
            patch("vibeagent.read_commands.get_read_files_report", return_value=files_report) as get_files,
            patch("vibeagent.read_commands.format_read_files_report_text", return_value="files rendered") as format_files,
            patch("vibeagent.read_commands.get_read_ranges_report", return_value=ranges_report) as get_ranges,
            patch("vibeagent.read_commands.format_read_ranges_report_text", return_value="ranges rendered") as format_ranges,
        ):
            self.assertEqual(
                get_read_files_text(root, ["src/app.py"], max_bytes_per_file=2_000, show_line_numbers=True),
                "files rendered",
            )
            self.assertEqual(
                get_read_ranges_text(root, ["src/app.py:1:2"], max_bytes_per_range=3_000),
                "ranges rendered",
            )

        get_files.assert_called_once_with(
            root,
            ["src/app.py"],
            max_bytes_per_file=2_000,
            show_line_numbers=True,
        )
        format_files.assert_called_once_with(files_report)
        get_ranges.assert_called_once_with(root, ["src/app.py:1:2"], max_bytes_per_range=3_000)
        format_ranges.assert_called_once_with(ranges_report)


if __name__ == "__main__":
    unittest.main()
