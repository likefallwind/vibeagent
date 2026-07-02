from __future__ import annotations

import unittest

from vibeagent import session_accounting_commands, session_commands


class SessionAccountingCommandsTests(unittest.TestCase):
    def test_session_commands_keeps_accounting_formatters_compatible(self) -> None:
        sessions_report = {"exists": False, "message": "No sessions found."}
        usage_report = {"exists": False, "message": "No sessions found."}
        cost_report = {"exists": False, "message": "No sessions found."}

        self.assertEqual(
            session_commands.format_sessions_report_text(sessions_report),
            session_accounting_commands.format_sessions_report_text(sessions_report),
        )
        self.assertEqual(
            session_commands.format_usage_report_text(usage_report),
            session_accounting_commands.format_usage_report_text(usage_report),
        )
        self.assertEqual(
            session_commands.format_cost_report_text(cost_report),
            session_accounting_commands.format_cost_report_text(cost_report),
        )


if __name__ == "__main__":
    unittest.main()
