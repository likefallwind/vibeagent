import io
import unittest
from contextlib import redirect_stderr

from vibeagent import cli as cli_module
from vibeagent.tool_categories import valid_tool_categories
from vibeagent.tool_search_options import tool_search_approval_choices


class CliArgsValidationTests(unittest.TestCase):
    def test_fallback_model_requires_print_one_shot_code(self) -> None:
        valid = cli_module.parse_args(["-p", "--fallback-model", "backup", "inspect"])
        no_print = cli_module.parse_args(["--fallback-model", "backup", "inspect"])
        chat = cli_module.parse_args(["-p", "--chat", "--fallback-model", "backup", "hello"])
        empty = cli_module.parse_args(["-p", "--fallback-model", " ", "inspect"])

        self.assertIsNone(cli_module.validate_cli_args(valid))
        self.assertIn("one-shot coding task", cli_module.validate_cli_args(no_print) or "")
        self.assertIn("one-shot coding task", cli_module.validate_cli_args(chat) or "")
        self.assertIn("cannot be empty", cli_module.validate_cli_args(empty) or "")

    def test_max_budget_requires_print_one_shot_code(self) -> None:
        valid = cli_module.parse_args(["-p", "--max-budget-usd", "1.25", "inspect"])
        no_print = cli_module.parse_args(["--max-budget-usd", "1", "inspect"])
        chat = cli_module.parse_args(["-p", "--chat", "--max-budget-usd", "1", "hello"])

        self.assertIsNone(cli_module.validate_cli_args(valid))
        self.assertEqual(str(valid.max_budget_usd), "1.25")
        self.assertIn("one-shot coding task", cli_module.validate_cli_args(no_print) or "")
        self.assertIn("one-shot coding task", cli_module.validate_cli_args(chat) or "")

    def test_max_budget_rejects_nonpositive_and_nonfinite_values(self) -> None:
        for value in ("0", "-1", "NaN", "Infinity", "bad"):
            with self.subTest(value=value), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                cli_module.parse_args(["-p", "--max-budget-usd", value, "inspect"])

    def test_json_schema_requires_print_mode_one_shot_code(self) -> None:
        schema = '{"type":"object"}'
        valid = cli_module.parse_args(["-p", "--json-schema", schema, "inspect"])
        no_print = cli_module.parse_args(["--json-schema", schema, "inspect"])
        interactive = cli_module.parse_args(["--json-schema", schema])
        chat = cli_module.parse_args(["-p", "--json-schema", schema, "--chat", "inspect"])
        local = cli_module.parse_args(["-p", "--json-schema", schema, "--status"])

        self.assertIsNone(cli_module.validate_cli_args(valid))
        for args in (no_print, interactive, chat, local):
            self.assertEqual(
                cli_module.validate_cli_args(args),
                "--json-schema requires a one-shot coding task with --print.",
            )

    def test_cli_name_is_forwarded_and_rejects_non_session_modes(self) -> None:
        one_shot = cli_module.parse_args(["-n", "auth-refactor", "inspect"])
        interactive = cli_module.parse_args(["--name", "auth-refactor"])
        chat = cli_module.parse_args(["--chat", "--name", "chat-name", "hello"])
        local = cli_module.parse_args(["--sessions", "--name", "local-name"])
        reserved = cli_module.parse_args(["--name", "latest"])

        self.assertIsNone(cli_module.validate_cli_args(one_shot))
        self.assertIsNone(cli_module.validate_cli_args(interactive))
        self.assertEqual(cli_module.build_one_shot_kwargs_from_args(one_shot)["session_name"], "auth-refactor")
        self.assertEqual(
            cli_module.validate_cli_args(chat),
            "--name requires a non-empty interactive or one-shot coding session name.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(local),
            "--name requires a non-empty interactive or one-shot coding session name.",
        )
        self.assertEqual(cli_module.validate_cli_args(reserved), "Session name is reserved: latest")

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

    def test_cli_fork_session_requires_resume_and_coding_mode(self) -> None:
        valid_continue = cli_module.parse_args(["--continue", "--fork-session"])
        valid_resume = cli_module.parse_args(["--resume", "run-1", "--fork-session", "continue"])
        missing_source = cli_module.parse_args(["--fork-session", "continue"])
        compact = cli_module.parse_args(["--compact", "run-1", "--fork-session", "continue"])
        chat = cli_module.parse_args(["--chat", "--resume", "run-1", "--fork-session", "hello"])
        local = cli_module.parse_args(["--sessions", "--resume", "run-1", "--fork-session"])
        cleared = cli_module.parse_args(["--resume", "off", "--fork-session", "continue"])

        self.assertIsNone(cli_module.validate_cli_args(valid_continue))
        self.assertIsNone(cli_module.validate_cli_args(valid_resume))
        self.assertTrue(cli_module.build_one_shot_kwargs_from_args(valid_resume)["fork_session"])
        self.assertEqual(
            cli_module.validate_cli_args(missing_source),
            "--fork-session requires --resume, --session-id, or --continue.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(compact),
            "--fork-session cannot be combined with --compact.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(chat),
            "--fork-session requires an interactive or one-shot coding session.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(local),
            "--fork-session requires an interactive or one-shot coding session.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(cleared),
            "--fork-session requires a resumable source session, not --resume off.",
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
        empty_file_args = cli_module.parse_args(["--system-prompt-file", " ", "inspect"])
        local_args = cli_module.parse_args(["--append-system-prompt", "Extra", "--tools"])
        conflict_args = cli_module.parse_args(
            ["--system-prompt", "Inline", "--system-prompt-file", "prompt.txt", "inspect"]
        )

        self.assertEqual(cli_module.validate_cli_args(empty_args), "--system-prompt cannot be empty.")
        self.assertEqual(
            cli_module.validate_cli_args(empty_file_args),
            "--system-prompt-file path cannot be empty.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(local_args),
            "System prompt options require an interactive or one-shot session.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(conflict_args),
            "--system-prompt cannot be combined with --system-prompt-file.",
        )

    def test_cli_accepts_system_prompt_options_for_interactive_startup(self) -> None:
        text_args = cli_module.parse_args(["--system-prompt", "Be concise."])
        file_args = cli_module.parse_args(
            ["--system-prompt-file", "system.txt", "--append-system-prompt-file", "append.txt"]
        )

        self.assertIsNone(cli_module.validate_cli_args(text_args))
        self.assertIsNone(cli_module.validate_cli_args(file_args))

    def test_cli_validates_additional_directory_session_scope(self) -> None:
        interactive_args = cli_module.parse_args(["--add-dir", "../shared"])
        one_shot_args = cli_module.parse_args(["--add-dir", "../shared", "inspect"])
        empty_args = cli_module.parse_args(["--add-dir", " ", "inspect"])
        chat_args = cli_module.parse_args(["--chat", "--add-dir", "../shared", "explain"])
        local_args = cli_module.parse_args(["--add-dir", "../shared", "--tools"])
        worktree_args = cli_module.parse_args(["--add-dir", "../shared", "--worktree", "inspect"])

        self.assertIsNone(cli_module.validate_cli_args(interactive_args))
        self.assertIsNone(cli_module.validate_cli_args(one_shot_args))
        self.assertEqual(cli_module.validate_cli_args(empty_args), "--add-dir path cannot be empty.")
        self.assertEqual(
            cli_module.validate_cli_args(chat_args),
            "--add-dir requires an interactive or one-shot coding session.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(local_args),
            "--add-dir requires an interactive or one-shot coding session.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(worktree_args),
            "--add-dir cannot be combined with --worktree.",
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
