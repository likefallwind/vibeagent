import unittest

from vibeagent.action_parsing_file_write import parse_file_write_action
from vibeagent.action_parsing_helpers import ActionParseError
from vibeagent.types import CheckWriteFileAction, CheckWriteFilesAction, WriteFileAction, WriteFilesAction


class ActionParsingFileWriteTests(unittest.TestCase):
    def test_parse_file_write_action_parses_single_file_actions(self) -> None:
        checked = parse_file_write_action(
            "check_write_file",
            {"path": "app.py", "content": "print('ok')\n"},
            "{}",
        )
        written = parse_file_write_action(
            "write_file",
            {"path": "app.py", "content": "print('ok')\n"},
            "{}",
        )

        self.assertEqual(checked, CheckWriteFileAction(type="check_write_file", path="app.py", content="print('ok')\n"))
        self.assertEqual(written, WriteFileAction(type="write_file", path="app.py", content="print('ok')\n"))

    def test_parse_file_write_action_parses_batch_file_actions(self) -> None:
        value = {"files": [{"path": "a.py", "content": "a\n"}, {"path": "b.py", "content": "b\n"}]}

        checked = parse_file_write_action("check_write_files", value, "{}")
        written = parse_file_write_action("write_files", value, "{}")

        self.assertIsInstance(checked, CheckWriteFilesAction)
        self.assertIsInstance(written, WriteFilesAction)
        self.assertEqual([file.path for file in checked.files], ["a.py", "b.py"])
        self.assertEqual([file.content for file in written.files], ["a\n", "b\n"])

    def test_parse_file_write_action_returns_none_for_other_actions(self) -> None:
        self.assertIsNone(parse_file_write_action("edit_file", {"path": "app.py"}, "{}"))

    def test_parse_file_write_action_preserves_validation_errors(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "check_write_file action requires string content"):
            parse_file_write_action("check_write_file", {"path": "app.py"}, '{"type":"check_write_file"}')

        with self.assertRaisesRegex(ActionParseError, "write_files action requires a non-empty files list"):
            parse_file_write_action("write_files", {"files": []}, '{"type":"write_files"}')


if __name__ == "__main__":
    unittest.main()
