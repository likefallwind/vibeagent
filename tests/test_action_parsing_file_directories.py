import unittest

from vibeagent.action_parsing_file_directories import parse_file_directory_action
from vibeagent.action_parsing_helpers import ActionParseError
from vibeagent.types import CheckCreateDirectoriesAction, CheckMoveDirectoryAction, CopyDirectoriesAction, DeleteEmptyDirectoryAction


class ActionParsingFileDirectoriesTests(unittest.TestCase):
    def test_parse_file_directory_action_parses_move_actions(self) -> None:
        checked = parse_file_directory_action("check_move_dir", {"source": "old", "destination": "new"}, "{}")

        self.assertEqual(checked, CheckMoveDirectoryAction(type="check_move_dir", source="old", destination="new"))

    def test_parse_file_directory_action_parses_copy_and_create_actions(self) -> None:
        copied = parse_file_directory_action(
            "copy_dirs",
            {"transfers": [{"source": "template", "destination": "generated"}]},
            "{}",
        )
        created = parse_file_directory_action("check_create_dirs", {"paths": ["pkg/generated", "assets/icons"]}, "{}")

        self.assertIsInstance(copied, CopyDirectoriesAction)
        self.assertEqual([(transfer.source, transfer.destination) for transfer in copied.transfers], [("template", "generated")])
        self.assertEqual(created, CheckCreateDirectoriesAction(type="check_create_dirs", paths=["pkg/generated", "assets/icons"]))

    def test_parse_file_directory_action_parses_delete_empty_actions(self) -> None:
        deleted = parse_file_directory_action("delete_empty_dir", {"path": "pkg/empty"}, "{}")

        self.assertEqual(deleted, DeleteEmptyDirectoryAction(type="delete_empty_dir", path="pkg/empty"))

    def test_parse_file_directory_action_returns_none_for_other_actions(self) -> None:
        self.assertIsNone(parse_file_directory_action("write_file", {"path": "app.py"}, "{}"))

    def test_parse_file_directory_action_preserves_validation_errors(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "check_move_dir action requires string destination"):
            parse_file_directory_action("check_move_dir", {"source": "old"}, "{}")

        with self.assertRaisesRegex(ActionParseError, "copy_dirs transfer 1 requires a non-empty destination"):
            parse_file_directory_action("copy_dirs", {"transfers": [{"source": "old", "destination": ""}]}, "{}")

        with self.assertRaisesRegex(ActionParseError, "create_dirs action requires a non-empty paths list"):
            parse_file_directory_action("create_dirs", {"paths": []}, "{}")


if __name__ == "__main__":
    unittest.main()
