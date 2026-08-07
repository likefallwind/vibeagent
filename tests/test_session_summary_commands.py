from __future__ import annotations

import unittest

from vibeagent import (
    session_commands,
    session_plan_commands,
    session_search_commands,
    session_summary_commands,
    session_summary_formatting,
    session_transcript_commands,
)


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
        self.assertIs(session_summary_commands._clip, session_summary_formatting.clip)
        self.assertIs(session_summary_commands._format_name_counts, session_summary_formatting.format_name_counts)
        self.assertIs(
            session_summary_commands.format_session_plan_report_text,
            session_plan_commands.format_session_plan_report_text,
        )
        self.assertIs(
            session_summary_commands.format_session_transcript_report_text,
            session_transcript_commands.format_session_transcript_report_text,
        )
        self.assertIs(
            session_summary_commands.format_session_search_report_text,
            session_search_commands.format_session_search_report_text,
        )
        self.assertIs(session_summary_commands.get_session_search_report, session_search_commands.get_session_search_report)
        self.assertIs(session_summary_commands.get_session_search_text, session_search_commands.get_session_search_text)
        self.assertIs(session_summary_commands.SESSION_SEARCH_USAGE, session_search_commands.SESSION_SEARCH_USAGE)
        self.assertIs(session_summary_commands.get_transcript_report, session_transcript_commands.get_transcript_report)
        self.assertIs(session_summary_commands.get_transcript_text, session_transcript_commands.get_transcript_text)
        self.assertIs(session_summary_commands.get_plan_report, session_plan_commands.get_plan_report)
        self.assertIs(session_summary_commands.get_plan_text, session_plan_commands.get_plan_text)

    def test_session_summary_report_formats_limited_completion_detail_sections(self) -> None:
        report = {
            "session": "run-1",
            "exists": True,
            "status": "blocked",
            "events": {"total": 1, "iterations": 1},
            "toolCalls": {"names": []},
            "approvals": {},
            "completion": {
                "ready": False,
                "blockers": [],
                "warnings": [],
                "blockedCount": 1,
                "latestToolErrors": ["", "  ", *[f"tool error {index}" for index in range(12)]],
            },
        }

        text = session_summary_commands.format_session_summary_report_text(report)

        self.assertIn("  completion: ready=no, blockers=0, warnings=0, blockedAttempts=1", text)
        self.assertIn("    latestCompletionToolErrors:", text)
        self.assertIn("      - tool error 0", text)
        self.assertIn("      - tool error 9", text)
        self.assertIn("      - ... 2 more", text)
        self.assertNotIn("tool error 10", text)
        self.assertNotIn("tool error 11", text)


if __name__ == "__main__":
    unittest.main()
