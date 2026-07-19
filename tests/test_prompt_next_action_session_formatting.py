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
    subagent_failure_labels,
    text_section_items,
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
        self.assertTrue(session_plan_has_unfinished_work("- [ ] finish tests"))
        self.assertTrue(session_plan_has_unfinished_work("1. [ ] finish tests"))
        self.assertTrue(session_plan_has_unfinished_work("2) [ ] review changes"))
        self.assertTrue(session_plan_has_unfinished_work("- ☐ finish tests"))
        self.assertTrue(session_plan_has_unfinished_work("☐ finish tests"))
        self.assertTrue(session_plan_has_unfinished_work("- [not done] finish tests"))
        self.assertTrue(session_plan_has_unfinished_work("- [undone] review changes"))
        self.assertTrue(session_plan_has_unfinished_work("- [to-do] run final checks"))
        self.assertFalse(session_plan_appears_complete("- [ ] finish tests"))
        self.assertFalse(session_plan_appears_complete("- [not done] finish tests"))
        self.assertFalse(session_plan_appears_complete("- [pending] run tests"))
        self.assertTrue(session_plan_appears_complete("- [x] run tests"))
        self.assertTrue(session_plan_appears_complete("* [X] run tests"))
        self.assertTrue(session_plan_appears_complete("+ [x] run tests"))
        self.assertTrue(session_plan_appears_complete("1. [x] run tests"))
        self.assertTrue(session_plan_appears_complete("- ☑ run tests"))
        self.assertTrue(session_plan_appears_complete("✅ run tests"))
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

        self.assertEqual(text_section_items(observation.audit, ("completionBlockers",)), ["run verification"])
        self.assertEqual(audit_section_items(observation.audit, ("completionBlockers",)), ["run verification"])
        self.assertEqual(completion_blocker_labels(observation), ["run verification"])
        self.assertTrue(has_completion_blocker_signal([], observation))

    def test_completion_blockers_parse_handoff_or_summary_report_sections(self) -> None:
        handoff_observation = SimpleNamespace(
            completion_blockers=[],
            latest_completion_blockers=[],
            audit="",
            handoff="\n".join(
                [
                    "completionBlockers:",
                    "- resolve failed smoke test",
                ]
            ),
            summary="",
        )
        summary_observation = SimpleNamespace(
            completion_blockers=[],
            latest_completion_blockers=[],
            audit="",
            handoff="",
            summary="\n".join(
                [
                    "latestCompletionBlockers:",
                    "- commit validated stage",
                ]
            ),
        )

        self.assertEqual(completion_blocker_labels(handoff_observation), ["resolve failed smoke test"])
        self.assertTrue(has_completion_blocker_signal([], handoff_observation))
        self.assertEqual(completion_blocker_labels(summary_observation), ["commit validated stage"])
        self.assertTrue(has_completion_blocker_signal([], summary_observation))

    def test_completion_blocker_signal_uses_structured_fields_first(self) -> None:
        observation = SimpleNamespace(
            completion_ready=False,
            completion_blockers=[" finish tests "],
            latest_completion_blockers=["commit changes"],
            audit="completionReady: yes",
        )

        self.assertEqual(completion_blocker_labels(observation), ["finish tests", "commit changes"])
        self.assertTrue(has_completion_blocker_signal([], observation))

    def test_subagent_failures_use_structured_fields_or_report_sections(self) -> None:
        structured_observation = SimpleNamespace(
            latest_subagent_failures=[" delegate-1 failed: retry limit "],
            audit="latestSubagentFailures:\n- ignored",
            handoff="",
            summary="",
        )
        handoff_observation = SimpleNamespace(
            latest_subagent_failures=[],
            audit="",
            handoff="\n".join(
                [
                    "subagents:",
                    "  latestFailures:",
                    "    - delegate-2 failed: tool denied",
                ]
            ),
            summary="",
        )
        summary_observation = SimpleNamespace(
            latest_subagent_failures=[],
            audit="",
            handoff="",
            summary="\n".join(
                [
                    "latestSubagentFailures:",
                    "- delegate-3 failed: max iterations",
                ]
            ),
        )

        self.assertEqual(subagent_failure_labels(structured_observation), ["delegate-1 failed: retry limit"])
        self.assertEqual(subagent_failure_labels(handoff_observation), ["delegate-2 failed: tool denied"])
        self.assertEqual(subagent_failure_labels(summary_observation), ["delegate-3 failed: max iterations"])

    def test_labels_filter_empty_inputs(self) -> None:
        process = SimpleNamespace(process_id="p1", command="npm run dev", cwd="web")

        self.assertEqual(session_audit_process_labels([process]), ["p1: npm run dev (cwd=web)"])
        self.assertEqual(plan_item_labels([{"status": "pending", "step": "run tests"}, {"status": "done"}]), ["pending: run tests"])
        self.assertEqual(file_reference_labels([{"path": "vibeagent/agent.py", "uses": ["edit", " verify "]}]), ["vibeagent/agent.py (uses: edit, verify)"])


if __name__ == "__main__":
    unittest.main()
