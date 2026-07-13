import unittest

from vibeagent.tool_definition_file_exact_edit import FILE_EXACT_EDIT_TOOL_DEFINITIONS
from vibeagent.tool_definition_file_line_edit import FILE_LINE_EDIT_TOOL_DEFINITIONS
from vibeagent.tool_definition_file_patch_edit import FILE_PATCH_EDIT_TOOL_DEFINITIONS
from vibeagent.tool_definition_file_text import FILE_TEXT_TOOL_DEFINITIONS
from vibeagent.tool_definition_file_write import FILE_WRITE_TOOL_DEFINITIONS


class FileTextToolDefinitionTests(unittest.TestCase):
    def test_file_text_definitions_are_split_in_order(self) -> None:
        self.assertEqual(
            FILE_TEXT_TOOL_DEFINITIONS,
            FILE_EXACT_EDIT_TOOL_DEFINITIONS
            + FILE_LINE_EDIT_TOOL_DEFINITIONS
            + FILE_PATCH_EDIT_TOOL_DEFINITIONS
            + FILE_WRITE_TOOL_DEFINITIONS,
        )

    def test_file_text_definition_boundaries_remain_stable(self) -> None:
        self.assertEqual(FILE_EXACT_EDIT_TOOL_DEFINITIONS[0]["name"], "check_edit_file")
        self.assertEqual(FILE_EXACT_EDIT_TOOL_DEFINITIONS[-1]["name"], "multi_edit_file")
        self.assertEqual(FILE_LINE_EDIT_TOOL_DEFINITIONS[0]["name"], "check_replace_lines")
        self.assertEqual(FILE_LINE_EDIT_TOOL_DEFINITIONS[-1]["name"], "append_file")
        self.assertEqual(FILE_PATCH_EDIT_TOOL_DEFINITIONS[0]["name"], "check_regex_replace")
        self.assertEqual(FILE_PATCH_EDIT_TOOL_DEFINITIONS[-1]["name"], "patch_files")
        self.assertEqual(FILE_WRITE_TOOL_DEFINITIONS[0]["name"], "check_write_file")
        self.assertEqual(FILE_WRITE_TOOL_DEFINITIONS[-1]["name"], "write_files")

    def test_file_text_tool_names_remain_in_original_order(self) -> None:
        self.assertEqual(
            [tool["name"] for tool in FILE_TEXT_TOOL_DEFINITIONS],
            [
                "check_edit_file",
                "edit_file",
                "check_multi_edit_file",
                "check_notebook_edit",
                "multi_edit_file",
                "check_replace_lines",
                "replace_lines",
                "check_insert_lines",
                "insert_lines",
                "check_append_file",
                "append_file",
                "check_regex_replace",
                "regex_replace",
                "check_patch",
                "check_patches",
                "patch_file",
                "patch_files",
                "check_write_file",
                "write_file",
                "check_write_files",
                "write_files",
            ],
        )


if __name__ == "__main__":
    unittest.main()
