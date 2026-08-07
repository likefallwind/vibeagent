import unittest

from vibeagent import session_summary_completion_reports
from vibeagent import session_summary_details
from vibeagent import session_summary_final_review
from vibeagent import session_summary_model
from vibeagent import session_summary_reports
from vibeagent import session_tool_result_failures
from vibeagent import session_utils


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

        self.assertEqual(details.pending_verification_checks, ["npm test"])
        self.assertEqual(details.next_actions, ["rerun checks"])
        self.assertEqual(
            session_summary_details.subagent_failure_label(
                {"task": "inspect", "agent": "reviewer", "mode": "read_only", "message": "failed"}
            ),
            "task=inspect; agent=reviewer; mode=read_only; message=failed",
        )

    def test_session_summary_details_merges_only_nonempty_completion_updates(self) -> None:
        previous = session_summary_details.parse_completion_detail_lists(
            {
                "pendingVerificationChecks": ["npm test"],
                "failedVerificationChecks": ["pytest"],
                "nextActions": ["rerun checks"],
            }
        )
        updates = session_summary_details.parse_completion_detail_lists(
            {
                "pendingVerificationChecks": [],
                "failedVerificationChecks": ["npm test"],
                "nextActions": ["finish"],
            }
        )

        merged = session_summary_details.merge_nonempty_completion_detail_lists(previous, updates)

        self.assertEqual(merged.pending_verification_checks, ["npm test"])
        self.assertEqual(merged.failed_verification_checks, ["npm test"])
        self.assertEqual(merged.next_actions, ["finish"])

    def test_session_summary_model_tracks_usage_and_final_messages(self) -> None:
        usage = session_summary_model.SessionModelUsageTotals()

        usage.add_payload(
            {
                "input_tokens": 3,
                "output_tokens": 4,
                "total_tokens": 7,
                "cache_creation_tokens": 2,
                "cache_read_tokens": 1,
            }
        )
        usage.add_payload({"input_tokens": 5, "output_tokens": 6})

        self.assertEqual(usage.input_tokens, 8)
        self.assertEqual(usage.output_tokens, 10)
        self.assertEqual(usage.total_tokens, 18)
        self.assertEqual(usage.cache_creation_tokens, 2)
        self.assertEqual(usage.cache_read_tokens, 1)
        self.assertEqual(session_summary_model.model_final_message([{"type": "text", "text": "done"}]), "done")
        self.assertIsNone(
            session_summary_model.model_final_message(
                [{"type": "text", "text": "thinking"}, {"type": "tool_call", "name": "read_file"}]
            )
        )
        self.assertEqual(session_summary_model.model_error_message({"message": " failed "}), "failed")

    def test_session_summary_final_review_parses_readiness_fields(self) -> None:
        review = session_summary_final_review.parse_final_review_summary(
            {
                "ready": False,
                "blocking_issues": ["syntax"],
                "warnings": ["large diff"],
                "total_files": 3,
                "files": [{"status": "M", "path": "app.py"}],
                "suggested_checks_total": 2,
                "suggested_checks": ["npm test"],
                "message": " review blocked ",
                "python": [{"path": "app.py", "ok": False, "message": "SyntaxError"}],
                "config": [{"path": "pyproject.toml", "ok": False, "message": "invalid"}],
            }
        )

        self.assertFalse(review.ready)
        self.assertEqual(review.blocking_issues, 1)
        self.assertEqual(review.warnings, 1)
        self.assertEqual(review.files, 3)
        self.assertEqual(review.changed_files, ["M app.py"])
        self.assertEqual(review.suggested_checks, 2)
        self.assertEqual(review.message, " review blocked ")
        self.assertEqual(review.python_failures, ["app.py: SyntaxError"])
        self.assertEqual(review.config_failures, ["pyproject.toml: invalid"])

    def test_session_utils_reexports_tool_result_failure_classifier(self) -> None:
        self.assertIs(session_utils.is_failed_tool_result, session_tool_result_failures.is_failed_tool_result)

    def test_tool_result_failure_classifier_handles_key_result_shapes(self) -> None:
        self.assertTrue(session_tool_result_failures.is_failed_tool_result({"kind": "tool_error"}))
        self.assertTrue(
            session_tool_result_failures.is_failed_tool_result(
                {"kind": "read_files", "files": [{"ok": True}, {"ok": False}]}
            )
        )
        self.assertTrue(
            session_tool_result_failures.is_failed_tool_result(
                {"kind": "run_command", "result": {"exit_code": 1, "timed_out": False}}
            )
        )
        self.assertFalse(
            session_tool_result_failures.is_failed_tool_result(
                {"kind": "run_command", "result": {"exit_code": 0, "timed_out": False}}
            )
        )


if __name__ == "__main__":
    unittest.main()
