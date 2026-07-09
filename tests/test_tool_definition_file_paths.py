import unittest

from vibeagent.tool_definition_file_copies import FILE_COPY_TOOL_DEFINITIONS
from vibeagent.tool_definition_file_deletes import FILE_DELETE_TOOL_DEFINITIONS
from vibeagent.tool_definition_file_moves import FILE_MOVE_TOOL_DEFINITIONS
from vibeagent.tool_definition_file_paths import FILE_PATH_TOOL_DEFINITIONS


class FilePathToolDefinitionTests(unittest.TestCase):
    def test_file_path_definitions_are_split_in_order(self) -> None:
        self.assertEqual(
            FILE_PATH_TOOL_DEFINITIONS,
            FILE_DELETE_TOOL_DEFINITIONS
            + FILE_MOVE_TOOL_DEFINITIONS
            + FILE_COPY_TOOL_DEFINITIONS,
        )

    def test_file_path_definition_boundaries_remain_stable(self) -> None:
        self.assertEqual(FILE_DELETE_TOOL_DEFINITIONS[0]["name"], "check_delete_file")
        self.assertEqual(FILE_DELETE_TOOL_DEFINITIONS[-1]["name"], "delete_files")
        self.assertEqual(FILE_MOVE_TOOL_DEFINITIONS[0]["name"], "check_move_file")
        self.assertEqual(FILE_MOVE_TOOL_DEFINITIONS[-1]["name"], "move_files")
        self.assertEqual(FILE_COPY_TOOL_DEFINITIONS[0]["name"], "check_copy_file")
        self.assertEqual(FILE_COPY_TOOL_DEFINITIONS[-1]["name"], "copy_files")

    def test_file_path_tool_names_remain_in_original_order(self) -> None:
        self.assertEqual(
            [tool["name"] for tool in FILE_PATH_TOOL_DEFINITIONS],
            [
                "check_delete_file",
                "delete_file",
                "check_delete_files",
                "delete_files",
                "check_move_file",
                "move_file",
                "check_move_files",
                "move_files",
                "check_copy_file",
                "copy_file",
                "check_copy_files",
                "copy_files",
            ],
        )


if __name__ == "__main__":
    unittest.main()
