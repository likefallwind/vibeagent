from __future__ import annotations

import unittest

from vibeagent.action_parsing import parse_tool_action
from vibeagent.action_parsing_read import READ_ACTION_TYPES
from vibeagent.action_parsing_read_output import READ_OUTPUT_ACTION_TYPES, parse_read_output_action
from vibeagent.types import OutputContextsAction, OutputDiagnosticsAction


class ActionParsingReadOutputTests(unittest.TestCase):
    def test_read_parser_keeps_output_action_types_registered(self) -> None:
        self.assertLessEqual(READ_OUTPUT_ACTION_TYPES, READ_ACTION_TYPES)
        self.assertIsNone(parse_read_output_action("read_file", {"path": "app.py"}, "raw"))

    def test_parse_output_contexts_keeps_limits(self) -> None:
        action = parse_tool_action(
            "output_contexts",
            {
                "text": "src/app.py:2: failed",
                "context_lines": 3,
                "max_contexts": 4,
                "max_bytes_per_context": 1000,
            },
        )

        self.assertIsInstance(action, OutputContextsAction)
        self.assertEqual(action.text, "src/app.py:2: failed")
        self.assertEqual(action.context_lines, 3)
        self.assertEqual(action.max_contexts, 4)
        self.assertEqual(action.max_bytes_per_context, 1000)

    def test_parse_python_traceback_maps_to_output_diagnostics(self) -> None:
        action = parse_tool_action(
            "python_traceback",
            {
                "text": "Traceback\n  File \"src/app.py\", line 2",
                "context_lines": 1,
                "max_diagnostics": 2,
                "max_contexts": 3,
                "max_bytes_per_context": 1000,
            },
        )

        self.assertIsInstance(action, OutputDiagnosticsAction)
        self.assertEqual(action.type, "output_diagnostics")
        self.assertEqual(action.context_lines, 1)
        self.assertEqual(action.max_diagnostics, 2)
        self.assertEqual(action.max_contexts, 3)
        self.assertEqual(action.max_bytes_per_context, 1000)


if __name__ == "__main__":
    unittest.main()
