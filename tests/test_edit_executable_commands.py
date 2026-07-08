import unittest

from vibeagent import edit_executable_commands
from vibeagent import edit_patch_commands


class EditExecutableCommandsTests(unittest.TestCase):
    def test_edit_patch_commands_reexports_executable_helpers(self) -> None:
        self.assertIs(edit_patch_commands.get_check_set_executable_report, edit_executable_commands.get_check_set_executable_report)
        self.assertIs(edit_patch_commands.get_check_set_executable_text, edit_executable_commands.get_check_set_executable_text)
        self.assertIs(edit_patch_commands.get_set_executable_report, edit_executable_commands.get_set_executable_report)
        self.assertIs(edit_patch_commands.get_set_executable_text, edit_executable_commands.get_set_executable_text)
        self.assertIs(edit_patch_commands.format_executable_observation, edit_executable_commands.format_executable_observation)
        self.assertIs(edit_patch_commands.serialize_executable_report, edit_executable_commands.serialize_executable_report)
        self.assertIs(edit_patch_commands.format_executable_report_text, edit_executable_commands.format_executable_report_text)


if __name__ == "__main__":
    unittest.main()
