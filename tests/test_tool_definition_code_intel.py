from __future__ import annotations

import unittest

from vibeagent.tool_definition_code_dependencies import CODE_DEPENDENCY_TOOL_DEFINITIONS
from vibeagent.tool_definition_code_intel import CODE_INTEL_TOOL_DEFINITIONS
from vibeagent.tool_definition_generic_code import GENERIC_CODE_TOOL_DEFINITIONS
from vibeagent.tool_definition_python_code import PYTHON_CODE_TOOL_DEFINITIONS
from vibeagent.tool_definition_search import SEARCH_TOOL_DEFINITIONS


class ToolDefinitionCodeIntelTests(unittest.TestCase):
    def test_code_intel_tool_definitions_are_grouped_in_original_order(self) -> None:
        self.assertEqual(
            CODE_INTEL_TOOL_DEFINITIONS,
            CODE_DEPENDENCY_TOOL_DEFINITIONS
            + GENERIC_CODE_TOOL_DEFINITIONS
            + PYTHON_CODE_TOOL_DEFINITIONS
            + SEARCH_TOOL_DEFINITIONS,
        )

    def test_group_boundaries_match_code_intel_domains(self) -> None:
        self.assertEqual([tool["name"] for tool in CODE_DEPENDENCY_TOOL_DEFINITIONS], ["python_dependencies", "code_dependencies"])
        self.assertEqual(
            [tool["name"] for tool in GENERIC_CODE_TOOL_DEFINITIONS],
            ["code_references", "code_reference_contexts", "code_definitions", "code_rename_preview", "code_rename"],
        )
        self.assertEqual(
            [tool["name"] for tool in PYTHON_CODE_TOOL_DEFINITIONS],
            [
                "python_definitions",
                "check_replace_python_definition",
                "replace_python_definition",
                "python_calls",
                "python_call_graph",
                "python_references",
                "python_reference_contexts",
                "python_rename_preview",
                "python_rename",
            ],
        )
        self.assertEqual([tool["name"] for tool in SEARCH_TOOL_DEFINITIONS], ["search", "search_contexts", "find_files", "glob"])


if __name__ == "__main__":
    unittest.main()
