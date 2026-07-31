from __future__ import annotations

import unittest

from vibeagent import edit_directory_commands, edit_directory_transfer_commands


class EditDirectoryCommandsTests(unittest.TestCase):
    def test_directory_commands_reexports_transfer_helpers(self) -> None:
        self.assertIs(
            edit_directory_commands.get_check_move_dir_report,
            edit_directory_transfer_commands.get_check_move_dir_report,
        )
        self.assertIs(edit_directory_commands.get_move_dir_text, edit_directory_transfer_commands.get_move_dir_text)
        self.assertIs(
            edit_directory_commands.get_check_copy_dirs_report,
            edit_directory_transfer_commands.get_check_copy_dirs_report,
        )
        self.assertIs(edit_directory_commands.get_copy_dirs_text, edit_directory_transfer_commands.get_copy_dirs_text)


if __name__ == "__main__":
    unittest.main()
