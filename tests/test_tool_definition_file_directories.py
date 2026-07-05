import unittest

from vibeagent.tool_definition_file_directories import FILE_DIRECTORY_TOOL_DEFINITIONS
from vibeagent.tool_definition_file_editing import FILE_EDITING_TOOL_DEFINITIONS
from vibeagent.tool_definition_file_paths import FILE_PATH_TOOL_DEFINITIONS
from vibeagent.tool_definition_file_text import FILE_TEXT_TOOL_DEFINITIONS


class ToolDefinitionFileDirectoriesTests(unittest.TestCase):
    def test_file_editing_definitions_are_split_in_order(self) -> None:
        self.assertEqual(
            FILE_EDITING_TOOL_DEFINITIONS,
            FILE_TEXT_TOOL_DEFINITIONS + FILE_PATH_TOOL_DEFINITIONS + FILE_DIRECTORY_TOOL_DEFINITIONS,
        )

    def test_file_editing_definition_boundaries_remain_stable(self) -> None:
        self.assertEqual(FILE_TEXT_TOOL_DEFINITIONS[0]["name"], "check_edit_file")
        self.assertEqual(FILE_TEXT_TOOL_DEFINITIONS[-1]["name"], "write_files")
        self.assertEqual(FILE_PATH_TOOL_DEFINITIONS[0]["name"], "check_delete_file")
        self.assertEqual(FILE_PATH_TOOL_DEFINITIONS[-1]["name"], "copy_files")
        self.assertEqual(FILE_DIRECTORY_TOOL_DEFINITIONS[0]["name"], "check_move_dir")
        self.assertEqual(FILE_DIRECTORY_TOOL_DEFINITIONS[-1]["name"], "set_executable")

    def test_file_editing_definitions_append_directory_tools_in_order(self) -> None:
        editing_names = [str(tool["name"]) for tool in FILE_EDITING_TOOL_DEFINITIONS]
        directory_names = [str(tool["name"]) for tool in FILE_DIRECTORY_TOOL_DEFINITIONS]

        self.assertEqual(directory_names[0], "check_move_dir")
        self.assertEqual(directory_names[-1], "set_executable")
        self.assertEqual(editing_names[-len(directory_names) :], directory_names)
        self.assertEqual(editing_names[editing_names.index("copy_files") + 1], "check_move_dir")


if __name__ == "__main__":
    unittest.main()
