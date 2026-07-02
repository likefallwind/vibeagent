import unittest

from vibeagent import session
from vibeagent import session_event_report_commands


class SessionEventReportCommandsTests(unittest.TestCase):
    def test_session_module_reexports_event_report_commands(self) -> None:
        self.assertIs(
            session.format_session_transcript,
            session_event_report_commands.format_session_transcript,
        )
        self.assertIs(
            session.build_session_transcript_report,
            session_event_report_commands.build_session_transcript_report,
        )
        self.assertIs(session.format_session_search, session_event_report_commands.format_session_search)
        self.assertIs(
            session.build_session_search_report,
            session_event_report_commands.build_session_search_report,
        )
        self.assertIs(session.session_search_matches, session_event_report_commands.session_search_matches)
        self.assertIs(session.format_session_commands, session_event_report_commands.format_session_commands)
        self.assertIs(
            session.build_session_commands_report,
            session_event_report_commands.build_session_commands_report,
        )


if __name__ == "__main__":
    unittest.main()
