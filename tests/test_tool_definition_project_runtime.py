from __future__ import annotations

import unittest

from vibeagent.tool_definition_command_runtime import COMMAND_RUNTIME_TOOL_DEFINITIONS
from vibeagent.tool_definition_git_reading import GIT_READING_TOOL_DEFINITIONS
from vibeagent.tool_definition_project_context import PROJECT_CONTEXT_TOOL_DEFINITIONS
from vibeagent.tool_definition_project_runtime import PROJECT_RUNTIME_TOOL_DEFINITIONS


class ProjectRuntimeToolDefinitionTests(unittest.TestCase):
    def test_project_runtime_definitions_are_split_in_order(self) -> None:
        self.assertEqual(
            PROJECT_RUNTIME_TOOL_DEFINITIONS,
            PROJECT_CONTEXT_TOOL_DEFINITIONS + COMMAND_RUNTIME_TOOL_DEFINITIONS + GIT_READING_TOOL_DEFINITIONS,
        )

    def test_project_runtime_definition_boundaries_remain_stable(self) -> None:
        self.assertEqual(PROJECT_CONTEXT_TOOL_DEFINITIONS[0]["name"], "project_commands")
        self.assertEqual(PROJECT_CONTEXT_TOOL_DEFINITIONS[-1]["name"], "project_overview")
        self.assertEqual(COMMAND_RUNTIME_TOOL_DEFINITIONS[0]["name"], "command_check")
        self.assertEqual(COMMAND_RUNTIME_TOOL_DEFINITIONS[-1]["name"], "environment_info")
        self.assertEqual(GIT_READING_TOOL_DEFINITIONS[0]["name"], "git_diff")
        self.assertEqual(GIT_READING_TOOL_DEFINITIONS[-1]["name"], "git_blame")


if __name__ == "__main__":
    unittest.main()
