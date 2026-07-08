import unittest

from vibeagent import edit_delete_commands
from vibeagent import edit_path_commands


class EditDeleteCommandsTests(unittest.TestCase):
    def test_edit_path_commands_reexports_delete_helpers(self) -> None:
        self.assertIs(edit_path_commands.get_check_delete_file_report, edit_delete_commands.get_check_delete_file_report)
        self.assertIs(edit_path_commands.get_check_delete_file_text, edit_delete_commands.get_check_delete_file_text)
        self.assertIs(edit_path_commands.get_delete_file_report, edit_delete_commands.get_delete_file_report)
        self.assertIs(edit_path_commands.get_delete_file_text, edit_delete_commands.get_delete_file_text)
        self.assertIs(edit_path_commands.get_check_delete_files_report, edit_delete_commands.get_check_delete_files_report)
        self.assertIs(edit_path_commands.get_check_delete_files_text, edit_delete_commands.get_check_delete_files_text)
        self.assertIs(edit_path_commands.get_delete_files_report, edit_delete_commands.get_delete_files_report)
        self.assertIs(edit_path_commands.get_delete_files_text, edit_delete_commands.get_delete_files_text)


if __name__ == "__main__":
    unittest.main()
