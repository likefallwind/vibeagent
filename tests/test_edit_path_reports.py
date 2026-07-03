import unittest

from vibeagent import edit_path_commands
from vibeagent import edit_path_reports


class EditPathReportsTests(unittest.TestCase):
    def test_edit_path_commands_reexports_report_helpers(self) -> None:
        self.assertIs(edit_path_commands.format_path_action_observation, edit_path_reports.format_path_action_observation)
        self.assertIs(edit_path_commands.serialize_path_action_report, edit_path_reports.serialize_path_action_report)
        self.assertIs(edit_path_commands.format_path_action_report_text, edit_path_reports.format_path_action_report_text)
        self.assertIs(edit_path_commands.format_path_list_observation, edit_path_reports.format_path_list_observation)
        self.assertIs(edit_path_commands.serialize_path_list_report, edit_path_reports.serialize_path_list_report)
        self.assertIs(edit_path_commands.format_path_list_report_text, edit_path_reports.format_path_list_report_text)
        self.assertIs(
            edit_path_commands.format_file_transfer_observation,
            edit_path_reports.format_file_transfer_observation,
        )
        self.assertIs(edit_path_commands.serialize_file_transfer_report, edit_path_reports.serialize_file_transfer_report)
        self.assertIs(
            edit_path_commands.format_file_transfer_report_text,
            edit_path_reports.format_file_transfer_report_text,
        )
        self.assertIs(
            edit_path_commands.format_file_transfer_list_observation,
            edit_path_reports.format_file_transfer_list_observation,
        )
        self.assertIs(
            edit_path_commands.serialize_file_transfer_list_report,
            edit_path_reports.serialize_file_transfer_list_report,
        )
        self.assertIs(
            edit_path_commands.format_file_transfer_list_report_text,
            edit_path_reports.format_file_transfer_list_report_text,
        )


if __name__ == "__main__":
    unittest.main()
