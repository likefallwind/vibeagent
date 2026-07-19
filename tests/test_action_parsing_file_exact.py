import unittest

from vibeagent.action_parsing_file_exact import parse_file_exact_action
from vibeagent.action_parsing_helpers import ActionParseError
from vibeagent.types import CheckEditFileAction, CheckMultiEditAction, EditFileAction, MultiEditAction


class ActionParsingFileExactTests(unittest.TestCase):
    def test_parse_file_exact_action_parses_single_edit_actions(self) -> None:
        checked = parse_file_exact_action("check_edit_file", {"path": "app.py", "old": "a", "new": "b"}, "{}")
        edited = parse_file_exact_action("edit_file", {"path": "app.py", "old": "a", "new": "b"}, "{}")

        self.assertEqual(checked, CheckEditFileAction(type="check_edit_file", path="app.py", old="a", new="b"))
        self.assertEqual(edited, EditFileAction(type="edit_file", path="app.py", old="a", new="b"))

    def test_parse_file_exact_action_parses_multi_edit_actions(self) -> None:
        value = {"path": "app.py", "edits": [{"old": "a", "new": "b"}, {"old": "c", "new": "d", "replace_all": True}]}

        checked = parse_file_exact_action("check_multi_edit_file", value, "{}")
        edited = parse_file_exact_action("multi_edit_file", value, "{}")

        self.assertIsInstance(checked, CheckMultiEditAction)
        self.assertIsInstance(edited, MultiEditAction)
        self.assertEqual([edit.old for edit in checked.edits], ["a", "c"])
        self.assertEqual([edit.new for edit in edited.edits], ["b", "d"])
        self.assertTrue(edited.edits[1].replace_all)

    def test_parse_file_exact_action_returns_none_for_other_actions(self) -> None:
        self.assertIsNone(parse_file_exact_action("write_file", {"path": "app.py"}, "{}"))

    def test_parse_file_exact_action_preserves_validation_errors(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "check_edit_file action requires string old"):
            parse_file_exact_action("check_edit_file", {"path": "app.py", "new": "b"}, "{}")

        with self.assertRaisesRegex(ActionParseError, "multi_edit_file action requires a non-empty edits list"):
            parse_file_exact_action("multi_edit_file", {"path": "app.py", "edits": []}, "{}")


if __name__ == "__main__":
    unittest.main()
