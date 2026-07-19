import io
import unittest
from unittest.mock import patch

from vibeagent.cli import build_approval_handler, handle_approval_command, prompt_approval
from vibeagent.cli_system_prompt_state import update_system_prompt_state
from vibeagent.types import ApprovalRequest


class CliApprovalHelpersTests(unittest.TestCase):
    def test_update_system_prompt_state_shows_sets_and_clears_value(self) -> None:
        current, shown = update_system_prompt_state(None, None, label="System prompt")
        updated, set_text = update_system_prompt_state(current, "Use short answers.", label="System prompt")
        cleared, clear_text = update_system_prompt_state(updated, "off", label="System prompt")

        self.assertIsNone(current)
        self.assertEqual(shown, "System prompt: default")
        self.assertEqual(updated, "Use short answers.")
        self.assertEqual(set_text, "System prompt set (18 chars).")
        self.assertIsNone(cleared)
        self.assertEqual(clear_text, "System prompt cleared.")

    def test_prompt_approval_accepts_y_and_yes(self) -> None:
        request = ApprovalRequest(
            action_type="write_file",
            target="note.txt",
            risk="This will create or replace a file in the active project.",
        )

        for answer in ("y", "yes"):
            with self.subTest(answer=answer):
                with patch("builtins.input", return_value=answer), patch("sys.stdout", new_callable=io.StringIO):
                    decision = prompt_approval(request)

                self.assertTrue(decision.approved)

    def test_prompt_approval_denies_other_input(self) -> None:
        request = ApprovalRequest(
            action_type="run_command",
            target="npm test",
            risk="This will run a shell command from the active project directory.",
        )

        with patch("builtins.input", return_value="n"), patch("sys.stdout", new_callable=io.StringIO):
            decision = prompt_approval(request)

        self.assertFalse(decision.approved)

    def test_prompt_approval_supports_session_scope(self) -> None:
        request = ApprovalRequest(
            action_type="run_command",
            target="npm test",
            risk="This will run a shell command from the active project directory.",
        )

        for answer in ("a", "always"):
            with self.subTest(answer=answer):
                with patch("builtins.input", return_value=answer), patch("sys.stdout", new_callable=io.StringIO):
                    decision = prompt_approval(request)

                self.assertTrue(decision.approved)
                self.assertEqual(decision.scope, "session")

    def test_prompt_approval_prints_target_and_risk_without_file_content(self) -> None:
        request = ApprovalRequest(
            action_type="write_file",
            target="report.md",
            risk="This will create or replace a file in the active project.",
        )
        large_file_content = "secret\n" * 500

        with patch("builtins.input", return_value="n"), patch("sys.stdout", new_callable=io.StringIO) as stdout:
            prompt_approval(request)

        output = stdout.getvalue()
        self.assertIn("write_file", output)
        self.assertIn("report.md", output)
        self.assertIn("create or replace", output)
        self.assertNotIn(large_file_content, output)

    def test_prompt_approval_prints_preview_summary(self) -> None:
        request = ApprovalRequest(
            action_type="write_file",
            target="report.md",
            risk="This will create or replace a file in the active project.",
            preview="Preview passed; diffChars=42",
        )

        with patch("builtins.input", return_value="n"), patch("sys.stdout", new_callable=io.StringIO) as stdout:
            prompt_approval(request)

        output = stdout.getvalue()
        self.assertIn("Preview: Preview passed; diffChars=42", output)

    def test_handle_approval_command_shows_and_updates_policy(self) -> None:
        self.assertEqual(handle_approval_command(None, "ask"), ("ask", "Approval policy: ask"))
        self.assertEqual(handle_approval_command("allow", "ask"), ("allow", "Approval policy: allow"))
        self.assertEqual(handle_approval_command("deny", "allow"), ("deny", "Approval policy: deny"))
        self.assertEqual(handle_approval_command("plan", "deny"), ("plan", "Approval policy: plan"))
        self.assertEqual(handle_approval_command("bad", "deny"), ("deny", "Usage: /approval [ask|allow|deny|plan]"))

    def test_build_approval_handler_uses_policy_without_prompting(self) -> None:
        request = ApprovalRequest(
            action_type="run_command",
            target="python -m unittest",
            risk="This will run a shell command.",
        )

        self.assertTrue(build_approval_handler("allow")(request).approved)
        denied = build_approval_handler("deny")(request)
        self.assertFalse(denied.approved)
        self.assertIn("Denied by policy", denied.message)
        plan_denied = build_approval_handler("plan")(request)
        self.assertFalse(plan_denied.approved)
        self.assertIn("Plan mode is read-only", plan_denied.message)


if __name__ == "__main__":
    unittest.main()
