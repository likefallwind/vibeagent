import unittest

from vibeagent import edit_command_parsing
from vibeagent import edit_path_parsing


class EditPathParsingTests(unittest.TestCase):
    def test_edit_command_parsing_reexports_path_parsers(self) -> None:
        self.assertIs(
            edit_command_parsing.parse_required_single_path_argument,
            edit_path_parsing.parse_required_single_path_argument,
        )
        self.assertIs(
            edit_command_parsing.parse_required_path_list_argument,
            edit_path_parsing.parse_required_path_list_argument,
        )
        self.assertIs(
            edit_command_parsing.parse_source_destination_argument,
            edit_path_parsing.parse_source_destination_argument,
        )
        self.assertIs(
            edit_command_parsing.parse_file_transfer_list_argument,
            edit_path_parsing.parse_file_transfer_list_argument,
        )
        self.assertIs(
            edit_command_parsing.parse_directory_transfer_list_argument,
            edit_path_parsing.parse_directory_transfer_list_argument,
        )
        self.assertIs(edit_command_parsing.parse_executable_argument, edit_path_parsing.parse_executable_argument)
        self.assertIs(edit_command_parsing.parse_optional_bool, edit_path_parsing.parse_optional_bool)


if __name__ == "__main__":
    unittest.main()
