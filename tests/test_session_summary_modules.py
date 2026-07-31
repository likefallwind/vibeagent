import unittest

from vibeagent import session_summary_completion_reports
from vibeagent import session_summary_details
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

    def test_session_summary_details_parse_completion_and_subagent_labels(self) -> None:
        details = session_summary_details.parse_completion_detail_lists(
            {
                "pendingVerificationChecks": ["npm test", ""],
                "failedVerificationChecks": ["pytest"],
                "finalReviewBlockingIssues": ["syntax error"],
                "finalReviewChangedFiles": ["M app.py"],
                "toolErrors": ["read_file: boom"],
                "checkpointFailures": ["checkpoint_create: failed"],
                "activeBackgroundProcesses": ["proc-1"],
                "deniedApprovals": ["write_file app.py"],
                "nextActions": ["rerun checks"],
            }
        )

        self.assertEqual(details[0], ["npm test"])
        self.assertEqual(details[8], ["rerun checks"])
        self.assertEqual(
            session_summary_details.subagent_failure_label(
                {"task": "inspect", "agent": "reviewer", "mode": "read_only", "message": "failed"}
            ),
            "task=inspect; agent=reviewer; mode=read_only; message=failed",
        )


if __name__ == "__main__":
    unittest.main()
