import unittest

from vibeagent.action_parsing_file_paths import parse_file_path_action
from vibeagent.action_parsing_helpers import ActionParseError
from vibeagent.types import CheckCopyFileAction, CheckMoveFilesAction, CheckSetExecutableAction, DeleteFilesAction, MoveFileAction


class ActionParsingFilePathsTests(unittest.TestCase):
    def test_parse_file_path_action_parses_delete_actions(self) -> None:
        deleted = parse_file_path_action("delete_files", {"paths": ["old.py", "other.py"]}, "{}")

        self.assertEqual(deleted, DeleteFilesAction(type="delete_files", paths=["old.py", "other.py"]))

    def test_parse_file_path_action_parses_move_and_copy_actions(self) -> None:
        moved = parse_file_path_action("move_file", {"source": "old.py", "destination": "new.py"}, "{}")
        checked_moves = parse_file_path_action(
            "check_move_files",
            {"transfers": [{"source": "a.py", "destination": "b.py"}]},
            "{}",
        )
        copied = parse_file_path_action("check_copy_file", {"source": "template.py", "destination": "new.py"}, "{}")

        self.assertEqual(moved, MoveFileAction(type="move_file", source="old.py", destination="new.py"))
        self.assertIsInstance(checked_moves, CheckMoveFilesAction)
        self.assertEqual([(transfer.source, transfer.destination) for transfer in checked_moves.transfers], [("a.py", "b.py")])
        self.assertEqual(copied, CheckCopyFileAction(type="check_copy_file", source="template.py", destination="new.py"))

    def test_parse_file_path_action_parses_executable_actions(self) -> None:
        checked = parse_file_path_action("check_set_executable", {"path": "bin/tool", "executable": False}, "{}")

        self.assertEqual(checked, CheckSetExecutableAction(type="check_set_executable", path="bin/tool", executable=False))

    def test_parse_file_path_action_returns_none_for_other_actions(self) -> None:
        self.assertIsNone(parse_file_path_action("write_file", {"path": "app.py"}, "{}"))

    def test_parse_file_path_action_preserves_validation_errors(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "check_delete_file action requires a string path"):
            parse_file_path_action("check_delete_file", {}, "{}")

        with self.assertRaisesRegex(ActionParseError, "move_files transfer 1 requires a non-empty destination"):
            parse_file_path_action("move_files", {"transfers": [{"source": "old.py", "destination": ""}]}, "{}")

        with self.assertRaisesRegex(ActionParseError, "set_executable action executable must be a boolean"):
            parse_file_path_action("set_executable", {"path": "tool.sh", "executable": "true"}, "{}")


if __name__ == "__main__":
    unittest.main()
