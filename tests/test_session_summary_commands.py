from __future__ import annotations

import unittest

from vibeagent import session_commands, session_summary_commands


class SessionSummaryCommandsTests(unittest.TestCase):
    def test_session_commands_keeps_summary_formatters_compatible(self) -> None:
        missing = {"session": "missing", "exists": False, "message": "Session not found: missing"}
        no_sessions = {"session": None, "exists": False, "message": "No sessions found."}
        search = {
            "session": "run-1",
            "exists": True,
            "query": "needle",
            "caseSensitive": False,
            "matches": {"total": 0, "shown": 0, "omitted": 0, "items": []},
        }

        self.assertEqual(
            session_commands.format_session_summary_report_text(missing),
            session_summary_commands.format_session_summary_report_text(missing),
        )
        self.assertEqual(
            session_commands.format_session_plan_report_text(no_sessions),
            session_summary_commands.format_session_plan_report_text(no_sessions),
        )
        self.assertEqual(
            session_commands.format_session_transcript_report_text(no_sessions),
            session_summary_commands.format_session_transcript_report_text(no_sessions),
        )
        self.assertEqual(
            session_commands.format_session_search_report_text(search),
            session_summary_commands.format_session_search_report_text(search),
        )


if __name__ == "__main__":
    unittest.main()
