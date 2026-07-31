import unittest
from types import SimpleNamespace

from vibeagent import prompt_next_action_session, prompt_next_action_session_reports


class PromptNextActionSessionReportsTests(unittest.TestCase):
    def test_report_recovery_instructions_live_in_report_module(self) -> None:
        self.assertIs(
            prompt_next_action_session.session_summary_next_action_instruction,
            prompt_next_action_session_reports.session_summary_next_action_instruction,
        )
        self.assertIs(
            prompt_next_action_session.session_transcript_next_action_instruction,
            prompt_next_action_session_reports.session_transcript_next_action_instruction,
        )
        self.assertIs(
            prompt_next_action_session.session_search_next_action_instruction,
            prompt_next_action_session_reports.session_search_next_action_instruction,
        )
        self.assertIs(
            prompt_next_action_session.session_commands_next_action_instruction,
            prompt_next_action_session_reports.session_commands_next_action_instruction,
        )
        self.assertIs(
            prompt_next_action_session.session_plan_next_action_instruction,
            prompt_next_action_session_reports.session_plan_next_action_instruction,
        )
        self.assertIs(
            prompt_next_action_session.session_failures_next_action_instruction,
            prompt_next_action_session_reports.session_failures_next_action_instruction,
        )
        self.assertIs(
            prompt_next_action_session.session_files_next_action_instruction,
            prompt_next_action_session_reports.session_files_next_action_instruction,
        )

    def test_session_report_dispatch_keeps_recovery_guidance(self) -> None:
        latest = SimpleNamespace(kind="session_plan", ok=True, plan="- [ ] run tests")

        instruction = prompt_next_action_session.session_next_action_instruction("Next.", latest)

        self.assertIn("Session plan shows unfinished work", instruction)
        self.assertIn("session_verification", instruction)


if __name__ == "__main__":
    unittest.main()
