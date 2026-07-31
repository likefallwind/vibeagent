from __future__ import annotations

import unittest

from vibeagent.tool_definition_claude_file import (
    CLAUDE_EDIT_TOOL_DEFINITIONS,
    CLAUDE_FILE_TOOL_DEFINITIONS,
    CLAUDE_READ_TOOL_DEFINITIONS,
    CLAUDE_SEARCH_TOOL_DEFINITIONS,
)
from vibeagent.tool_definition_reading import READING_TOOL_DEFINITIONS
from vibeagent.tool_definition_reading_batch import READING_BATCH_TOOL_DEFINITIONS
from vibeagent.tool_definition_reading_context import READING_CONTEXT_TOOL_DEFINITIONS
from vibeagent.tool_definition_reading_inspection import READING_INSPECTION_TOOL_DEFINITIONS
from vibeagent.tool_definition_reading_output import READING_OUTPUT_TOOL_DEFINITIONS
from vibeagent.tool_definition_reading_project import READING_PROJECT_TOOL_DEFINITIONS
from vibeagent.tool_definition_reading_source import READING_SOURCE_TOOL_DEFINITIONS


class ReadingToolDefinitionTests(unittest.TestCase):
    def test_reading_tool_definitions_are_grouped_in_original_order(self) -> None:
        self.assertEqual(
            READING_TOOL_DEFINITIONS,
            READING_PROJECT_TOOL_DEFINITIONS
            + READING_CONTEXT_TOOL_DEFINITIONS
            + READING_OUTPUT_TOOL_DEFINITIONS
            + READING_BATCH_TOOL_DEFINITIONS
            + READING_INSPECTION_TOOL_DEFINITIONS
            + READING_SOURCE_TOOL_DEFINITIONS
            + CLAUDE_FILE_TOOL_DEFINITIONS,
        )

    def test_reading_definition_boundaries_match_reading_domains(self) -> None:
        self.assertEqual([tool["name"] for tool in READING_PROJECT_TOOL_DEFINITIONS], ["list_files", "list_tree", "repo_map"])
        self.assertEqual(
            [tool["name"] for tool in READING_CONTEXT_TOOL_DEFINITIONS],
            ["read_file", "read_file_context", "read_file_contexts"],
        )
        self.assertEqual(
            [tool["name"] for tool in READING_OUTPUT_TOOL_DEFINITIONS],
            ["output_contexts", "output_diagnostics", "python_traceback"],
        )
        self.assertEqual(
            [tool["name"] for tool in READING_BATCH_TOOL_DEFINITIONS],
            ["tail_file", "read_files", "read_file_ranges"],
        )
        self.assertEqual(
            [tool["name"] for tool in READING_INSPECTION_TOOL_DEFINITIONS],
            ["file_info", "image_info", "view_image"],
        )
        self.assertEqual(
            [tool["name"] for tool in READING_SOURCE_TOOL_DEFINITIONS],
            ["python_symbols", "code_outline", "python_check", "config_check"],
        )
        self.assertEqual(
            [tool["name"] for tool in CLAUDE_FILE_TOOL_DEFINITIONS],
            ["Read", "NotebookRead", "LS", "Glob", "Grep", "Write", "Edit", "NotebookEdit", "MultiEdit"],
        )

    def test_claude_file_definition_groups_preserve_domain_order(self) -> None:
        self.assertEqual([tool["name"] for tool in CLAUDE_READ_TOOL_DEFINITIONS], ["Read", "NotebookRead"])
        self.assertEqual([tool["name"] for tool in CLAUDE_SEARCH_TOOL_DEFINITIONS], ["LS", "Glob", "Grep"])
        self.assertEqual([tool["name"] for tool in CLAUDE_EDIT_TOOL_DEFINITIONS], ["Write", "Edit", "NotebookEdit", "MultiEdit"])
        self.assertEqual(
            CLAUDE_FILE_TOOL_DEFINITIONS,
            CLAUDE_READ_TOOL_DEFINITIONS + CLAUDE_SEARCH_TOOL_DEFINITIONS + CLAUDE_EDIT_TOOL_DEFINITIONS,
        )

    def test_claude_notebook_schemas_match_supported_parser_shapes(self) -> None:
        tools = {tool["name"]: tool for tool in CLAUDE_FILE_TOOL_DEFINITIONS}
        notebook_read_schema = tools["NotebookRead"]["input_schema"]
        notebook_edit_schema = tools["NotebookEdit"]["input_schema"]

        self.assertIn("include_outputs", notebook_read_schema["properties"])
        self.assertEqual(notebook_edit_schema["required"], ["notebook_path"])
        self.assertIn({"required": ["cell_id", "new_source"]}, notebook_edit_schema["anyOf"])
        self.assertIn({"required": ["cell_number", "new_source"]}, notebook_edit_schema["anyOf"])
        self.assertIn({"required": ["old_string", "new_string"]}, notebook_edit_schema["anyOf"])

    def test_claude_read_schema_exposes_supported_full_file_options(self) -> None:
        tools = {tool["name"]: tool for tool in CLAUDE_FILE_TOOL_DEFINITIONS}
        read_schema = tools["Read"]["input_schema"]

        read_range_schema = read_schema["properties"]["read_range"]

        self.assertIn("read_range", read_schema["properties"])
        self.assertEqual(len(read_range_schema["oneOf"]), 3)
        self.assertEqual(set(read_range_schema["oneOf"][0]["properties"]), {"start", "end", "start_line", "end_line"})
        self.assertEqual([branch["required"] for branch in read_range_schema["oneOf"][0]["anyOf"]], [["start", "end"], ["start_line", "end_line"]])
        self.assertFalse(read_range_schema["oneOf"][0]["additionalProperties"])
        self.assertIn("max_bytes", read_schema["properties"])
        self.assertIn("show_line_numbers", read_schema["properties"])
        self.assertNotIn("read_range", read_schema["required"])
        self.assertNotIn("max_bytes", read_schema["required"])
        self.assertNotIn("show_line_numbers", read_schema["required"])

    def test_claude_glob_schema_exposes_supported_limits(self) -> None:
        tools = {tool["name"]: tool for tool in CLAUDE_FILE_TOOL_DEFINITIONS}
        glob_schema = tools["Glob"]["input_schema"]

        self.assertIn("max_matches", glob_schema["properties"])
        self.assertIn("include_dirs", glob_schema["properties"])
        self.assertNotIn("max_matches", glob_schema["required"])
        self.assertNotIn("include_dirs", glob_schema["required"])

    def test_claude_ls_schema_exposes_supported_tree_limits(self) -> None:
        tools = {tool["name"]: tool for tool in CLAUDE_FILE_TOOL_DEFINITIONS}
        ls_schema = tools["LS"]["input_schema"]

        self.assertIn("ignore", ls_schema["properties"])
        self.assertEqual(ls_schema["properties"]["max_depth"]["maximum"], 10)
        self.assertEqual(ls_schema["properties"]["max_entries"]["maximum"], 1000)
        self.assertNotIn("ignore", ls_schema["required"])
        self.assertNotIn("max_depth", ls_schema["required"])
        self.assertNotIn("max_entries", ls_schema["required"])

    def test_claude_grep_schema_exposes_all_supported_output_modes(self) -> None:
        tools = {tool["name"]: tool for tool in CLAUDE_FILE_TOOL_DEFINITIONS}
        grep_schema = tools["Grep"]["input_schema"]

        self.assertEqual(
            grep_schema["properties"]["output_mode"]["enum"],
            ["lines", "content", "files_with_matches", "count"],
        )
        self.assertIn("regex", grep_schema["properties"])
        self.assertIn("case_sensitive", grep_schema["properties"])
        self.assertNotIn("regex", grep_schema["required"])
        self.assertNotIn("case_sensitive", grep_schema["required"])


if __name__ == "__main__":
    unittest.main()
