import unittest

from vibeagent.session_handoff_details import extract_session_handoff_details


class SessionHandoffDetailsTests(unittest.TestCase):
    def test_extracts_latest_completion_detail_fields(self) -> None:
        report = {
            "ready": False,
            "status": "blocked",
            "audit": {
                "completion": {
                    "ready": False,
                    "blockers": ["Run did not complete successfully."],
                    "latestBlockers": ["Task plan still has unfinished item(s): 1 in_progress."],
                    "latestPendingVerificationChecks": ["npm test"],
                    "latestFailedVerificationChecks": ["npm run build (exit=1)"],
                    "latestFinalReviewBlockingIssues": ["Changed Python files have syntax errors."],
                    "latestFinalReviewChangedFiles": ["M app.py"],
                    "latestToolErrors": ["read_file: Tool execution failed: boom"],
                    "latestCheckpointFailures": ["checkpoint_create: git diff failed."],
                    "latestActiveBackgroundProcesses": ["bg-1: pid=123, cwd=web, command=npm run dev"],
                    "latestDeniedApprovals": ["write_file note.txt: Denied by policy."],
                },
            },
        }

        details = extract_session_handoff_details(report)

        self.assertEqual(details.completion_blockers, ["Run did not complete successfully."])
        self.assertEqual(details.latest_completion_blockers, ["Task plan still has unfinished item(s): 1 in_progress."])
        self.assertEqual(details.latest_completion_pending_verification_checks, ["npm test"])
        self.assertEqual(details.latest_completion_failed_verification_checks, ["npm run build (exit=1)"])
        self.assertEqual(details.latest_completion_final_review_issues, ["Changed Python files have syntax errors."])
        self.assertEqual(details.latest_completion_final_review_changed_files, ["M app.py"])
        self.assertEqual(details.latest_completion_tool_errors, ["read_file: Tool execution failed: boom"])
        self.assertEqual(details.latest_completion_checkpoint_failures, ["checkpoint_create: git diff failed."])
        self.assertEqual(
            details.latest_completion_active_background_processes,
            ["bg-1: pid=123, cwd=web, command=npm run dev"],
        )
        self.assertEqual(details.latest_completion_denied_approvals, ["write_file note.txt: Denied by policy."])

    def test_extracts_latest_subagent_failures_from_audit_summary(self) -> None:
        report = {
            "ready": False,
            "status": "blocked",
            "audit": {
                "summary": {
                    "latestSubagentFailures": [
                        " task=Inspect; agent=context-reader; mode=read-only; message=failed. ",
                        "",
                        123,
                    ],
                },
            },
        }

        details = extract_session_handoff_details(report)

        self.assertEqual(
            details.latest_subagent_failures,
            ["task=Inspect; agent=context-reader; mode=read-only; message=failed."],
        )

    def test_extracts_legacy_top_level_latest_subagent_failures(self) -> None:
        report = {
            "ready": False,
            "status": "blocked",
            "audit": {
                "latestSubagentFailures": [" task=Legacy; agent=reader; mode=explore; message=failed. "],
            },
        }

        details = extract_session_handoff_details(report)

        self.assertEqual(
            details.latest_subagent_failures,
            ["task=Legacy; agent=reader; mode=explore; message=failed."],
        )


if __name__ == "__main__":
    unittest.main()
