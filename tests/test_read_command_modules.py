from __future__ import annotations

import unittest

from vibeagent import read_commands, read_context_commands
from vibeagent.read_report_helpers import (
    format_around_many_report_text,
    format_around_report_text,
    format_read_files_report_text,
    format_read_ranges_report_text,
    format_read_report_text,
    format_tail_report_text,
    indent_block,
)


class ReadCommandModuleTests(unittest.TestCase):
    def test_read_commands_reexports_report_helpers(self) -> None:
        self.assertIs(read_commands.format_read_report_text, format_read_report_text)
        self.assertIs(read_commands.format_tail_report_text, format_tail_report_text)
        self.assertIs(read_commands.format_around_report_text, format_around_report_text)
        self.assertIs(read_commands.format_around_many_report_text, format_around_many_report_text)
        self.assertIs(read_commands.format_read_files_report_text, format_read_files_report_text)
        self.assertIs(read_commands.format_read_ranges_report_text, format_read_ranges_report_text)
        self.assertIs(read_commands._indent_block, indent_block)

    def test_read_commands_reexports_context_report_commands(self) -> None:
        self.assertIs(read_commands.get_around_report, read_context_commands.get_around_report)
        self.assertIs(read_commands.get_around_many_report, read_context_commands.get_around_many_report)


if __name__ == "__main__":
    unittest.main()
