import unittest
from types import SimpleNamespace

from vibeagent.prompt_next_action_session_formatting import (
    audit_section_items,
    completion_blocker_labels,
    file_reference_labels,
    format_next_action_items,
    has_completion_blocker_signal,
    plan_item_labels,
    session_audit_process_labels,
    session_plan_appears_complete,
    session_plan_has_unfinished_work,
    text_reports_ready,
    verification_command_labels,
)


class PromptNextActionSessionFormattingTests(unittest.TestCase):
    def test_format_next_action_items_limits_output(self) -> None:
        self.assertEqual(format_next_action_items(["one", "two", "three", "four"]), "one; two; three; +1 more")

    def test_text_reports_ready_matches_summary_readiness_markers(self) -> None:
        self.assertTrue(text_reports_ready("Session summary:\n  ready: yes"))
        self.assertTrue(text_reports_ready("Session handoff:\n  status: READY"))
        self.assertFalse(text_reports_ready("Session summary:\n  status: active"))

    def test_session_plan_status_helpers_prioritize_unfinished_markers(self) -> None:
        self.assertTrue(session_plan_has_unfinished_work("- [not done] finish tests"))
        self.assertTrue(session_plan_has_unfinished_work("- [undone] review changes"))
        self.assertTrue(session_plan_has_unfinished_work("- [to-do] run final checks"))
        self.assertFalse(session_plan_appears_complete("- [not done] finish tests"))
        self.assertFalse(session_plan_appears_complete("- [pending] run tests"))
        self.assertTrue(session_plan_appears_complete("- [completed] run tests"))

    def test_verification_command_labels_include_cwd_and_reason(self) -> None:
        labels = verification_command_labels(
            [
                {"command": "npm test", "cwd": "web", "failureReason": "exit 1"},
                {"command": "python -m unittest", "cwd": "", "failureReason": ""},
                {"cwd": "."},
            ]
        )

        self.assertEqual(labels, ["npm test (cwd=web): exit 1", "python -m unittest (cwd=.)"])

    def test_audit_and_completion_blockers_parse_report_sections(self) -> None:
        observation = SimpleNamespace(
            completion_blockers=[],
            latest_completion_blockers=[],
            audit="\n".join(
                [
                    "completionBlockers:",
                    "- run verification",
                    "- none",
                    "Other:",
                    "- ignored",
                ]
            ),
        )

        self.assertEqual(audit_section_items(observation.audit, ("completionBlockers",)), ["run verification"])
        self.assertEqual(completion_blocker_labels(observation), ["run verification"])
        self.assertTrue(has_completion_blocker_signal([], observation))

    def test_completion_blocker_signal_uses_structured_fields_first(self) -> None:
        observation = SimpleNamespace(
            completion_ready=False,
            completion_blockers=[" finish tests "],
            latest_completion_blockers=["commit changes"],
            audit="completionReady: yes",
        )

        self.assertEqual(completion_blocker_labels(observation), ["finish tests", "commit changes"])
        self.assertTrue(has_completion_blocker_signal([], observation))

    def test_labels_filter_empty_inputs(self) -> None:
        process = SimpleNamespace(process_id="p1", command="npm run dev", cwd="web")

        self.assertEqual(session_audit_process_labels([process]), ["p1: npm run dev (cwd=web)"])
        self.assertEqual(plan_item_labels([{"status": "pending", "step": "run tests"}, {"status": "done"}]), ["pending: run tests"])
        self.assertEqual(file_reference_labels([{"path": "vibeagent/agent.py", "uses": ["edit", " verify "]}]), ["vibeagent/agent.py (uses: edit, verify)"])


if __name__ == "__main__":
    unittest.main()
