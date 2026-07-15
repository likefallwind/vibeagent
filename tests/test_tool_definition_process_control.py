from __future__ import annotations

import unittest

from vibeagent.tool_definition_claude_process import CLAUDE_PROCESS_TOOL_DEFINITIONS
from vibeagent.tool_definition_process_control import PROCESS_CONTROL_TOOL_DEFINITIONS
from vibeagent.tool_definition_process_io import PROCESS_IO_TOOL_DEFINITIONS
from vibeagent.tool_definition_process_output import PROCESS_OUTPUT_TOOL_DEFINITIONS
from vibeagent.tool_definition_process_run import PROCESS_RUN_TOOL_DEFINITIONS
from vibeagent.tool_definition_process_stop import PROCESS_STOP_TOOL_DEFINITIONS
from vibeagent.tool_definition_task_control import PLAN_ITEM_SCHEMA, TASK_CONTROL_TOOL_DEFINITIONS, TODO_ITEM_SCHEMA


class ProcessControlToolDefinitionTests(unittest.TestCase):
    def test_process_control_tool_definitions_are_grouped_in_original_order(self) -> None:
        self.assertEqual(
            PROCESS_CONTROL_TOOL_DEFINITIONS,
            PROCESS_RUN_TOOL_DEFINITIONS
            + PROCESS_OUTPUT_TOOL_DEFINITIONS
            + PROCESS_IO_TOOL_DEFINITIONS
            + PROCESS_STOP_TOOL_DEFINITIONS
            + TASK_CONTROL_TOOL_DEFINITIONS
            + CLAUDE_PROCESS_TOOL_DEFINITIONS,
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
            [
                "ask_user",
                "AskUserQuestion",
                "update_plan",
                "todo_write",
                "todo_read",
                "TodoRead",
                "TodoWrite",
                "ExitPlanMode",
                "finish",
            ],
        )
        self.assertEqual(
            [tool["name"] for tool in CLAUDE_PROCESS_TOOL_DEFINITIONS],
            ["Bash", "BashOutput", "KillBash"],
        )

    def test_todo_write_schema_accepts_plan_or_todos(self) -> None:
        todo_write = next(tool for tool in TASK_CONTROL_TOOL_DEFINITIONS if tool["name"] == "todo_write")
        schema = todo_write["input_schema"]

        self.assertNotIn("required", schema)
        self.assertEqual([branch["required"] for branch in schema["anyOf"]], [["plan"], ["todos"]])
        self.assertIn("plan", schema["anyOf"][0]["properties"])
        self.assertIn("todos", schema["anyOf"][1]["properties"])

    def test_task_control_plan_and_todo_item_schemas_are_shared(self) -> None:
        update_plan = next(tool for tool in TASK_CONTROL_TOOL_DEFINITIONS if tool["name"] == "update_plan")
        todo_write = next(tool for tool in TASK_CONTROL_TOOL_DEFINITIONS if tool["name"] == "todo_write")

        self.assertIs(update_plan["input_schema"]["properties"]["plan"]["items"], PLAN_ITEM_SCHEMA)
        self.assertIs(todo_write["input_schema"]["properties"]["plan"]["items"], PLAN_ITEM_SCHEMA)
        self.assertIs(todo_write["input_schema"]["anyOf"][0]["properties"]["plan"]["items"], PLAN_ITEM_SCHEMA)
        self.assertIs(todo_write["input_schema"]["properties"]["todos"]["items"], TODO_ITEM_SCHEMA)
        self.assertIs(todo_write["input_schema"]["anyOf"][1]["properties"]["todos"]["items"], TODO_ITEM_SCHEMA)

    def test_task_control_status_schemas_accept_aliases(self) -> None:
        self.assertEqual(
            PLAN_ITEM_SCHEMA["properties"]["status"]["enum"],
            [
                "active",
                "complete",
                "completed",
                "doing",
                "done",
                "finished",
                "in-progress",
                "in_progress",
                "not started",
                "not-started",
                "not_started",
                "open",
                "pending",
                "queued",
                "started",
                "succeeded",
                "success",
                "to do",
                "to-do",
                "to_do",
                "todo",
            ],
        )
        self.assertIs(TODO_ITEM_SCHEMA["properties"]["status"]["enum"], PLAN_ITEM_SCHEMA["properties"]["status"]["enum"])


if __name__ == "__main__":
    unittest.main()
