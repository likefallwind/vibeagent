import unittest

from vibeagent.tool_definition_file_directories import FILE_DIRECTORY_TOOL_DEFINITIONS
from vibeagent.tool_definition_file_editing import FILE_EDITING_TOOL_DEFINITIONS


class ToolDefinitionFileDirectoriesTests(unittest.TestCase):
    def test_file_editing_definitions_append_directory_tools_in_order(self) -> None:
        editing_names = [str(tool["name"]) for tool in FILE_EDITING_TOOL_DEFINITIONS]
        directory_names = [str(tool["name"]) for tool in FILE_DIRECTORY_TOOL_DEFINITIONS]

        self.assertEqual(directory_names[0], "check_move_dir")
        self.assertEqual(directory_names[-1], "set_executable")
        self.assertEqual(editing_names[-len(directory_names) :], directory_names)
        self.assertEqual(editing_names[editing_names.index("copy_files") + 1], "check_move_dir")


if __name__ == "__main__":
    unittest.main()
