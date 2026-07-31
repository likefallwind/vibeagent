import unittest

from vibeagent import session_summary_completion_reports
from vibeagent import session_summary_reports


class SessionSummaryModuleTests(unittest.TestCase):
    def test_session_summary_reports_reexports_completion_helpers(self) -> None:
        self.assertIs(
            session_summary_reports.final_review_resolved_by_completion,
            session_summary_completion_reports.final_review_resolved_by_completion,
        )
        self.assertIs(
            session_summary_reports.format_final_review_failure_lines,
            session_summary_completion_reports.format_final_review_failure_lines,
        )
        self.assertIs(
            session_summary_reports.format_latest_completion_detail_lines,
            session_summary_completion_reports.format_latest_completion_detail_lines,
        )


if __name__ == "__main__":
    unittest.main()
