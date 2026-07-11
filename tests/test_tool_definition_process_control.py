from __future__ import annotations

import unittest

from vibeagent.tool_definition_process_control import PROCESS_CONTROL_TOOL_DEFINITIONS
from vibeagent.tool_definition_process_io import PROCESS_IO_TOOL_DEFINITIONS
from vibeagent.tool_definition_process_output import PROCESS_OUTPUT_TOOL_DEFINITIONS
from vibeagent.tool_definition_process_run import PROCESS_RUN_TOOL_DEFINITIONS
from vibeagent.tool_definition_process_stop import PROCESS_STOP_TOOL_DEFINITIONS
from vibeagent.tool_definition_task_control import TASK_CONTROL_TOOL_DEFINITIONS


class ProcessControlToolDefinitionTests(unittest.TestCase):
    def test_process_control_tool_definitions_are_grouped_in_original_order(self) -> None:
        self.assertEqual(
            PROCESS_CONTROL_TOOL_DEFINITIONS,
            PROCESS_RUN_TOOL_DEFINITIONS
            + PROCESS_OUTPUT_TOOL_DEFINITIONS
            + PROCESS_IO_TOOL_DEFINITIONS
            + PROCESS_STOP_TOOL_DEFINITIONS
            + TASK_CONTROL_TOOL_DEFINITIONS,
        )

    def test_process_control_definition_boundaries_match_runtime_domains(self) -> None:
        self.assertEqual([tool["name"] for tool in PROCESS_RUN_TOOL_DEFINITIONS], ["run_command", "check_start_command", "start_command"])
        self.assertEqual(
            [tool["name"] for tool in PROCESS_OUTPUT_TOOL_DEFINITIONS],
            ["read_process", "process_output_contexts", "process_output_diagnostics"],
        )
        self.assertEqual([tool["name"] for tool in PROCESS_IO_TOOL_DEFINITIONS], ["wait_process", "check_write_process", "write_process"])
        self.assertEqual(
            [tool["name"] for tool in PROCESS_STOP_TOOL_DEFINITIONS],
            ["list_processes", "check_stop_all_processes", "check_stop_process", "stop_all_processes", "stop_process"],
        )
        self.assertEqual(
            [tool["name"] for tool in TASK_CONTROL_TOOL_DEFINITIONS],
            ["ask_user", "update_plan", "todo_write", "todo_read", "finish"],
        )

    def test_todo_write_schema_accepts_plan_or_todos(self) -> None:
        todo_write = next(tool for tool in TASK_CONTROL_TOOL_DEFINITIONS if tool["name"] == "todo_write")
        schema = todo_write["input_schema"]

        self.assertNotIn("required", schema)
        self.assertEqual([branch["required"] for branch in schema["anyOf"]], [["plan"], ["todos"]])
        self.assertIn("plan", schema["anyOf"][0]["properties"])
        self.assertIn("todos", schema["anyOf"][1]["properties"])


if __name__ == "__main__":
    unittest.main()
