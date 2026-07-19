from __future__ import annotations

import unittest

from vibeagent import action_parsing_helpers
from vibeagent.action_parsing_run_commands import parse_run_command_items
from vibeagent.action_parsing_scalars import ActionParseError
from vibeagent.types import RunCommandItem


class ActionParsingRunCommandsTests(unittest.TestCase):
    def test_helpers_reexport_run_command_item_parser(self) -> None:
        self.assertIs(action_parsing_helpers.parse_run_command_items, parse_run_command_items)

    def test_parse_run_command_items_parses_execution_options(self) -> None:
        items = parse_run_command_items(
            [
                {
                    "command": " python3 -m unittest ",
                    "cwd": "tests",
                    "description": "run tests",
                    "timeout_ms": 1000,
                    "max_output_chars": 2000,
                    "extract_output_contexts": True,
                    "extract_output_diagnostics": True,
                    "context_lines": 2,
                    "max_diagnostics": 3,
                    "max_contexts": 4,
                    "max_bytes_per_context": 5000,
                }
            ],
            "raw",
            "run_commands",
        )

        self.assertEqual(
            items,
            [
                RunCommandItem(
                    command="python3 -m unittest",
                    timeout_ms=1000,
                    cwd="tests",
                    max_output_chars=2000,
                    extract_output_contexts=True,
                    extract_output_diagnostics=True,
                    context_lines=2,
                    max_diagnostics=3,
                    max_contexts=4,
                    max_bytes_per_context=5000,
                    description="run tests",
                )
            ],
        )

    def test_parse_run_command_items_rejects_invalid_options(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "requires a non-empty commands list"):
            parse_run_command_items([], "raw", "check_run_commands")
        with self.assertRaisesRegex(ActionParseError, "cwd must be a string"):
            parse_run_command_items([{"command": "python3 --version", "cwd": 1}], "raw", "run_commands")
        with self.assertRaisesRegex(ActionParseError, "max_bytes_per_context must be at least 1000"):
            parse_run_command_items([{"command": "python3 --version", "max_bytes_per_context": 999}], "raw", "run_commands")


if __name__ == "__main__":
    unittest.main()
