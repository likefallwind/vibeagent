from __future__ import annotations

import unittest

from vibeagent.tool_definition_claude_file import CLAUDE_FILE_TOOL_DEFINITIONS
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
            ["Read", "LS", "Glob", "Grep", "Write", "Edit", "MultiEdit"],
        )


if __name__ == "__main__":
    unittest.main()
