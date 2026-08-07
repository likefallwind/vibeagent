from __future__ import annotations

import unittest

from vibeagent.action_parsing import parse_tool_action
from vibeagent.action_parsing_session import SESSION_ACTION_TYPES
from vibeagent.action_parsing_session_output import SESSION_OUTPUT_ACTION_TYPES, parse_session_output_action
from vibeagent.types import SessionCommandsAction, SessionOutputContextsAction, SessionOutputDiagnosticsAction


class ActionParsingSessionOutputTests(unittest.TestCase):
    def test_session_parser_keeps_output_action_types_registered(self) -> None:
        self.assertLessEqual(SESSION_OUTPUT_ACTION_TYPES, SESSION_ACTION_TYPES)
        self.assertIsNone(parse_session_output_action("session_summary", {}, "raw"))

    def test_parse_session_commands_keeps_default_output_limit(self) -> None:
        action = parse_tool_action("session_commands", {"run_id": " run-1 ", "max_commands": 3})

        self.assertEqual(
            action,
            SessionCommandsAction(type="session_commands", run_id="run-1", max_commands=3, max_output_chars=2_000),
        )

    def test_parse_session_output_contexts_keeps_context_options(self) -> None:
        action = parse_tool_action(
            "session_output_contexts",
            {
                "run_id": "run-2",
                "max_commands": 4,
                "max_output_chars": 5000,
                "context_lines": 6,
                "max_contexts": 7,
                "max_bytes_per_context": 8000,
            },
        )

        self.assertEqual(
            action,
            SessionOutputContextsAction(
                type="session_output_contexts",
                run_id="run-2",
                max_commands=4,
                max_output_chars=5000,
                context_lines=6,
                max_contexts=7,
                max_bytes_per_context=8000,
            ),
        )

    def test_parse_session_output_diagnostics_keeps_diagnostic_options(self) -> None:
        action = parse_tool_action(
            "session_output_diagnostics",
            {
                "run_id": "run-3",
                "max_commands": 5,
                "max_output_chars": 6000,
                "context_lines": 1,
                "max_diagnostics": 2,
                "max_contexts": 3,
                "max_bytes_per_context": 4000,
            },
        )

        self.assertEqual(
            action,
            SessionOutputDiagnosticsAction(
                type="session_output_diagnostics",
                run_id="run-3",
                max_commands=5,
                max_output_chars=6000,
                context_lines=1,
                max_diagnostics=2,
                max_contexts=3,
                max_bytes_per_context=4000,
            ),
        )


if __name__ == "__main__":
    unittest.main()
