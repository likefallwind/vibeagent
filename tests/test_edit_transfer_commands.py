import unittest

from vibeagent import edit_path_commands, edit_transfer_commands


class EditTransferCommandModuleTests(unittest.TestCase):
    def test_edit_path_commands_reexports_transfer_helpers(self) -> None:
        self.assertIs(edit_path_commands.get_check_move_file_report, edit_transfer_commands.get_check_move_file_report)
        self.assertIs(edit_path_commands.get_check_move_file_text, edit_transfer_commands.get_check_move_file_text)
        self.assertIs(edit_path_commands.get_move_file_report, edit_transfer_commands.get_move_file_report)
        self.assertIs(edit_path_commands.get_move_file_text, edit_transfer_commands.get_move_file_text)
        self.assertIs(edit_path_commands.get_check_move_files_report, edit_transfer_commands.get_check_move_files_report)
        self.assertIs(edit_path_commands.get_check_move_files_text, edit_transfer_commands.get_check_move_files_text)
        self.assertIs(edit_path_commands.get_move_files_report, edit_transfer_commands.get_move_files_report)
        self.assertIs(edit_path_commands.get_move_files_text, edit_transfer_commands.get_move_files_text)
        self.assertIs(edit_path_commands.get_check_copy_file_report, edit_transfer_commands.get_check_copy_file_report)
        self.assertIs(edit_path_commands.get_check_copy_file_text, edit_transfer_commands.get_check_copy_file_text)
        self.assertIs(edit_path_commands.get_copy_file_report, edit_transfer_commands.get_copy_file_report)
        self.assertIs(edit_path_commands.get_copy_file_text, edit_transfer_commands.get_copy_file_text)
        self.assertIs(edit_path_commands.get_check_copy_files_report, edit_transfer_commands.get_check_copy_files_report)
        self.assertIs(edit_path_commands.get_check_copy_files_text, edit_transfer_commands.get_check_copy_files_text)
        self.assertIs(edit_path_commands.get_copy_files_report, edit_transfer_commands.get_copy_files_report)
        self.assertIs(edit_path_commands.get_copy_files_text, edit_transfer_commands.get_copy_files_text)


if __name__ == "__main__":
    unittest.main()
