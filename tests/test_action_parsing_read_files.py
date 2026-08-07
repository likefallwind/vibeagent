from __future__ import annotations

import unittest

from vibeagent.action_parsing import parse_tool_action
from vibeagent.action_parsing_read import READ_ACTION_TYPES
from vibeagent.action_parsing_read_files import READ_FILE_ACTION_TYPES, parse_read_file_action
from vibeagent.types import NotebookReadAction, ReadFileAction, ReadFilesAction


class ActionParsingReadFilesTests(unittest.TestCase):
    def test_read_parser_keeps_file_action_types_registered(self) -> None:
        self.assertLessEqual(READ_FILE_ACTION_TYPES, READ_ACTION_TYPES)
        self.assertIsNone(parse_read_file_action("file_info", {"paths": ["app.py"]}, "raw"))

    def test_parse_read_file_keeps_line_and_byte_limits(self) -> None:
        action = parse_tool_action(
            "read_file",
            {"path": "src/app.py", "start_line": 3, "line_count": 5, "max_bytes": 1000, "show_line_numbers": True},
        )

        self.assertIsInstance(action, ReadFileAction)
        self.assertEqual(action.path, "src/app.py")
        self.assertEqual(action.start_line, 3)
        self.assertEqual(action.line_count, 5)
        self.assertEqual(action.max_bytes, 1000)
        self.assertTrue(action.show_line_numbers)

    def test_parse_notebook_read_normalizes_defaults(self) -> None:
        action = parse_tool_action("notebook_read", {"path": "analysis.ipynb", "include_outputs": True})

        self.assertIsInstance(action, NotebookReadAction)
        self.assertEqual(action.path, "analysis.ipynb")
        self.assertEqual(action.start_cell, 1)
        self.assertEqual(action.cell_count, 50)
        self.assertTrue(action.include_outputs)
        self.assertEqual(action.max_source_chars, 2000)

    def test_parse_read_files_keeps_paths_and_line_numbers(self) -> None:
        action = parse_tool_action(
            "read_files",
            {"paths": ["src/app.py", "tests/test_app.py"], "max_bytes_per_file": 1000, "show_line_numbers": True},
        )

        self.assertIsInstance(action, ReadFilesAction)
        self.assertEqual(action.paths, ["src/app.py", "tests/test_app.py"])
        self.assertEqual(action.max_bytes_per_file, 1000)
        self.assertTrue(action.show_line_numbers)


if __name__ == "__main__":
    unittest.main()
