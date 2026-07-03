from __future__ import annotations

import unittest

from vibeagent import session_activity_commands, session_commands


class SessionActivityCommandsTests(unittest.TestCase):
    def test_session_commands_keeps_activity_command_exports(self) -> None:
        self.assertIs(
            session_commands.get_session_commands_text,
            session_activity_commands.get_session_commands_text,
        )
        self.assertIs(
            session_commands.get_session_commands_report,
            session_activity_commands.get_session_commands_report,
        )
        self.assertIs(
            session_commands.format_session_commands_report_text,
            session_activity_commands.format_session_commands_report_text,
        )
        self.assertIs(
            session_commands.get_session_files_text,
            session_activity_commands.get_session_files_text,
        )
        self.assertIs(
            session_commands.get_session_files_report,
            session_activity_commands.get_session_files_report,
        )
        self.assertIs(
            session_commands.format_session_files_report_text,
            session_activity_commands.format_session_files_report_text,
        )
        self.assertIs(
            session_commands.get_session_failures_text,
            session_activity_commands.get_session_failures_text,
        )
        self.assertIs(
            session_commands.get_session_failures_report,
            session_activity_commands.get_session_failures_report,
        )
        self.assertIs(
            session_commands.format_session_failures_report_text,
            session_activity_commands.format_session_failures_report_text,
        )


if __name__ == "__main__":
    unittest.main()
