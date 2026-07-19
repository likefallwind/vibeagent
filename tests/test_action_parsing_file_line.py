import unittest

from vibeagent.action_parsing_file_line import parse_file_line_action
from vibeagent.action_parsing_helpers import ActionParseError
from vibeagent.types import AppendFileAction, CheckInsertLinesAction, CheckReplaceLinesAction, InsertLinesAction


class ActionParsingFileLineTests(unittest.TestCase):
    def test_parse_file_line_action_parses_replace_actions(self) -> None:
        checked = parse_file_line_action(
            "check_replace_lines",
            {"path": "app.py", "start_line": 1, "end_line": 2, "content": "new\n"},
            "{}",
        )

        self.assertEqual(
            checked,
            CheckReplaceLinesAction(type="check_replace_lines", path="app.py", start_line=1, end_line=2, content="new\n"),
        )

    def test_parse_file_line_action_parses_insert_and_append_actions(self) -> None:
        checked_insert = parse_file_line_action("check_insert_lines", {"path": "app.py", "line": 2, "content": "new\n"}, "{}")
        inserted = parse_file_line_action("insert_lines", {"path": "app.py", "line": 2, "content": "new\n"}, "{}")
        appended = parse_file_line_action("append_file", {"path": "app.py", "content": "tail\n"}, "{}")

        self.assertEqual(checked_insert, CheckInsertLinesAction(type="check_insert_lines", path="app.py", line=2, content="new\n"))
        self.assertEqual(inserted, InsertLinesAction(type="insert_lines", path="app.py", line=2, content="new\n"))
        self.assertEqual(appended, AppendFileAction(type="append_file", path="app.py", content="tail\n"))

    def test_parse_file_line_action_returns_none_for_other_actions(self) -> None:
        self.assertIsNone(parse_file_line_action("write_file", {"path": "app.py"}, "{}"))

    def test_parse_file_line_action_preserves_validation_errors(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "check_replace_lines action requires start_line"):
            parse_file_line_action("check_replace_lines", {"path": "app.py", "end_line": 2, "content": "new\n"}, "{}")

        with self.assertRaisesRegex(ActionParseError, "end_line must be greater than or equal to start_line"):
            parse_file_line_action("replace_lines", {"path": "app.py", "start_line": 3, "end_line": 2, "content": "new\n"}, "{}")

        with self.assertRaisesRegex(ActionParseError, "append_file action requires non-empty string content"):
            parse_file_line_action("append_file", {"path": "app.py", "content": ""}, "{}")


if __name__ == "__main__":
    unittest.main()
