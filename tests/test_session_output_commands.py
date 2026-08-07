from __future__ import annotations

import unittest

from vibeagent import session_commands, session_output_commands, session_output_formatting


class SessionOutputCommandModuleTests(unittest.TestCase):
    def test_session_commands_keeps_output_command_exports(self) -> None:
        self.assertIs(
            session_commands.get_session_output_contexts_text,
            session_output_commands.get_session_output_contexts_text,
        )
        self.assertIs(
            session_commands.get_session_output_contexts_observation,
            session_output_commands.get_session_output_contexts_observation,
        )
        self.assertIs(
            session_commands.get_session_output_contexts_report,
            session_output_commands.get_session_output_contexts_report,
        )
        self.assertIs(
            session_commands.format_session_output_contexts_report_text,
            session_output_commands.format_session_output_contexts_report_text,
        )
        self.assertIs(
            session_output_commands.format_session_output_contexts_report_text,
            session_output_formatting.format_session_output_contexts_report_text,
        )
        self.assertIs(
            session_output_commands._format_output_context_item_text,
            session_output_formatting.format_output_context_item_text,
        )
        self.assertIs(session_output_commands._indent_block, session_output_formatting.indent_block)
        self.assertIs(
            session_commands.get_session_output_diagnostics_text,
            session_output_commands.get_session_output_diagnostics_text,
        )
        self.assertIs(
            session_commands.get_session_output_diagnostics_observation,
            session_output_commands.get_session_output_diagnostics_observation,
        )
        self.assertIs(
            session_commands.get_session_output_diagnostics_report,
            session_output_commands.get_session_output_diagnostics_report,
        )
        self.assertIs(
            session_commands.format_session_output_diagnostics_report_text,
            session_output_commands.format_session_output_diagnostics_report_text,
        )
        self.assertIs(
            session_output_commands.format_session_output_diagnostics_report_text,
            session_output_formatting.format_session_output_diagnostics_report_text,
        )


if __name__ == "__main__":
    unittest.main()
