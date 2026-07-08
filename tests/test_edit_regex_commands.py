import unittest

from vibeagent import edit_patch_commands
from vibeagent import edit_regex_commands


class EditRegexCommandsTests(unittest.TestCase):
    def test_edit_patch_commands_reexports_regex_helpers(self) -> None:
        self.assertIs(edit_patch_commands.get_check_regex_replace_report, edit_regex_commands.get_check_regex_replace_report)
        self.assertIs(edit_patch_commands.get_check_regex_replace_text, edit_regex_commands.get_check_regex_replace_text)
        self.assertIs(edit_patch_commands.get_regex_replace_report, edit_regex_commands.get_regex_replace_report)
        self.assertIs(edit_patch_commands.get_regex_replace_text, edit_regex_commands.get_regex_replace_text)
        self.assertIs(edit_patch_commands.format_regex_replace_observation, edit_regex_commands.format_regex_replace_observation)
        self.assertIs(edit_patch_commands.serialize_regex_replace_report, edit_regex_commands.serialize_regex_replace_report)
        self.assertIs(edit_patch_commands.format_regex_replace_report_text, edit_regex_commands.format_regex_replace_report_text)


if __name__ == "__main__":
    unittest.main()
