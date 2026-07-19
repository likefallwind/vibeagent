import io
import unittest
from contextlib import redirect_stderr

from vibeagent import cli as cli_module
from vibeagent.tool_categories import valid_tool_categories
from vibeagent.tool_search_options import tool_search_approval_choices


class CliArgsValidationTests(unittest.TestCase):
    def test_model_flag_without_value_remains_local_but_model_value_is_one_shot_override(self) -> None:
        local_args = cli_module.parse_args(["--model"])
        override_args = cli_module.parse_args(["--model", "MiniMax-custom", "inspect"])

        self.assertIs(local_args.model, True)
        self.assertTrue(cli_module.has_local_flag(local_args))
        self.assertEqual(override_args.model, "MiniMax-custom")
        self.assertFalse(cli_module.has_local_flag(override_args))

    def test_cli_resume_short_alias_accepts_run_id(self) -> None:
        args = cli_module.parse_args(["-r", "run-1", "continue"])

        self.assertEqual(args.resume, "run-1")
        self.assertFalse(args.resume_from_continue)

    def test_cli_compat_alias_conflicts_are_validation_errors(self) -> None:
        approval_args = cli_module.parse_args(["--approval", "allow", "--permission-mode", "deny", "inspect"])
        matching_accept_edits_args = cli_module.parse_args(["--approval", "ask", "--permission-mode", "acceptEdits", "inspect"])
        conflicting_accept_edits_args = cli_module.parse_args(["--approval", "allow", "--permission-mode", "acceptEdits", "inspect"])
        matching_bypass_args = cli_module.parse_args(["--approval", "allow", "--permission-mode", "bypassPermissions", "inspect"])
        matching_default_args = cli_module.parse_args(["--approval", "ask", "--permission-mode", "default", "inspect"])
        turn_args = cli_module.parse_args(["--max-iterations", "2", "--max-turns", "3", "inspect"])
        skip_approval_args = cli_module.parse_args(["--dangerously-skip-permissions", "--approval", "allow", "inspect"])
        skip_permission_mode_args = cli_module.parse_args(["--dangerously-skip-permissions", "--permission-mode", "acceptEdits", "inspect"])

        self.assertEqual(
            cli_module.validate_cli_args(approval_args),
            "--approval and --permission-mode cannot specify different policies.",
        )
        self.assertIsNone(cli_module.validate_cli_args(matching_accept_edits_args))
        self.assertEqual(
            cli_module.validate_cli_args(conflicting_accept_edits_args),
            "--approval and --permission-mode cannot specify different policies.",
        )
        self.assertIsNone(cli_module.validate_cli_args(matching_bypass_args))
        self.assertIsNone(cli_module.validate_cli_args(matching_default_args))
        self.assertEqual(
            cli_module.validate_cli_args(turn_args),
            "--max-iterations and --max-turns cannot specify different values.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(skip_approval_args),
            "--dangerously-skip-permissions cannot be combined with --approval or --permission-mode.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(skip_permission_mode_args),
            "--dangerously-skip-permissions cannot be combined with --approval or --permission-mode.",
        )

        bare_model_args = cli_module.parse_args(["--model", "MiniMax-custom"])
        model_with_config_args = cli_module.parse_args(["--model", "--config"])
        self.assertEqual(
            cli_module.validate_cli_args(bare_model_args),
            "--model MODEL requires a one-shot task or --save-config.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(model_with_config_args),
            "--model cannot be combined with other local command flags unless a MODEL value is provided.",
        )

        session_compact_args = cli_module.parse_args(["--session-id", "run-1", "--compact", "run-2", "continue"])
        self.assertEqual(
            cli_module.validate_cli_args(session_compact_args),
            "--resume/--session-id and --compact cannot be used together.",
        )

    def test_cli_dangerously_skip_permissions_requires_one_shot_code_task(self) -> None:
        no_task_args = cli_module.parse_args(["--dangerously-skip-permissions"])
        chat_args = cli_module.parse_args(["--dangerously-skip-permissions", "--chat", "hello"])
        local_args = cli_module.parse_args(["--dangerously-skip-permissions", "--tools"])

        self.assertEqual(
            cli_module.validate_cli_args(no_task_args),
            "--dangerously-skip-permissions requires a one-shot coding task.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(chat_args),
            "--dangerously-skip-permissions requires a one-shot coding task.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(local_args),
            "--dangerously-skip-permissions requires a one-shot coding task.",
        )

    def test_cli_continue_without_task_is_valid_but_not_with_local_flags(self) -> None:
        continue_args = cli_module.parse_args(["-c"])
        local_args = cli_module.parse_args(["-c", "--tools"])

        self.assertIsNone(cli_module.validate_cli_args(continue_args))
        self.assertEqual(
            cli_module.validate_cli_args(local_args),
            "--resume, --compact, and --continue cannot be combined with local command flags.",
        )

    def test_cli_no_auto_compact_requires_plain_one_shot_code_task(self) -> None:
        no_task_args = cli_module.parse_args(["--no-auto-compact"])
        chat_args = cli_module.parse_args(["--no-auto-compact", "--chat", "hello"])
        local_args = cli_module.parse_args(["--no-auto-compact", "--tools"])
        resume_args = cli_module.parse_args(["--no-auto-compact", "--resume", "run-1", "continue"])
        compact_args = cli_module.parse_args(["--no-auto-compact", "--compact", "run-1", "continue"])
        continue_args = cli_module.parse_args(["--no-auto-compact", "-c", "continue"])

        self.assertEqual(
            cli_module.validate_cli_args(no_task_args),
            "--no-auto-compact requires a one-shot coding task.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(chat_args),
            "--no-auto-compact requires a one-shot coding task.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(local_args),
            "--no-auto-compact requires a one-shot coding task.",
        )
        for args in (resume_args, compact_args, continue_args):
            with self.subTest(args=args):
                self.assertEqual(
                    cli_module.validate_cli_args(args),
                    "--no-auto-compact cannot be combined with --resume, --compact, or --continue.",
                )

    def test_cli_rejects_empty_or_local_system_prompt_arguments(self) -> None:
        empty_args = cli_module.parse_args(["--system-prompt", " ", "inspect"])
        local_args = cli_module.parse_args(["--append-system-prompt", "Extra", "--tools"])

        self.assertEqual(cli_module.validate_cli_args(empty_args), "--system-prompt cannot be empty.")
        self.assertEqual(
            cli_module.validate_cli_args(local_args),
            "--system-prompt and --append-system-prompt require a one-shot task.",
        )

    def test_cli_rejects_mcp_config_without_one_shot_task(self) -> None:
        args = cli_module.parse_args(["--mcp-config", "extra.mcp.json", "--tools"])
        strict_args = cli_module.parse_args(["--strict-mcp-config", "--tools"])

        self.assertEqual(cli_module.validate_cli_args(args), "--mcp-config requires a one-shot task.")
        self.assertEqual(cli_module.validate_cli_args(strict_args), "--strict-mcp-config requires a one-shot task.")

    def test_parse_args_accepts_explicit_aliases_but_rejects_implicit_abbreviations(self) -> None:
        command_args = cli_module.parse_args(["--command", "python3 --version"])
        run_args = cli_module.parse_args(["--run", "python3 --version"])
        start_args = cli_module.parse_args(["--start", "npm run dev"])
        stderr = io.StringIO()

        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            cli_module.parse_args(["--mod"])

        self.assertEqual(command_args.command_check, "python3 --version")
        self.assertEqual(run_args.run_command, "python3 --version")
        self.assertEqual(start_args.start_command, "npm run dev")
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("unrecognized arguments: --mod", stderr.getvalue())

    def test_parse_args_tool_search_category_uses_shared_categories(self) -> None:
        for category in valid_tool_categories():
            with self.subTest(category=category):
                args = cli_module.parse_args(["--tool-search", "read", "--tool-search-category", category])
                self.assertEqual(args.tool_search_category, category)

        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            cli_module.parse_args(["--tool-search", "read", "--tool-search-category", "missing"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("invalid choice: 'missing'", stderr.getvalue())

    def test_parse_args_tool_search_approval_uses_shared_choices(self) -> None:
        for approval in tool_search_approval_choices():
            with self.subTest(approval=approval):
                args = cli_module.parse_args(["--tool-search", "read", "--tool-search-approval", approval])
                self.assertEqual(args.tool_search_approval, approval)

        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            cli_module.parse_args(["--tool-search", "read", "--tool-search-approval", "maybe"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("invalid choice: 'maybe'", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
