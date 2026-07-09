import unittest

from vibeagent.tool_definition_file_directories import FILE_DIRECTORY_TOOL_DEFINITIONS
from vibeagent.tool_definition_file_directory_lifecycle import FILE_DIRECTORY_LIFECYCLE_TOOL_DEFINITIONS
from vibeagent.tool_definition_file_directory_transfers import FILE_DIRECTORY_TRANSFER_TOOL_DEFINITIONS
from vibeagent.tool_definition_file_executable import FILE_EXECUTABLE_TOOL_DEFINITIONS


class FileDirectoryToolDefinitionTests(unittest.TestCase):
    def test_file_directory_definitions_are_split_in_order(self) -> None:
        self.assertEqual(
            FILE_DIRECTORY_TOOL_DEFINITIONS,
            FILE_DIRECTORY_TRANSFER_TOOL_DEFINITIONS
            + FILE_DIRECTORY_LIFECYCLE_TOOL_DEFINITIONS
            + FILE_EXECUTABLE_TOOL_DEFINITIONS,
        )

    def test_file_directory_definition_boundaries_remain_stable(self) -> None:
        self.assertEqual(FILE_DIRECTORY_TRANSFER_TOOL_DEFINITIONS[0]["name"], "check_move_dir")
        self.assertEqual(FILE_DIRECTORY_TRANSFER_TOOL_DEFINITIONS[-1]["name"], "copy_dirs")
        self.assertEqual(FILE_DIRECTORY_LIFECYCLE_TOOL_DEFINITIONS[0]["name"], "check_create_dir")
        self.assertEqual(FILE_DIRECTORY_LIFECYCLE_TOOL_DEFINITIONS[-1]["name"], "delete_empty_dirs")
        self.assertEqual(FILE_EXECUTABLE_TOOL_DEFINITIONS[0]["name"], "check_set_executable")
        self.assertEqual(FILE_EXECUTABLE_TOOL_DEFINITIONS[-1]["name"], "set_executable")

    def test_file_directory_tool_names_remain_in_original_order(self) -> None:
        self.assertEqual(
            [tool["name"] for tool in FILE_DIRECTORY_TOOL_DEFINITIONS],
            [
                "check_move_dir",
                "move_dir",
                "check_move_dirs",
                "move_dirs",
                "check_copy_dir",
                "check_copy_dirs",
                "copy_dir",
                "copy_dirs",
                "check_create_dir",
                "check_create_dirs",
                "create_dir",
                "create_dirs",
                "check_delete_empty_dir",
                "check_delete_empty_dirs",
                "delete_empty_dir",
                "delete_empty_dirs",
                "check_set_executable",
                "set_executable",
            ],
        )


if __name__ == "__main__":
    unittest.main()
