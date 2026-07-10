import unittest

from vibeagent.tool_definition_command_runtime import COMMAND_RUNTIME_TOOL_DEFINITIONS
from vibeagent.tool_definition_command_sequences import COMMAND_SEQUENCE_TOOL_DEFINITIONS
from vibeagent.tool_definition_environment_runtime import ENVIRONMENT_RUNTIME_TOOL_DEFINITIONS
from vibeagent.tool_definition_runtime_network import RUNTIME_NETWORK_TOOL_DEFINITIONS


class CommandRuntimeToolDefinitionTests(unittest.TestCase):
    def test_command_runtime_definitions_are_split_in_order(self) -> None:
        self.assertEqual(
            COMMAND_RUNTIME_TOOL_DEFINITIONS,
            COMMAND_SEQUENCE_TOOL_DEFINITIONS
            + RUNTIME_NETWORK_TOOL_DEFINITIONS
            + ENVIRONMENT_RUNTIME_TOOL_DEFINITIONS,
        )

    def test_command_runtime_definition_boundaries_remain_stable(self) -> None:
        self.assertEqual(COMMAND_SEQUENCE_TOOL_DEFINITIONS[0]["name"], "command_check")
        self.assertEqual(COMMAND_SEQUENCE_TOOL_DEFINITIONS[-1]["name"], "run_commands")
        self.assertEqual(RUNTIME_NETWORK_TOOL_DEFINITIONS[0]["name"], "port_check")
        self.assertEqual(RUNTIME_NETWORK_TOOL_DEFINITIONS[-1]["name"], "web_fetch")
        self.assertEqual(ENVIRONMENT_RUNTIME_TOOL_DEFINITIONS[0]["name"], "environment_info")

    def test_command_runtime_tool_names_remain_in_original_order(self) -> None:
        self.assertEqual(
            [tool["name"] for tool in COMMAND_RUNTIME_TOOL_DEFINITIONS],
            [
                "command_check",
                "check_run_commands",
                "run_commands",
                "port_check",
                "http_check",
                "http_fetch",
                "web_fetch",
                "environment_info",
            ],
        )


if __name__ == "__main__":
    unittest.main()
