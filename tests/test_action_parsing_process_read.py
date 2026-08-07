from __future__ import annotations

import unittest

from vibeagent.action_parsing import parse_tool_action
from vibeagent.action_parsing_process import PROCESS_ACTION_TYPES
from vibeagent.action_parsing_process_read import PROCESS_READ_ACTION_TYPES, parse_process_read_action
from vibeagent.types import ListProcessesAction, ProcessOutputDiagnosticsAction, ReadProcessAction


class ActionParsingProcessReadTests(unittest.TestCase):
    def test_process_parser_keeps_read_action_types_registered(self) -> None:
        self.assertLessEqual(PROCESS_READ_ACTION_TYPES, PROCESS_ACTION_TYPES)
        self.assertIsNone(parse_process_read_action("start_command", {"command": "npm test"}, "raw"))

    def test_parse_read_process_keeps_filter_and_limit(self) -> None:
        action = parse_tool_action(
            "read_process",
            {"process_id": "bg-1", "max_output_chars": 2000, "output_filter": "error|failed"},
        )

        self.assertEqual(
            action,
            ReadProcessAction(
                type="read_process",
                process_id="bg-1",
                max_output_chars=2000,
                output_filter="error|failed",
            ),
        )

    def test_parse_process_output_diagnostics_keeps_context_options(self) -> None:
        action = parse_tool_action(
            "process_output_diagnostics",
            {
                "process_id": "bg-2",
                "max_output_chars": 3000,
                "context_lines": 4,
                "max_diagnostics": 6,
                "max_contexts": 8,
                "max_bytes_per_context": 10_000,
            },
        )

        self.assertEqual(
            action,
            ProcessOutputDiagnosticsAction(
                type="process_output_diagnostics",
                process_id="bg-2",
                max_output_chars=3000,
                context_lines=4,
                max_diagnostics=6,
                max_contexts=8,
                max_bytes_per_context=10_000,
            ),
        )

    def test_parse_list_processes(self) -> None:
        self.assertEqual(parse_tool_action("list_processes", {}), ListProcessesAction(type="list_processes"))


if __name__ == "__main__":
    unittest.main()
