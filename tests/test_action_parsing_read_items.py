from __future__ import annotations

import unittest

from vibeagent import action_parsing_helpers
from vibeagent.action_parsing_read_items import parse_read_file_contexts, parse_read_file_ranges
from vibeagent.action_parsing_scalars import ActionParseError
from vibeagent.types import ReadFileContextItem, ReadFileRangeItem


class ActionParsingReadItemsTests(unittest.TestCase):
    def test_helpers_reexport_read_item_parsers(self) -> None:
        self.assertIs(action_parsing_helpers.parse_read_file_contexts, parse_read_file_contexts)
        self.assertIs(action_parsing_helpers.parse_read_file_ranges, parse_read_file_ranges)

    def test_parse_read_file_contexts_trims_paths_and_defaults_context(self) -> None:
        self.assertEqual(
            parse_read_file_contexts([{"path": " src/app.py ", "line": "12"}], "raw"),
            [ReadFileContextItem(path="src/app.py", line=12, context_lines=20)],
        )

    def test_parse_read_file_ranges_trims_paths_and_defaults_line_count(self) -> None:
        self.assertEqual(
            parse_read_file_ranges([{"path": " src/app.py ", "start_line": "7"}], "raw"),
            [ReadFileRangeItem(path="src/app.py", start_line=7, line_count=120)],
        )

    def test_parse_read_items_reject_invalid_records(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "requires line"):
            parse_read_file_contexts([{"path": "src/app.py"}], "raw")
        with self.assertRaisesRegex(ActionParseError, "requires start_line"):
            parse_read_file_ranges([{"path": "src/app.py"}], "raw")


if __name__ == "__main__":
    unittest.main()
