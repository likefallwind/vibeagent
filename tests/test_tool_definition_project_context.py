import unittest

from vibeagent.tool_definition_project_commands import PROJECT_COMMAND_TOOL_DEFINITIONS
from vibeagent.tool_definition_project_context import PROJECT_CONTEXT_TOOL_DEFINITIONS
from vibeagent.tool_definition_project_metadata import PROJECT_METADATA_TOOL_DEFINITIONS
from vibeagent.tool_definition_project_tests import PROJECT_TEST_TOOL_DEFINITIONS
from vibeagent.tool_definition_project_tools import PROJECT_TOOL_CATALOG_TOOL_DEFINITIONS


class ProjectContextToolDefinitionTests(unittest.TestCase):
    def test_project_context_definitions_are_split_in_order(self) -> None:
        self.assertEqual(
            PROJECT_CONTEXT_TOOL_DEFINITIONS,
            PROJECT_COMMAND_TOOL_DEFINITIONS
            + PROJECT_TOOL_CATALOG_TOOL_DEFINITIONS
            + PROJECT_TEST_TOOL_DEFINITIONS
            + PROJECT_METADATA_TOOL_DEFINITIONS,
        )

    def test_project_context_definition_boundaries_remain_stable(self) -> None:
        self.assertEqual(PROJECT_COMMAND_TOOL_DEFINITIONS[0]["name"], "project_commands")
        self.assertEqual(PROJECT_TOOL_CATALOG_TOOL_DEFINITIONS[0]["name"], "tool_search")
        self.assertEqual(PROJECT_TEST_TOOL_DEFINITIONS[0]["name"], "related_tests")
        self.assertEqual(PROJECT_TEST_TOOL_DEFINITIONS[-1]["name"], "run_focused_test_commands")
        self.assertEqual(PROJECT_METADATA_TOOL_DEFINITIONS[0]["name"], "project_manifests")
        self.assertEqual(PROJECT_METADATA_TOOL_DEFINITIONS[-1]["name"], "project_overview")

    def test_project_context_tool_names_remain_in_original_order(self) -> None:
        self.assertEqual(
            [tool["name"] for tool in PROJECT_CONTEXT_TOOL_DEFINITIONS],
            [
                "project_commands",
                "tool_search",
                "ToolSearch",
                "related_tests",
                "focused_test_commands",
                "check_focused_test_commands",
                "run_focused_test_commands",
                "project_manifests",
                "project_instructions",
                "project_skills",
                "project_agents",
                "skill",
                "Skill",
                "project_todos",
                "project_overview",
            ],
        )


if __name__ == "__main__":
    unittest.main()
