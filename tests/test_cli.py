import argparse
import io
import json
import os
import subprocess
import tempfile
import time
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, call, patch

from vibeagent import cli as cli_module
from vibeagent import cli_command_namespace, commands as commands_module
from vibeagent.agent import AgentResult
from vibeagent.cli import build_approval_handler, format_error, handle_approval_command, main, print_agent_result, prompt_approval
from vibeagent.cli_local_dispatch import LOCAL_FLAG_HANDLER_NAMES, dispatch_local_flag
from vibeagent.cli_local_flag_detection import LOCAL_FLAG_ARG_NAMES
from vibeagent.cli_system_prompt_state import update_system_prompt_state
from vibeagent.command_namespace_exports import command_export_names
from vibeagent.tool_categories import valid_tool_categories
from vibeagent.tool_search_options import tool_search_approval_choices
from vibeagent.types import ApprovalRequest, PlanItem, TaskStep


class Http401Error(Exception):
    status = 401


class CliTests(unittest.TestCase):
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

    def test_cli_reexports_command_namespace_helpers(self) -> None:
        missing_or_changed = [
            name
            for name in cli_command_namespace.__all__
            if getattr(cli_module, name, None) is not getattr(commands_module, name, None)
        ]

        self.assertEqual([], missing_or_changed)
        self.assertIn("get_read_text", cli_command_namespace.__all__)
        self.assertIn("format_review_report_text", cli_command_namespace.__all__)
        self.assertIn("parse_local_command", cli_command_namespace.__all__)

    def test_cli_command_namespace_uses_public_command_exports_only(self) -> None:
        self.assertEqual(len(commands_module.__all__), 554)
        self.assertEqual(command_export_names(commands_module), commands_module.__all__)
        self.assertEqual(command_export_names(commands_module), cli_command_namespace.__all__)
        self.assertNotIn("format_tool_property", cli_command_namespace.__all__)
        self.assertNotIn("get_blocked_command_reason", cli_command_namespace.__all__)

    def test_dispatch_local_flag_preserves_order_and_handler_signatures(self) -> None:
        args = argparse.Namespace()
        project_root = Path("/tmp/project")
        config_root = Path("/tmp/config")
        provider_env = {"VIBEAGENT_PROVIDER": "minimax"}
        calls: list[tuple[str, object, ...]] = []

        def generic_handler(name: str, result: tuple[str, dict[str, object]] | None = None):
            def run(args, project_root, commands):
                calls.append((name, project_root, commands))
                return result

            return run

        def project_handler(name: str, result: tuple[str, dict[str, object]] | None = None):
            def run(args, project_root, config_root, provider_env, commands):
                calls.append((name, project_root, config_root, provider_env, commands))
                return result

            return run

        def review_handler(result: tuple[str, dict[str, object]] | None = None):
            def run(args, project_root, provider_env, commands):
                calls.append(("run_review_local_flag", project_root, provider_env, commands))
                return result

            return run

        namespace = {
            name: (
                review_handler(("review text", {"review": {"ok": True}}))
                if name == "run_review_local_flag"
                else project_handler(name)
                if name == "run_project_local_flag"
                else generic_handler(name)
            )
            for name in LOCAL_FLAG_HANDLER_NAMES
        }

        result = dispatch_local_flag(args, project_root, config_root, provider_env, namespace)

        self.assertEqual(result, ("review text", {"review": {"ok": True}}))
        self.assertEqual([call[0] for call in calls], list(LOCAL_FLAG_HANDLER_NAMES[:12]))
        self.assertEqual(calls[0], ("run_project_local_flag", project_root, config_root, provider_env, namespace))
        self.assertEqual(calls[1], ("run_command_local_flag", project_root, namespace))
        self.assertEqual(calls[-1], ("run_review_local_flag", project_root, provider_env, namespace))

    def test_session_kwargs_helpers_keep_cli_option_mapping(self) -> None:
        args = argparse.Namespace(
            session_transcript_event_max=12,
            session_max_text=500,
            session_search_match_max=7,
            session_search_case_sensitive=True,
            session_max_commands=3,
            session_max_output_chars=1000,
            session_output_command_max=4,
            session_output_max_chars=1200,
            session_output_context_lines=2,
            session_output_context_max=5,
            session_output_context_max_bytes=800,
            session_output_diagnostic_max=6,
            session_max_files=9,
            session_max_failures=10,
            session_max_checks=11,
            run_timeout_ms=1500,
            run_max_chars=2000,
            run_session_no_failed=True,
            run_session_no_pending=False,
            run_continue_on_failure=True,
            run_output_contexts=True,
            run_output_diagnostics=True,
            run_output_context_lines=2,
            run_output_diagnostic_max=6,
            run_output_context_max=5,
            run_output_context_max_bytes=800,
        )

        self.assertEqual(cli_module.session_transcript_kwargs(args), {"max_events": 12, "max_text": 500})
        self.assertEqual(
            cli_module.session_search_kwargs(args),
            {"max_matches": 7, "max_text": 500, "case_sensitive": True},
        )
        self.assertEqual(cli_module.session_commands_kwargs(args), {"max_commands": 3, "max_output_chars": 1000})
        self.assertEqual(
            cli_module.session_output_contexts_kwargs(args),
            {
                "max_commands": 4,
                "max_output_chars": 1200,
                "context_lines": 2,
                "max_contexts": 5,
                "max_bytes_per_context": 800,
            },
        )
        self.assertEqual(
            cli_module.session_output_diagnostics_kwargs(args),
            {
                "max_commands": 4,
                "max_output_chars": 1200,
                "context_lines": 2,
                "max_contexts": 5,
                "max_bytes_per_context": 800,
                "max_diagnostics": 6,
            },
        )
        self.assertEqual(cli_module.session_files_kwargs(args), {"max_files": 9})
        self.assertEqual(cli_module.session_failures_kwargs(args), {"max_failures": 10, "max_text": 500})
        self.assertEqual(cli_module.session_verification_kwargs(args), {"max_checks": 11})
        self.assertEqual(
            cli_module.run_session_verification_kwargs(args),
            {
                "max_checks": 11,
                "timeout_ms": 1500,
                "max_output_chars": 2000,
                "extract_output_contexts": True,
                "extract_output_diagnostics": True,
                "context_lines": 2,
                "max_diagnostics": 6,
                "max_contexts": 5,
                "max_bytes_per_context": 800,
                "include_failed": False,
                "stop_on_failure": False,
            },
        )
        self.assertEqual(
            cli_module.session_audit_kwargs(args),
            {
                "max_failures": 10,
                "max_files": 9,
                "max_commands": 3,
                "max_checks": 11,
                "max_text": 500,
            },
        )
        self.assertEqual(
            cli_module.session_handoff_kwargs(args),
            {
                "max_failures": 10,
                "max_files": 9,
                "max_commands": 3,
                "max_checks": 11,
                "max_output_chars": 1000,
                "max_text": 500,
            },
        )

    def test_session_kwargs_helpers_omit_unset_optional_values(self) -> None:
        args = argparse.Namespace(
            session_transcript_event_max=None,
            session_max_text=None,
            session_search_match_max=None,
            session_search_case_sensitive=False,
            session_max_commands=None,
            session_max_output_chars=None,
            session_output_command_max=20,
            session_output_max_chars=4000,
            session_output_context_lines=2,
            session_output_context_max=10,
            session_output_context_max_bytes=12000,
            session_output_diagnostic_max=10,
            session_max_files=None,
            session_max_failures=None,
            session_max_checks=None,
            run_timeout_ms=30000,
            run_max_chars=12000,
            run_session_no_failed=False,
            run_session_no_pending=False,
            run_continue_on_failure=False,
            run_output_contexts=False,
            run_output_diagnostics=False,
            run_output_context_lines=5,
            run_output_diagnostic_max=50,
            run_output_context_max=20,
            run_output_context_max_bytes=20000,
        )

        self.assertEqual(cli_module.session_transcript_kwargs(args), {})
        self.assertEqual(cli_module.session_search_kwargs(args), {})
        self.assertEqual(cli_module.session_commands_kwargs(args), {})
        self.assertEqual(cli_module.session_files_kwargs(args), {})
        self.assertEqual(cli_module.session_failures_kwargs(args), {})
        self.assertEqual(cli_module.session_verification_kwargs(args), {})
        self.assertEqual(
            cli_module.run_session_verification_kwargs(args),
            {
                "timeout_ms": 30000,
                "max_output_chars": 12000,
                "extract_output_contexts": False,
                "extract_output_diagnostics": False,
                "context_lines": 5,
                "max_diagnostics": 50,
                "max_contexts": 20,
                "max_bytes_per_context": 20000,
            },
        )
        self.assertEqual(cli_module.session_audit_kwargs(args), {})
        self.assertEqual(cli_module.session_handoff_kwargs(args), {})
        self.assertEqual(
            cli_module.session_output_contexts_kwargs(args),
            {
                "max_commands": 20,
                "max_output_chars": 4000,
                "context_lines": 2,
                "max_contexts": 10,
                "max_bytes_per_context": 12000,
            },
        )

    def test_local_result_exit_code_covers_local_result_flags(self) -> None:
        self.assertEqual(LOCAL_FLAG_ARG_NAMES - cli_module.LOCAL_RESULT_ARG_NAMES, set())
        self.assertEqual(cli_module.LOCAL_RESULT_ARG_NAMES - LOCAL_FLAG_ARG_NAMES, set())

    def test_model_flag_without_value_remains_local_but_model_value_is_one_shot_override(self) -> None:
        local_args = cli_module.parse_args(["--model"])
        override_args = cli_module.parse_args(["--model", "MiniMax-custom", "inspect"])

        self.assertIs(local_args.model, True)
        self.assertTrue(cli_module.has_local_flag(local_args))
        self.assertEqual(override_args.model, "MiniMax-custom")
        self.assertFalse(cli_module.has_local_flag(override_args))

    def test_normalize_task_bound_diff_args_moves_task_into_diff_argument(self) -> None:
        args = argparse.Namespace(
            diff_contexts="",
            diff_hunks=None,
            diff=None,
            diff_staged=False,
            task=["src/app.py", "tests/test_app.py"],
        )

        cli_module.normalize_task_bound_diff_args(args)

        self.assertEqual(args.diff_contexts, "src/app.py tests/test_app.py")
        self.assertEqual(args.task, [])

    def test_emit_local_result_sets_failed_status_for_local_errors(self) -> None:
        args = argparse.Namespace(json=True, tool="missing")

        with patch("sys.stdout", new_callable=io.StringIO) as stdout:
            exit_code = cli_module.emit_local_result(args, "Tool not found: missing", {"tool": {"ok": False}})

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["tool"], {"ok": False})

    def test_build_one_shot_kwargs_from_args_keeps_main_mapping(self) -> None:
        args = cli_module.parse_args(
            [
                "--chat",
                "--approval",
                "allow",
                "--resume",
                "last",
                "--max-iterations",
                "7",
                "--command-timeout-ms",
                "1234",
                "explain",
                "repo",
            ]
        )

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertEqual(kwargs["task"], "explain repo")
        self.assertEqual(kwargs["request_mode"], "chat")
        self.assertEqual(kwargs["approval_policy"], "allow")
        self.assertEqual(kwargs["resume_arg"], "last")
        self.assertEqual(kwargs["max_iterations"], 7)
        self.assertEqual(kwargs["command_timeout_ms"], 1234)
        self.assertTrue(kwargs["auto_compact"])
        self.assertEqual(kwargs["permission_overrides"].rules, ())
        self.assertIs(kwargs["provider_args"], args)

        plan_args = cli_module.parse_args(["--approval", "plan", "inspect", "repo"])
        self.assertEqual(plan_args.approval, "plan")

    def test_build_one_shot_kwargs_from_args_includes_system_prompt_overrides(self) -> None:
        args = cli_module.parse_args(
            [
                "--system-prompt",
                "You are a release engineer.",
                "--append-system-prompt",
                "Prefer focused tests.",
                "inspect",
            ]
        )

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertEqual(kwargs["system_prompt"], "You are a release engineer.")
        self.assertEqual(kwargs["append_system_prompt"], "Prefer focused tests.")

    def test_build_one_shot_kwargs_from_args_includes_mcp_config_paths(self) -> None:
        args = cli_module.parse_args(["--mcp-config", "extra.mcp.json", "inspect"])

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertEqual(kwargs["mcp_config_paths"], ["extra.mcp.json"])
        self.assertFalse(kwargs["strict_mcp_config"])

    def test_build_one_shot_kwargs_from_args_includes_strict_mcp_config(self) -> None:
        args = cli_module.parse_args(["--mcp-config", "extra.mcp.json", "--strict-mcp-config", "inspect"])

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertEqual(kwargs["mcp_config_paths"], ["extra.mcp.json"])
        self.assertTrue(kwargs["strict_mcp_config"])

    def test_build_one_shot_kwargs_from_args_includes_no_auto_compact(self) -> None:
        args = cli_module.parse_args(["--no-auto-compact", "inspect"])

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertFalse(kwargs["auto_compact"])

    def test_cli_compat_aliases_map_to_existing_one_shot_fields(self) -> None:
        args = cli_module.parse_args(
            [
                "-p",
                "-c",
                "--permission-mode",
                "plan",
                "--max-turns",
                "3",
                "inspect",
                "repo",
            ]
        )

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertTrue(args.print_mode)
        self.assertTrue(args.continue_latest)
        self.assertEqual(args.resume, "")
        self.assertTrue(args.resume_from_continue)
        self.assertEqual(kwargs["approval_policy"], "plan")
        self.assertEqual(kwargs["resume_arg"], "")
        self.assertEqual(kwargs["max_iterations"], 3)
        self.assertTrue(kwargs["print_mode"])

    def test_cli_continue_long_alias_maps_to_latest_resume_context(self) -> None:
        args = cli_module.parse_args(["--continue", "inspect", "repo"])

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertTrue(args.continue_latest)
        self.assertEqual(args.resume, "")
        self.assertTrue(args.resume_from_continue)
        self.assertEqual(kwargs["resume_arg"], "")
        self.assertIsNone(cli_module.validate_cli_args(args))

    def test_cli_permission_mode_accepts_claude_values(self) -> None:
        cases = [
            ("default", "ask"),
            ("acceptEdits", "allow"),
            ("bypassPermissions", "allow"),
            ("plan", "plan"),
        ]

        for value, expected in cases:
            with self.subTest(value=value):
                args = cli_module.parse_args(["--permission-mode", value, "inspect"])
                kwargs = cli_module.build_one_shot_kwargs_from_args(args)

                self.assertEqual(args.approval, expected)
                self.assertEqual(kwargs["approval_policy"], expected)
                self.assertIsNone(cli_module.validate_cli_args(args))

    def test_cli_dangerously_skip_permissions_maps_to_allow_for_code_tasks(self) -> None:
        args = cli_module.parse_args(["--dangerously-skip-permissions", "inspect", "repo"])

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertTrue(args.dangerously_skip_permissions)
        self.assertEqual(args.approval, "allow")
        self.assertEqual(kwargs["approval_policy"], "allow")
        self.assertIsNone(cli_module.validate_cli_args(args))

    def test_cli_resume_short_alias_accepts_run_id(self) -> None:
        args = cli_module.parse_args(["-r", "run-1", "continue"])

        self.assertEqual(args.resume, "run-1")
        self.assertFalse(args.resume_from_continue)

    def test_cli_session_id_alias_maps_to_resume_arg(self) -> None:
        args = cli_module.parse_args(["--session-id", "run-1", "continue"])

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)

        self.assertEqual(args.session_id, "run-1")
        self.assertEqual(kwargs["resume_arg"], "run-1")

    def test_cli_compat_alias_conflicts_are_validation_errors(self) -> None:
        approval_args = cli_module.parse_args(["--approval", "allow", "--permission-mode", "deny", "inspect"])
        matching_accept_edits_args = cli_module.parse_args(["--approval", "allow", "--permission-mode", "acceptEdits", "inspect"])
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

    def test_build_one_shot_kwargs_from_args_includes_permission_overrides(self) -> None:
        args = cli_module.parse_args(
            [
                "--allowedTools",
                "Read",
                "--allowed-tools",
                "Bash(git diff:*)",
                "--disallowedTools",
                "Edit(src/**)",
                "inspect",
            ]
        )

        kwargs = cli_module.build_one_shot_kwargs_from_args(args)
        permissions = kwargs["permission_overrides"]

        self.assertEqual([rule.effect for rule in permissions.rules], ["allow", "allow", "deny"])
        self.assertEqual([rule.raw for rule in permissions.rules], ["Read", "Bash(git diff:*)", "Edit(src/**)"])
        self.assertTrue(permissions.trusted_allow_sources)

    def test_main_rejects_invalid_permission_override_rule(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--allowed-tools", "Read(", "inspect"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["kind"], "error")
        self.assertIn("permission rule is invalid", payload["error"])
        create_chat_client.assert_not_called()

    def test_main_rejects_permission_overrides_without_code_task(self) -> None:
        cases = [
            ["--json", "--allowed-tools", "Read"],
            ["--json", "--allowed-tools", "Read", "--chat", "hello"],
            ["--json", "--disallowed-tools", "Edit", "--permissions"],
        ]
        for argv in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 2)
                self.assertIn("can only be used with one-shot coding tasks", payload["error"])
                create_chat_client.assert_not_called()

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

    def test_format_error_uses_provider_neutral_401_guidance(self) -> None:
        text = format_error(Http401Error("unauthorized"))

        self.assertIn("unauthorized", text)
        self.assertIn("configured model provider rejected the API key", text)
        self.assertIn("Check /model", text)
        self.assertNotIn("MiniMax rejected", text)
        self.assertNotIn("DEEPSEEK_API_KEY", text)

    def test_format_error_returns_plain_error_for_other_errors(self) -> None:
        self.assertEqual(format_error(ValueError("bad")), "bad")

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

    def test_main_prints_only_final_agent_message_for_code_tasks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="这是最终回复。",
                run_dir=Path(base),
                run_id="test-run",
                iterations=3,
                observations=[],
                steps=[
                    TaskStep(
                        id=1,
                        label="List files .",
                        action_type="list_files",
                        target=".",
                        status="completed",
                        message="Found 0 file(s).",
                    )
                ],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["现在用的什么 模型", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("这是最终回复。", output)
        self.assertNotIn("[thinking]", output)
        self.assertNotIn("Success", output)
        self.assertNotIn("Project directory:", output)
        self.assertNotIn("Iterations:", output)
        self.assertNotIn("Steps:", output)
        self.assertNotIn("List files .", output)
        self.assertNotIn("logger", run_agent.call_args.kwargs)

    def test_print_agent_result_shows_completion_warnings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="Done.",
                run_dir=Path(base),
                run_id="test-run",
                iterations=1,
                observations=[],
                steps=[],
                completion_ready=False,
                completion_blockers=["Final review did not report ready."],
                completion_warnings=["Project changes completed without a final_review observation."],
                verification_checks=["python -m unittest discover -s tests"],
                pending_verification_checks=["npm test"],
                failed_verification_checks=["npm test (exit=1)"],
                latest_completion_final_review_issues=["Changed Python files have syntax errors."],
                latest_completion_final_review_changed_files=["M app.py"],
                latest_completion_tool_errors=["read_file: Tool execution failed: boom"],
                latest_completion_checkpoint_failures=["checkpoint_create: git diff failed."],
                latest_completion_active_background_processes=["bg-1: pid=123, cwd=web, command=npm run dev"],
                latest_completion_denied_approvals=["write_file note.txt: denied"],
                final_review_changed_files=["M app.py", "A tests/test_app.py"],
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                print_agent_result(result)

        self.assertIn("Done.", stdout.getvalue())
        self.assertIn("Completion blockers:", stdout.getvalue())
        self.assertIn("Final review did not report ready.", stdout.getvalue())
        self.assertIn("Warnings:", stdout.getvalue())
        self.assertIn("Project changes completed without a final_review observation.", stdout.getvalue())
        self.assertIn("Changed files:", stdout.getvalue())
        self.assertIn("M app.py", stdout.getvalue())
        self.assertIn("A tests/test_app.py", stdout.getvalue())
        self.assertIn("Verified:", stdout.getvalue())
        self.assertIn("python -m unittest discover -s tests", stdout.getvalue())
        self.assertIn("Pending checks:", stdout.getvalue())
        self.assertIn("npm test", stdout.getvalue())
        self.assertIn("Failed checks:", stdout.getvalue())
        self.assertIn("npm test (exit=1)", stdout.getvalue())
        self.assertIn("Latest final review issues:", stdout.getvalue())
        self.assertIn("Changed Python files have syntax errors.", stdout.getvalue())
        self.assertIn("Latest final review changed files:", stdout.getvalue())
        self.assertIn("M app.py", stdout.getvalue())
        self.assertIn("Latest tool errors:", stdout.getvalue())
        self.assertIn("read_file: Tool execution failed: boom", stdout.getvalue())
        self.assertIn("Latest checkpoint failures:", stdout.getvalue())
        self.assertIn("checkpoint_create: git diff failed.", stdout.getvalue())
        self.assertIn("Latest active processes:", stdout.getvalue())
        self.assertIn("bg-1: pid=123, cwd=web, command=npm run dev", stdout.getvalue())
        self.assertIn("Latest denied approvals:", stdout.getvalue())
        self.assertIn("write_file note.txt: denied", stdout.getvalue())

    def test_main_runs_one_shot_code_task_from_args(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--approval",
                        "allow",
                        "--cwd",
                        base,
                        "--max-iterations",
                        "7",
                        "--command-timeout-ms",
                        "1234",
                        "--max-output-tokens",
                        "8192",
                        "--model-retries",
                        "2",
                        "--model-retry-delay-ms",
                        "25",
                        "--model-timeout-ms",
                        "45000",
                        "fix",
                        "the",
                        "test",
                    ]
                )

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("done", output)
        self.assertNotIn("VibeAgent v0.1", output)
        self.assertEqual(run_agent.call_args.args[0], "fix the test")
        self.assertEqual(run_agent.call_args.kwargs["base_dir"], Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["max_iterations"], 7)
        self.assertEqual(run_agent.call_args.kwargs["command_timeout_ms"], 1234)
        self.assertEqual(run_agent.call_args.kwargs["max_output_tokens"], 8192)
        self.assertEqual(run_agent.call_args.kwargs["model_retries"], 2)
        self.assertEqual(run_agent.call_args.kwargs["model_retry_delay_ms"], 25)
        self.assertEqual(run_agent.call_args.kwargs["model_timeout_ms"], 45000)
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])
        self.assertEqual(run_agent.call_args.kwargs["approval_policy"], "allow")
        handler = run_agent.call_args.kwargs["approval_handler"]
        self.assertTrue(handler(ApprovalRequest(action_type="write_file", target="note.txt", risk="write")).approved)

    def test_main_one_shot_code_task_exits_nonzero_when_completion_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
                completion_ready=False,
                completion_blockers=["Final review did not report ready."],
            )
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(stdout),
            ):
                exit_code = main(["fix", "the", "test"])

        self.assertEqual(exit_code, 1)
        self.assertIn("done", stdout.getvalue())
        self.assertIn("Completion blockers:", stdout.getvalue())
        self.assertIn("Final review did not report ready.", stdout.getvalue())

    def test_main_print_mode_outputs_only_final_code_message(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
                completion_ready=False,
                completion_blockers=["Final review did not report ready."],
                final_review_changed_files=["M app.py"],
            )
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(stdout),
            ):
                exit_code = main(["-p", "--cwd", base, "fix", "the", "test"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "done\n")

    def test_main_print_mode_keeps_json_machine_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(stdout),
            ):
                exit_code = main(["-p", "--json", "--cwd", base, "fix", "the", "test"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "code")
        self.assertEqual(payload["message"], "done")
        self.assertEqual(payload["result"], "done")

    def test_main_runs_one_shot_code_task_with_json_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=2,
                observations=[],
                steps=[TaskStep(id=1, label="Read file", action_type="read_file", target="app.py", status="completed")],
                plan=[
                    PlanItem(step="Inspect failure", status="completed"),
                    PlanItem(step="Run verification", status="pending"),
                ],
                completion_ready=False,
                completion_blockers=["1 suggested verification check(s) are still pending after the latest project change."],
                completion_warnings=["Suggested verification checks are still pending after the latest project change."],
                verification_checks=["python -m unittest discover -s tests"],
                pending_verification_checks=["npm test"],
                failed_verification_checks=["npm test (exit=1)"],
                completion_blocked_count=1,
                latest_completion_blockers=["Final review did not report ready."],
                latest_completion_pending_verification_checks=["npm test"],
                latest_completion_failed_verification_checks=["npm run build (exit=1)"],
                latest_completion_final_review_issues=["Changed Python files have syntax errors."],
                latest_completion_final_review_changed_files=["M app.py"],
                latest_completion_tool_errors=["read_file: Tool execution failed: boom"],
                latest_completion_checkpoint_failures=["checkpoint_create: git diff failed."],
                latest_completion_active_background_processes=["bg-1: pid=123, cwd=web, command=npm run dev"],
                latest_completion_denied_approvals=["write_file note.txt: denied"],
                final_review_changed_files=["M app.py"],
            )
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_compact_context", return_value=(None, None, "No sessions found.")),
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "fix", "the", "test"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["kind"], "code")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["stopReason"], "blocked")
        self.assertEqual(payload["stop_reason"], "blocked")
        self.assertEqual(payload["message"], "done")
        self.assertEqual(payload["result"], "done")
        self.assertEqual(payload["runId"], "one-shot")
        self.assertEqual(payload["sessionId"], "one-shot")
        self.assertEqual(payload["session_id"], "one-shot")
        self.assertEqual(payload["iterations"], 2)
        self.assertEqual(payload["numTurns"], 2)
        self.assertEqual(payload["num_turns"], 2)
        self.assertEqual(payload["steps"], 1)
        self.assertEqual(payload["priorContext"], {"loaded": False, "source": "auto_compact", "runId": None})
        self.assertEqual(
            payload["plan"],
            [
                {"status": "completed", "step": "Inspect failure"},
                {"status": "pending", "step": "Run verification"},
            ],
        )
        self.assertFalse(payload["completionReady"])
        self.assertEqual(payload["completionBlockers"], ["1 suggested verification check(s) are still pending after the latest project change."])
        self.assertEqual(payload["completionWarnings"], ["Suggested verification checks are still pending after the latest project change."])
        self.assertEqual(payload["completionBlockedCount"], 1)
        self.assertEqual(payload["latestCompletionBlockers"], ["Final review did not report ready."])
        self.assertEqual(payload["latestCompletionPendingChecks"], ["npm test"])
        self.assertEqual(payload["latestCompletionFailedChecks"], ["npm run build (exit=1)"])
        self.assertEqual(payload["latestCompletionFinalReviewIssues"], ["Changed Python files have syntax errors."])
        self.assertEqual(payload["latestCompletionFinalReviewChangedFiles"], ["M app.py"])
        self.assertEqual(payload["latestCompletionToolErrors"], ["read_file: Tool execution failed: boom"])
        self.assertEqual(payload["latestCompletionCheckpointFailures"], ["checkpoint_create: git diff failed."])
        self.assertEqual(payload["latestCompletionActiveProcesses"], ["bg-1: pid=123, cwd=web, command=npm run dev"])
        self.assertEqual(payload["latestCompletionDeniedApprovals"], ["write_file note.txt: denied"])
        self.assertEqual(payload["changedFiles"], ["M app.py"])
        self.assertEqual(payload["verificationChecks"], ["python -m unittest discover -s tests"])
        self.assertEqual(payload["pendingVerificationChecks"], ["npm test"])
        self.assertEqual(payload["failedVerificationChecks"], ["npm test (exit=1)"])

    def test_main_one_shot_code_task_handles_keyboard_interrupt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=KeyboardInterrupt),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "fix", "the", "test"])

        self.assertEqual(exit_code, 130)
        self.assertEqual(stdout.getvalue().strip(), "Interrupted.")

    def test_main_one_shot_code_task_handles_keyboard_interrupt_with_json_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=KeyboardInterrupt),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "fix", "the", "test"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 130)
        self.assertEqual(payload["kind"], "interrupted")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "interrupted")
        self.assertEqual(payload["error"], "Interrupted.")

    def test_main_local_flag_handles_keyboard_interrupt(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.get_review_report", side_effect=KeyboardInterrupt),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--review"])

        self.assertEqual(exit_code, 130)
        self.assertEqual(stdout.getvalue().strip(), "Interrupted.")

    def test_main_one_shot_code_task_uses_provider_overrides(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()) as create_chat_client,
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--provider",
                        "minimax",
                        "--model",
                        "MiniMax-custom",
                        "--base-url",
                        "https://minimax.example",
                        "--api-key",
                        "secret-key",
                        "fix",
                    ]
                )

        provider_env = create_chat_client.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertIn("done", stdout.getvalue())
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "minimax")
        self.assertEqual(provider_env["MINIMAX_MODEL"], "MiniMax-custom")
        self.assertEqual(provider_env["MINIMAX_BASE_URL"], "https://minimax.example")
        self.assertEqual(provider_env["MINIMAX_API_KEY"], "secret-key")

    def test_main_one_shot_code_task_uses_project_provider_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps(
                    {
                        "provider": "deepseek",
                        "model": "deepseek-reasoner",
                        "base_url": "https://deepseek.example",
                    }
                ),
                encoding="utf-8",
            )
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.create_chat_client", return_value=object()) as create_chat_client,
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "fix"])

        provider_env = create_chat_client.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["VIBEAGENT_MODEL"], "deepseek-reasoner")
        self.assertEqual(provider_env["VIBEAGENT_BASE_URL"], "https://deepseek.example")

    def test_main_one_shot_code_task_uses_current_project_provider_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps({"provider": "deepseek", "model": "deepseek-reasoner"}),
                encoding="utf-8",
            )
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.Path.cwd", return_value=Path(base).resolve()),
                patch("vibeagent.cli.create_chat_client", return_value=object()) as create_chat_client,
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["fix"])

        provider_env = create_chat_client.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["VIBEAGENT_MODEL"], "deepseek-reasoner")

    def test_main_one_shot_code_task_uses_project_execution_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps(
                    {
                        "max_iterations": 9,
                        "command_timeout_ms": 45000,
                        "max_output_tokens": 8192,
                        "model_retries": 0,
                        "model_retry_delay_ms": 0,
                        "model_timeout_ms": 45000,
                    }
                ),
                encoding="utf-8",
            )
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "fix"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["max_iterations"], 9)
        self.assertEqual(run_agent.call_args.kwargs["command_timeout_ms"], 45000)
        self.assertEqual(run_agent.call_args.kwargs["max_output_tokens"], 8192)
        self.assertEqual(run_agent.call_args.kwargs["model_retries"], 0)
        self.assertEqual(run_agent.call_args.kwargs["model_retry_delay_ms"], 0)
        self.assertEqual(run_agent.call_args.kwargs["model_timeout_ms"], 45000)

    def test_main_one_shot_code_task_cli_execution_flags_win_over_project_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps(
                    {
                        "max_iterations": 9,
                        "command_timeout_ms": 45000,
                        "max_output_tokens": 8192,
                        "model_retries": 0,
                        "model_retry_delay_ms": 0,
                        "model_timeout_ms": 45000,
                    }
                ),
                encoding="utf-8",
            )
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--max-iterations",
                        "4",
                        "--command-timeout-ms",
                        "1000",
                        "--max-output-tokens",
                        "2048",
                        "--model-retries",
                        "3",
                        "--model-retry-delay-ms",
                        "50",
                        "--model-timeout-ms",
                        "60000",
                        "fix",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["max_iterations"], 4)
        self.assertEqual(run_agent.call_args.kwargs["command_timeout_ms"], 1000)
        self.assertEqual(run_agent.call_args.kwargs["max_output_tokens"], 2048)
        self.assertEqual(run_agent.call_args.kwargs["model_retries"], 3)
        self.assertEqual(run_agent.call_args.kwargs["model_retry_delay_ms"], 50)
        self.assertEqual(run_agent.call_args.kwargs["model_timeout_ms"], 60000)

    def test_main_cli_provider_override_wins_over_project_provider_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps({"provider": "deepseek", "model": "deepseek-reasoner"}),
                encoding="utf-8",
            )
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.create_chat_client", return_value=object()) as create_chat_client,
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--provider", "minimax", "--model-name", "MiniMax-custom", "fix"])

        provider_env = create_chat_client.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "minimax")
        self.assertEqual(provider_env["MINIMAX_MODEL"], "MiniMax-custom")
        self.assertEqual(provider_env["VIBEAGENT_MODEL"], "deepseek-reasoner")

    def test_main_model_alias_sets_one_shot_provider_model(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.create_chat_client", return_value=object()) as create_chat_client,
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--provider", "minimax", "--model", "MiniMax-custom", "fix"])

        provider_env = create_chat_client.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "minimax")
        self.assertEqual(provider_env["MINIMAX_MODEL"], "MiniMax-custom")

    def test_main_runs_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_doctor_text", return_value="Doctor:\n  provider: minimax") as get_doctor_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--doctor"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Doctor:", stdout.getvalue())
        self.assertEqual(get_doctor_text.call_args.args[0], Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_local_flag_with_json_output(self) -> None:
        stdout = io.StringIO()
        report = {
            "ok": True,
            "provider": "minimax",
            "model": "MiniMax-M2.7",
            "baseUrl": "https://api.minimaxi.com/anthropic",
            "apiKeyConfigured": True,
            "apiKeySource": "MINIMAX_API_KEY",
            "error": "",
            "message": "Resolved model provider configuration.",
        }
        rendered = "Model provider: minimax"

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_model_report", return_value=report) as get_model_report,
            patch("vibeagent.cli.format_model_report_text", return_value=rendered) as format_model_report_text,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--model"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["text"], rendered)
        self.assertEqual(payload["model"], report)
        get_model_report.assert_called_once()
        format_model_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_local_config_flag_reports_json_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "projectConfig": False,
                "projectConfigError": "",
                "provider": {"ok": True, "name": "deepseek", "model": "deepseek-reasoner", "baseUrl": "https://api.deepseek.com", "apiKeyConfigured": False, "apiKeySource": "", "error": ""},
                "execution": {"ok": True, "maxIterations": 9, "commandTimeoutMs": 120000, "maxOutputTokens": 8192, "modelRetries": 2, "modelRetryDelayMs": 25, "modelTimeoutMs": 45000, "error": ""},
                "costRates": {"ok": True, "configured": 0, "total": 4, "errors": []},
            }
            rendered = "Config:\n  provider: deepseek"

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_config_report", return_value=report) as get_config_report,
                patch("vibeagent.cli.format_config_report_text", return_value=rendered) as format_config_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--config",
                        "--provider",
                        "deepseek",
                        "--model-name",
                        "deepseek-reasoner",
                        "--max-iterations",
                        "9",
                        "--command-timeout-ms",
                        "120000",
                        "--max-output-tokens",
                        "8192",
                        "--model-retries",
                        "2",
                        "--model-retry-delay-ms",
                        "25",
                        "--model-timeout-ms",
                        "45000",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        provider_env = get_config_report.call_args.args[1]
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["text"], rendered)
        self.assertEqual(payload["config"], report)
        self.assertEqual(get_config_report.call_args.args[0], Path(base).resolve())
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["OPENAI_COMPAT_MODEL"], "deepseek-reasoner")
        self.assertEqual(get_config_report.call_args.kwargs["max_iterations"], 9)
        self.assertEqual(get_config_report.call_args.kwargs["command_timeout_ms"], 120000)
        self.assertEqual(get_config_report.call_args.kwargs["max_output_tokens"], 8192)
        self.assertEqual(get_config_report.call_args.kwargs["model_retries"], 2)
        self.assertEqual(get_config_report.call_args.kwargs["model_retry_delay_ms"], 25)
        self.assertEqual(get_config_report.call_args.kwargs["model_timeout_ms"], 45000)
        format_config_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_doctor_json_with_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch.dict(
                    "vibeagent.cli.os.environ",
                    {
                        "VIBEAGENT_PROVIDER": "minimax",
                        "MINIMAX_API_KEY": "secret-key",
                    },
                    clear=True,
                ),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--doctor"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["success"])
        self.assertIn("Doctor:", payload["text"])
        doctor = payload["doctor"]
        self.assertEqual(doctor["projectRoot"], str(Path(base).resolve()))
        self.assertEqual(doctor["provider"]["apiKeySource"], "MINIMAX_API_KEY")
        self.assertNotIn("secret-key", json.dumps(payload, ensure_ascii=False))
        self.assertEqual(doctor["commandHardBlocks"]["active"], doctor["commandHardBlocks"]["total"])
        self.assertTrue(any(check["command"] == "code ." and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "cmd.exe /c explorer.exe ." and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "rundll32 url.dll,FileProtocolHandler ." and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(
            any(
                check["command"] == "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command Start-Process ."
                and check["active"]
                for check in doctor["commandHardBlocks"]["checks"]
            )
        )
        self.assertTrue(any(check["command"] == "python3 -m webbrowser http://127.0.0.1:5173" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "python3 -c \"import webbrowser; webbrowser.open('http://127.0.0.1:5173')\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "python3 -c \"import webbrowser; webbrowser.get().open('http://127.0.0.1:5173')\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "python3 -c \"import os; os.startfile('.')\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "python3 -c \"import os; os.system('xdg-open .')\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "python3 - <<'PY'\nimport subprocess\nsubprocess.run(['xdg-open', '.'])\nPY" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "node -e \"require('child_process').exec('xdg-open .')\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "node -e \"const {exec}=require('child_process'); const cmd='xdg-open .'; exec(cmd)\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "node - <<'JS'\nrequire('child_process').exec('xdg-open .')\nJS" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "node -e \"require('shelljs').exec('xdg-open .')\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(any(check["command"] == "node -e \"require('execa').execaCommand('xdg-open .')\"" and check["active"] for check in doctor["commandHardBlocks"]["checks"]))
        self.assertTrue(
            any(
                check["command"] == "node --input-type=module -e \"import { exec } from 'node:child_process'; exec('xdg-open .')\""
                and check["active"]
                for check in doctor["commandHardBlocks"]["checks"]
            )
        )
        self.assertTrue(
            any(
                check["command"] == "node --input-type=module -e \"import { execaCommand } from 'execa'; execaCommand('xdg-open .')\""
                and check["active"]
                for check in doctor["commandHardBlocks"]["checks"]
            )
        )
        self.assertTrue(
            any(
                check["command"] == "node --input-type=module -e \"const cp = await import('node:child_process'); cp.exec('xdg-open .')\""
                and check["active"]
                for check in doctor["commandHardBlocks"]["checks"]
            )
        )
        self.assertTrue(
            any(
                check["command"] == "node --input-type=module -e \"const { execaCommand } = await import('execa'); execaCommand('xdg-open .')\""
                and check["active"]
                for check in doctor["commandHardBlocks"]["checks"]
            )
        )
        create_chat_client.assert_not_called()

    def test_main_runs_doctor_json_formats_report_without_rerunning_text(self) -> None:
        report = {"projectRoot": "/tmp/project", "provider": {"ok": True}, "costRates": {"ok": True}, "executables": {}, "commandHardBlocks": {}}
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_doctor_report", return_value=report) as get_doctor_report,
            patch("vibeagent.cli.format_doctor_report_text", return_value="Doctor:\n  provider: minimax") as format_doctor_report_text,
            patch("vibeagent.cli.get_doctor_text") as get_doctor_text,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--doctor"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["doctor"], report)
        self.assertEqual(payload["text"], "Doctor:\n  provider: minimax")
        get_doctor_report.assert_called_once()
        format_doctor_report_text.assert_called_once_with(report)
        get_doctor_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_tools_local_flag_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--tools"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Tools:", stdout.getvalue())
        self.assertIn("list_files", stdout.getvalue())
        self.assertIn("run_command", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_runs_tools_local_flag_with_json_output(self) -> None:
        stdout = io.StringIO()
        report = {
            "ok": True,
            "total": 1,
            "approvalRequired": {"total": 1, "tools": ["write_file"]},
            "readOnly": {"total": 0, "tools": []},
            "categories": [{"name": "edit", "total": 1, "tools": ["write_file"]}],
            "tools": [{"name": "write_file", "category": "edit", "approvalRequired": True}],
            "message": "Found 1 model tool(s).",
        }

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tools_report", return_value=report) as get_tools_report,
            patch("vibeagent.cli.format_tools_report_text", return_value="Tools:\n  total: 1\n  approvalRequired: 1"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--tools"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertIn("Tools:", payload["text"])
        self.assertEqual(payload["tools"], report)
        get_tools_report.assert_called_once_with()
        create_chat_client.assert_not_called()

    def test_main_runs_tool_search_local_flag_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--tool-search", "verification"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Tool search:", stdout.getvalue())
        self.assertIn("session_verification", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_runs_tool_search_local_flag_with_json_output(self) -> None:
        stdout = io.StringIO()
        report = {
            "ok": True,
            "query": "read",
            "matches": [{"name": "read_file", "category": "project", "approvalRequired": False}],
            "total": 1,
            "shown": 1,
            "truncated": False,
            "category": None,
            "approvalRequired": None,
            "suggestions": ["read_file"],
            "message": "Found 1 matching tool(s).",
        }

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tool_search_report", return_value=report) as get_tool_search_report,
            patch("vibeagent.cli.format_tool_search_report_text", return_value="Tool search:\n  matches: 1/1"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--tool-search", "read"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["toolSearch"], report)
        get_tool_search_report.assert_called_once_with("read", max_matches=20, category=None, approval_required=None)
        create_chat_client.assert_not_called()

    def test_main_runs_filtered_tool_search_local_flag_with_json_output(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(
                [
                    "--json",
                    "--tool-search",
                    "verification",
                    "--tool-search-max",
                    "3",
                    "--tool-search-category",
                    "session",
                    "--tool-search-approval",
                    "no",
                ]
            )

        payload = json.loads(stdout.getvalue())
        matches = payload["toolSearch"]["matches"]
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["toolSearch"]["shown"], 3)
        self.assertTrue(all(match["category"] == "session" for match in matches))
        self.assertTrue(all(not match["approvalRequired"] for match in matches))
        create_chat_client.assert_not_called()

    def test_tool_search_filter_options_require_tool_search(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--tool-search-category", "session"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["kind"], "error")
        self.assertEqual(payload["error"], "--tool-search-category can only be used with --tool-search.")
        create_chat_client.assert_not_called()

    def test_main_runs_review_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_review_report", return_value={"ready": True}) as get_review_report,
                patch("vibeagent.cli.format_review_report_text", return_value="Review:\n  ready: yes") as format_review_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--review"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Review:", stdout.getvalue())
        get_review_report.assert_called_once_with(Path(base).resolve(), max_files=200, max_checks=5)
        format_review_report_text.assert_called_once_with({"ready": True})
        create_chat_client.assert_not_called()

    def test_main_runs_review_local_flag_with_limits_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_review_report", return_value={"ready": True}) as get_review_report,
                patch("vibeagent.cli.format_review_report_text", return_value="Review:\n  ready: yes") as format_review_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--review", "--review-max-files", "1", "--review-max-checks", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Review:", stdout.getvalue())
        get_review_report.assert_called_once_with(Path(base).resolve(), max_files=1, max_checks=2)
        format_review_report_text.assert_called_once_with({"ready": True})
        create_chat_client.assert_not_called()

    def test_main_runs_review_local_flag_with_json_output(self) -> None:
        stdout = io.StringIO()
        review = {"ready": False, "blockingIssues": ["Changed Python files have syntax errors."]}

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_review_report", return_value=review),
            patch("vibeagent.cli.format_review_report_text", return_value="Review:\n  ready: no"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--review"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(
            payload,
            {
                "kind": "local",
                "success": False,
                "status": "failed",
                "text": "Review:\n  ready: no",
                "review": review,
            },
        )
        create_chat_client.assert_not_called()

    def test_main_runs_review_json_with_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "package.json").write_text('{"scripts":{"test":"node test.js"}}\n', encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["--json", "--cwd", base, "--review", "--review-max-files", "10", "--review-max-checks", "5"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["success"])
        self.assertIn("Review:", payload["text"])
        review = payload["review"]
        self.assertEqual(review["projectRoot"], str(root.resolve()))
        self.assertTrue(review["ready"])
        self.assertEqual(review["changedFiles"]["total"], 1)
        commands = [item["command"] for item in review["suggestedChecks"]["commands"] if isinstance(item, dict)]
        self.assertIn("npm run test", commands)

    def test_main_runs_handoff_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_handoff_report", return_value={"ready": True}) as get_handoff_report,
                patch("vibeagent.cli.format_handoff_report_text", return_value="Handoff:\n  ready: yes") as format_handoff_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--handoff"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Handoff:", stdout.getvalue())
        get_handoff_report.assert_called_once_with(
            Path(base).resolve(),
            max_files=200,
            max_checks=10,
            max_status_chars=4000,
            max_plan_chars=4000,
        )
        format_handoff_report_text.assert_called_once_with({"ready": True})
        create_chat_client.assert_not_called()

    def test_main_runs_handoff_local_flag_with_limits_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_handoff_report", return_value={"ready": True}) as get_handoff_report,
                patch("vibeagent.cli.format_handoff_report_text", return_value="Handoff:\n  ready: yes") as format_handoff_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--handoff",
                        "--handoff-max-files",
                        "1",
                        "--handoff-max-checks",
                        "2",
                        "--handoff-max-status-chars",
                        "3000",
                        "--handoff-max-plan-chars",
                        "4000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Handoff:", stdout.getvalue())
        get_handoff_report.assert_called_once_with(
            Path(base).resolve(),
            max_files=1,
            max_checks=2,
            max_status_chars=3000,
            max_plan_chars=4000,
        )
        format_handoff_report_text.assert_called_once_with({"ready": True})
        create_chat_client.assert_not_called()

    def test_main_runs_handoff_local_flag_with_json_output(self) -> None:
        stdout = io.StringIO()
        handoff = {"ready": False, "blockingIssues": ["Suggested checks have not been run."]}

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_handoff_report", return_value=handoff),
            patch("vibeagent.cli.format_handoff_report_text", return_value="Handoff:\n  ready: no"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--handoff"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(
            payload,
            {
                "kind": "local",
                "success": False,
                "status": "failed",
                "text": "Handoff:\n  ready: no",
                "handoff": handoff,
            },
        )
        create_chat_client.assert_not_called()

    def test_main_runs_handoff_json_with_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "package.json").write_text('{"scripts":{"test":"node test.js"}}\n', encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["--json", "--cwd", base, "--handoff", "--handoff-max-files", "10", "--handoff-max-checks", "5"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["success"])
        self.assertIn("Handoff:", payload["text"])
        handoff = payload["handoff"]
        self.assertEqual(handoff["projectRoot"], str(root.resolve()))
        self.assertTrue(handoff["ready"])
        self.assertEqual(handoff["changedFiles"]["total"], 1)
        commands = [item["command"] for item in handoff["suggestedChecks"]["commands"] if isinstance(item, dict)]
        self.assertIn("npm run test", commands)
        self.assertEqual(handoff["blockingIssues"], [])

    def test_main_runs_changes_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_changes_report", return_value={"ok": True}) as get_changes_report,
                patch("vibeagent.cli.format_changes_report_text", return_value="Changes:\n  changedFiles: 1") as format_changes_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--changes"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Changes:", stdout.getvalue())
        get_changes_report.assert_called_once_with(Path(base).resolve(), max_files=200)
        format_changes_report_text.assert_called_once_with({"ok": True})
        create_chat_client.assert_not_called()

    def test_main_runs_changes_local_flag_with_max_files_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_changes_report", return_value={"ok": True}) as get_changes_report,
                patch("vibeagent.cli.format_changes_report_text", return_value="Changes:\n  shownFiles: 1/3") as format_changes_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--changes", "--changes-max-files", "1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Changes:", stdout.getvalue())
        get_changes_report.assert_called_once_with(Path(base).resolve(), max_files=1)
        format_changes_report_text.assert_called_once_with({"ok": True})
        create_chat_client.assert_not_called()

    def test_main_runs_changes_json_with_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("print('new')\n", encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["--json", "--cwd", base, "--changes", "--changes-max-files", "10"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["success"])
        self.assertIn("Changes:", payload["text"])
        changes = payload["changes"]
        self.assertEqual(changes["projectRoot"], str(root.resolve()))
        self.assertTrue(changes["ok"])
        self.assertEqual(changes["changedFiles"]["total"], 1)
        self.assertEqual(changes["counts"]["unstaged"], 1)

    def test_main_runs_diff_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_diff_text", return_value="Diff:\n  scope: staged") as get_diff_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--diff", "--staged app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Diff:", stdout.getvalue())
        get_diff_text.assert_called_once_with(Path(base).resolve(), "--staged app.py", max_chars=12000)
        create_chat_client.assert_not_called()

    def test_main_runs_diff_local_flag_with_max_chars_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_diff_text", return_value="Diff:\n  truncated: yes") as get_diff_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--diff", "app.py", "--diff-max-chars", "1000"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Diff:", stdout.getvalue())
        get_diff_text.assert_called_once_with(Path(base).resolve(), "app.py", max_chars=1000)
        create_chat_client.assert_not_called()

    def test_main_runs_diff_local_flag_with_unquoted_staged_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_diff_text", return_value="Diff:\n  scope: staged") as get_diff_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--diff", "--staged", "app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Diff:", stdout.getvalue())
        get_diff_text.assert_called_once_with(Path(base).resolve(), "--staged app.py", max_chars=12000)
        create_chat_client.assert_not_called()

    def test_main_runs_diff_hunks_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_diff_hunks_text", return_value="Diff hunks:\n  hunks: 1/1") as get_diff_hunks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--diff-hunks", "--staged", "app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Diff hunks:", stdout.getvalue())
        get_diff_hunks_text.assert_called_once_with(
            Path(base).resolve(),
            "--staged app.py",
            max_hunks=80,
            max_lines_per_hunk=80,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_diff_hunks_local_flag_with_limits_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_diff_hunks_text", return_value="Diff hunks:\n  truncated: yes") as get_diff_hunks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--diff-hunks",
                        "app.py",
                        "--diff-hunks-max-hunks",
                        "3",
                        "--diff-hunks-max-lines",
                        "4",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Diff hunks:", stdout.getvalue())
        get_diff_hunks_text.assert_called_once_with(
            Path(base).resolve(),
            "app.py",
            max_hunks=3,
            max_lines_per_hunk=4,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_diff_contexts_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_diff_contexts_text", return_value="Diff contexts:\n  contexts: 1/1") as get_diff_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--diff-contexts", "--staged", "app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Diff contexts:", stdout.getvalue())
        get_diff_contexts_text.assert_called_once_with(
            Path(base).resolve(),
            "--staged app.py",
            context_lines=5,
            max_hunks=80,
            max_bytes_per_context=20000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_diff_contexts_local_flag_with_limits_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_diff_contexts_text", return_value="Diff contexts:\n  contexts: 1/1") as get_diff_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--diff-contexts",
                        "app.py",
                        "--diff-context-lines",
                        "2",
                        "--diff-contexts-max-hunks",
                        "3",
                        "--diff-contexts-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Diff contexts:", stdout.getvalue())
        get_diff_contexts_text.assert_called_once_with(
            Path(base).resolve(),
            "app.py",
            context_lines=2,
            max_hunks=3,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_diff_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("before\nold\nafter\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("before\nnew\nafter\n", encoding="utf-8")

            diff_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as diff_create_chat_client,
                redirect_stdout(diff_stdout),
            ):
                diff_exit = main(["--json", "--cwd", base, "--diff", "app.py"])

            hunks_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as hunks_create_chat_client,
                redirect_stdout(hunks_stdout),
            ):
                hunks_exit = main(["--json", "--cwd", base, "--diff-hunks", "app.py"])

            contexts_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as contexts_create_chat_client,
                redirect_stdout(contexts_stdout),
            ):
                contexts_exit = main(["--json", "--cwd", base, "--diff-contexts", "app.py", "--diff-context-lines", "1"])

        diff_payload = json.loads(diff_stdout.getvalue())
        hunks_payload = json.loads(hunks_stdout.getvalue())
        contexts_payload = json.loads(contexts_stdout.getvalue())

        self.assertEqual(diff_exit, 0)
        self.assertEqual(diff_payload["diff"]["path"], "app.py")
        self.assertIn("+new", diff_payload["diff"]["diff"])
        self.assertEqual(hunks_exit, 0)
        self.assertEqual(hunks_payload["diffHunks"]["hunks"]["shown"], 1)
        self.assertEqual(hunks_payload["diffHunks"]["hunks"]["items"][0]["file"], "app.py")
        self.assertEqual(contexts_exit, 0)
        self.assertEqual(contexts_payload["diffContexts"]["contexts"]["shown"], 1)
        self.assertTrue(contexts_payload["diffContexts"]["contexts"]["items"][0]["context"]["ok"])
        self.assertIn("2: new", contexts_payload["diffContexts"]["contexts"]["items"][0]["context"]["content"])
        diff_create_chat_client.assert_not_called()
        hunks_create_chat_client.assert_not_called()
        contexts_create_chat_client.assert_not_called()

    def test_main_reports_staged_without_diff_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--staged", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--staged can only be used with --diff, --diff-hunks, or --diff-contexts.\n")
        create_chat_client.assert_not_called()

    def test_main_runs_init_local_flag_with_selected_instruction_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.init_project_instructions", return_value="Created CLAUDE.md.") as init_project_instructions,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--init", "CLAUDE.md"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "Created CLAUDE.md.\n")
        init_project_instructions.assert_called_once_with(Path(base).resolve(), "CLAUDE.md")
        create_chat_client.assert_not_called()

    def test_main_runs_init_local_flag_with_json_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "requestedFile": "CLAUDE.md",
                "fileName": "CLAUDE.md",
                "path": str(Path(base).resolve() / "CLAUDE.md"),
                "ok": True,
                "created": True,
                "exists": True,
                "error": "",
                "message": "Created CLAUDE.md.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_init_report", return_value=report) as get_init_report,
                patch("vibeagent.cli.format_init_report_text", return_value="Created CLAUDE.md."),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--init", "CLAUDE.md"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["init"], report)
        self.assertEqual(payload["text"], "Created CLAUDE.md.")
        get_init_report.assert_called_once_with(Path(base).resolve(), "CLAUDE.md")
        create_chat_client.assert_not_called()

    def test_main_runs_sessions_json_with_structured_payload(self) -> None:
        report = {"exists": True, "ok": True, "sessions": {"total": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_sessions_report", return_value=report) as get_sessions_report,
                patch("vibeagent.cli.format_sessions_report_text", return_value="Recent sessions:\n  run-1") as format_sessions_report_text,
                patch("vibeagent.cli.get_sessions_text") as get_sessions_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--sessions"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessions"], report)
        self.assertEqual(payload["text"], "Recent sessions:\n  run-1")
        get_sessions_report.assert_called_once_with(Path(base).resolve())
        format_sessions_report_text.assert_called_once_with(report)
        get_sessions_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_last_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "status": "completed"}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_last_session_report", return_value=report) as get_last_session_report,
                patch("vibeagent.cli.format_session_summary_report_text", return_value="Session: run-1\n  status: completed") as format_session_summary_report_text,
                patch("vibeagent.cli.get_last_session_text") as get_last_session_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--last"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionSummary"], report)
        self.assertEqual(payload["text"], "Session: run-1\n  status: completed")
        get_last_session_report.assert_called_once_with(Path(base).resolve())
        format_session_summary_report_text.assert_called_once_with(report)
        get_last_session_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "status": "completed"}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_report", return_value=report) as get_session_report,
                patch("vibeagent.cli.format_session_summary_report_text", return_value="Session: run-1\n  status: completed") as format_session_summary_report_text,
                patch("vibeagent.cli.get_session_text") as get_session_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--session", "run-1"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionSummary"], report)
        self.assertEqual(payload["text"], "Session: run-1\n  status: completed")
        get_session_report.assert_called_once_with("run-1", Path(base).resolve())
        format_session_summary_report_text.assert_called_once_with(report)
        get_session_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_usage_json_with_structured_payload(self) -> None:
        report = {"exists": True, "ok": True, "usage": {"sessions": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_usage_report", return_value=report) as get_usage_report,
                patch("vibeagent.cli.format_usage_report_text", return_value="Usage:\n  sessions: 1") as format_usage_report_text,
                patch("vibeagent.cli.get_usage_text") as get_usage_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--usage"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["usage"], report)
        self.assertEqual(payload["text"], "Usage:\n  sessions: 1")
        get_usage_report.assert_called_once_with(Path(base).resolve())
        format_usage_report_text.assert_called_once_with(report)
        get_usage_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_usage_json_reports_missing_sessions_as_failure(self) -> None:
        report = {"exists": False, "ok": False, "status": "missing", "message": "No sessions found."}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_usage_report", return_value=report) as get_usage_report,
                patch("vibeagent.cli.format_usage_report_text", return_value="No sessions found.") as format_usage_report_text,
                patch("vibeagent.cli.get_usage_text") as get_usage_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--usage"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["usage"], report)
        self.assertEqual(payload["text"], "No sessions found.")
        get_usage_report.assert_called_once_with(Path(base).resolve())
        format_usage_report_text.assert_called_once_with(report)
        get_usage_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_cost_json_with_structured_payload(self) -> None:
        report = {"exists": True, "ok": True, "estimate": {"available": True, "estimatedCostUsd": "0.000001"}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_cost_report", return_value=report) as get_cost_report,
                patch("vibeagent.cli.format_cost_report_text", return_value="Cost:\n  estimatedCostUsd: $0.000001") as format_cost_report_text,
                patch("vibeagent.cli.get_cost_text") as get_cost_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--cost"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["cost"], report)
        self.assertEqual(payload["text"], "Cost:\n  estimatedCostUsd: $0.000001")
        get_cost_report.assert_called_once_with(Path(base).resolve())
        format_cost_report_text.assert_called_once_with(report)
        get_cost_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_plan_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_plan_report", return_value={"session": "run-1", "ok": True}) as get_plan_report,
                patch("vibeagent.cli.get_plan_text", return_value="Plan:\n  session: run-1") as get_plan_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--plan", "run-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Plan:", stdout.getvalue())
        get_plan_report.assert_not_called()
        get_plan_text.assert_called_once_with(Path(base).resolve(), "run-1")
        create_chat_client.assert_not_called()

    def test_main_runs_plan_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "items": []}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_plan_report", return_value=report) as get_plan_report,
                patch("vibeagent.cli.get_plan_text", return_value="unused") as get_plan_text,
                patch(
                    "vibeagent.cli.format_session_plan_report_text",
                    return_value="Plan:\n  session: run-1",
                ) as format_session_plan_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--plan", "run-1"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionPlan"], report)
        get_plan_report.assert_called_once_with(Path(base).resolve(), "run-1")
        format_session_plan_report_text.assert_called_once_with(report)
        get_plan_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_transcript_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_transcript_report", return_value={"session": "run-1", "ok": True}) as get_transcript_report,
                patch("vibeagent.cli.get_transcript_text", return_value="Transcript:\n  session: run-1") as get_transcript_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--transcript",
                        "run-1",
                        "--session-transcript-event-max",
                        "3",
                        "--session-max-text",
                        "120",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Transcript:", stdout.getvalue())
        get_transcript_report.assert_not_called()
        get_transcript_text.assert_called_once_with(Path(base).resolve(), "run-1", max_events=3, max_text=120)
        create_chat_client.assert_not_called()

    def test_main_runs_transcript_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "events": {"total": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_transcript_report", return_value=report) as get_transcript_report,
                patch("vibeagent.cli.get_transcript_text", return_value="unused") as get_transcript_text,
                patch(
                    "vibeagent.cli.format_session_transcript_report_text",
                    return_value="Transcript:\n  session: run-1",
                ) as format_session_transcript_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--transcript",
                        "run-1",
                        "--session-transcript-event-max",
                        "3",
                        "--session-max-text",
                        "120",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionTranscript"], report)
        get_transcript_report.assert_called_once_with(Path(base).resolve(), "run-1", max_events=3, max_text=120)
        format_session_transcript_report_text.assert_called_once_with(report)
        get_transcript_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_search_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_search_report", return_value={"session": "run-1", "ok": True}) as get_session_search_report,
                patch("vibeagent.cli.get_session_search_text", return_value="Session search:\n  session: run-1") as get_session_search_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--session-search",
                        " missing config ",
                        "--session-search-run",
                        " run-1 ",
                        "--session-search-match-max",
                        "3",
                        "--session-search-case-sensitive",
                        "--session-max-text",
                        "120",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Session search:", stdout.getvalue())
        get_session_search_report.assert_not_called()
        get_session_search_text.assert_called_once_with(
            Path(base).resolve(),
            "missing config",
            "run-1",
            max_matches=3,
            max_text=120,
            case_sensitive=True,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_session_search_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "matches": {"total": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_search_report", return_value=report) as get_session_search_report,
                patch("vibeagent.cli.get_session_search_text", return_value="unused") as get_session_search_text,
                patch(
                    "vibeagent.cli.format_session_search_report_text",
                    return_value="Session search:\n  session: run-1",
                ) as format_session_search_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--session-search",
                        "missing config",
                        "--session-search-run",
                        "run-1",
                        "--session-search-match-max",
                        "3",
                        "--session-search-case-sensitive",
                        "--session-max-text",
                        "120",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionSearch"], report)
        expected_kwargs = {"max_matches": 3, "max_text": 120, "case_sensitive": True}
        get_session_search_report.assert_called_once_with(Path(base).resolve(), "missing config", "run-1", **expected_kwargs)
        format_session_search_report_text.assert_called_once_with(report)
        get_session_search_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_commands_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_commands_report", return_value={"session": "run-1", "ok": True}) as get_session_commands_report,
                patch("vibeagent.cli.get_session_commands_text", return_value="Command results:\n  session: run-1") as get_session_commands_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-commands", "run-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Command results:", stdout.getvalue())
        get_session_commands_report.assert_not_called()
        get_session_commands_text.assert_called_once_with(Path(base).resolve(), "run-1")
        create_chat_client.assert_not_called()

    def test_main_runs_session_commands_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "commands": {"total": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_commands_report", return_value=report) as get_session_commands_report,
                patch("vibeagent.cli.get_session_commands_text", return_value="unused") as get_session_commands_text,
                patch(
                    "vibeagent.cli.format_session_commands_report_text",
                    return_value="Command results:\n  session: run-1",
                ) as format_session_commands_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--session-commands", "run-1", "--session-max-output-chars", "0"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionCommands"], report)
        get_session_commands_report.assert_called_once_with(Path(base).resolve(), "run-1", max_output_chars=0)
        format_session_commands_report_text.assert_called_once_with(report)
        get_session_commands_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_output_contexts_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_output_contexts_report", return_value={"session": "run-1", "ok": True}) as get_session_output_contexts_report,
                patch("vibeagent.cli.get_session_output_contexts_text", return_value="Session output contexts:\n  session: run-1") as get_session_output_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--session-output-contexts",
                        "run-1",
                        "--session-output-command-max",
                        "3",
                        "--session-output-max-chars",
                        "4000",
                        "--session-output-context-lines",
                        "2",
                        "--session-output-context-max",
                        "5",
                        "--session-output-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Session output contexts:", stdout.getvalue())
        get_session_output_contexts_report.assert_not_called()
        get_session_output_contexts_text.assert_called_once_with(
            Path(base).resolve(),
            "run-1",
            max_commands=3,
            max_output_chars=4000,
            context_lines=2,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_session_output_contexts_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "contexts": {"total": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_output_contexts_report", return_value=report) as get_session_output_contexts_report,
                patch(
                    "vibeagent.cli.format_session_output_contexts_report_text",
                    return_value="Session output contexts:\n  session: run-1",
                ) as format_session_output_contexts_report_text,
                patch("vibeagent.cli.get_session_output_contexts_text", return_value="old text path") as get_session_output_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--session-output-contexts",
                        "run-1",
                        "--session-output-command-max",
                        "3",
                        "--session-output-max-chars",
                        "4000",
                        "--session-output-context-lines",
                        "2",
                        "--session-output-context-max",
                        "5",
                        "--session-output-context-max-bytes",
                        "1000",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionOutputContexts"], report)
        self.assertIn("Session output contexts:", payload["text"])
        expected_kwargs = {
            "max_commands": 3,
            "max_output_chars": 4000,
            "context_lines": 2,
            "max_contexts": 5,
            "max_bytes_per_context": 1000,
        }
        get_session_output_contexts_report.assert_called_once_with(Path(base).resolve(), "run-1", **expected_kwargs)
        format_session_output_contexts_report_text.assert_called_once_with(report)
        get_session_output_contexts_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_output_diagnostics_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_output_diagnostics_report", return_value={"session": "run-1", "ok": True}) as get_session_output_diagnostics_report,
                patch("vibeagent.cli.get_session_output_diagnostics_text", return_value="Session output diagnostics:\n  session: run-1") as get_session_output_diagnostics_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--session-output-diagnostics",
                        "run-1",
                        "--session-output-command-max",
                        "3",
                        "--session-output-max-chars",
                        "4000",
                        "--session-output-context-lines",
                        "2",
                        "--session-output-context-max",
                        "5",
                        "--session-output-context-max-bytes",
                        "1000",
                        "--session-output-diagnostic-max",
                        "4",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Session output diagnostics:", stdout.getvalue())
        get_session_output_diagnostics_report.assert_not_called()
        get_session_output_diagnostics_text.assert_called_once_with(
            Path(base).resolve(),
            "run-1",
            max_commands=3,
            max_output_chars=4000,
            context_lines=2,
            max_diagnostics=4,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_session_output_diagnostics_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "diagnostics": {"total": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_output_diagnostics_report", return_value=report) as get_session_output_diagnostics_report,
                patch(
                    "vibeagent.cli.format_session_output_diagnostics_report_text",
                    return_value="Session output diagnostics:\n  session: run-1",
                ) as format_session_output_diagnostics_report_text,
                patch("vibeagent.cli.get_session_output_diagnostics_text", return_value="Session output diagnostics:\n  session: run-1") as get_session_output_diagnostics_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--session-output-diagnostics",
                        "run-1",
                        "--session-output-command-max",
                        "3",
                        "--session-output-max-chars",
                        "4000",
                        "--session-output-context-lines",
                        "2",
                        "--session-output-context-max",
                        "5",
                        "--session-output-context-max-bytes",
                        "1000",
                        "--session-output-diagnostic-max",
                        "4",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionOutputDiagnostics"], report)
        self.assertIn("Session output diagnostics:", payload["text"])
        expected_kwargs = {
            "max_commands": 3,
            "max_output_chars": 4000,
            "context_lines": 2,
            "max_diagnostics": 4,
            "max_contexts": 5,
            "max_bytes_per_context": 1000,
        }
        get_session_output_diagnostics_report.assert_called_once_with(Path(base).resolve(), "run-1", **expected_kwargs)
        format_session_output_diagnostics_report_text.assert_called_once_with(report)
        get_session_output_diagnostics_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_session_output_analysis_local_flags_exit_nonzero_for_unreadable_contexts(self) -> None:
        cases = [
            (
                [
                    "--session-output-contexts",
                    "run-1",
                    "--session-output-command-max",
                    "3",
                    "--session-output-max-chars",
                    "4000",
                    "--session-output-context-lines",
                    "2",
                    "--session-output-context-max",
                    "5",
                    "--session-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_session_output_contexts_text",
                "Session output contexts:\n  ok: yes\n  contexts: 0/1",
                {
                    "max_commands": 3,
                    "max_output_chars": 4000,
                    "context_lines": 2,
                    "max_contexts": 5,
                    "max_bytes_per_context": 1000,
                },
            ),
            (
                [
                    "--session-output-diagnostics",
                    "run-1",
                    "--session-output-command-max",
                    "3",
                    "--session-output-max-chars",
                    "4000",
                    "--session-output-context-lines",
                    "2",
                    "--session-output-context-max",
                    "5",
                    "--session-output-context-max-bytes",
                    "1000",
                    "--session-output-diagnostic-max",
                    "4",
                ],
                "vibeagent.cli.get_session_output_diagnostics_text",
                "Session output diagnostics:\n  ok: yes\n  diagnostics: 1/1\n  contexts: 0/1",
                {
                    "max_commands": 3,
                    "max_output_chars": 4000,
                    "context_lines": 2,
                    "max_diagnostics": 4,
                    "max_contexts": 5,
                    "max_bytes_per_context": 1000,
                },
            ),
        ]

        for argv_tail, patch_target, text, expected_kwargs in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            getter.assert_called_once_with(Path(base).resolve(), "run-1", **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_session_output_analysis_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"session": "run-1", "exists": True, "ok": True, "contexts": {"ok": 0, "total": 1}}
            text = "Session output contexts:\n  ok: yes\n  contexts: 0/1"

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_output_contexts_report", return_value=report) as get_session_output_contexts_report,
                patch("vibeagent.cli.format_session_output_contexts_report_text", return_value=text) as format_session_output_contexts_report_text,
                patch("vibeagent.cli.get_session_output_contexts_text") as get_session_output_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--session-output-contexts", "run-1"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], text)
        self.assertEqual(payload["sessionOutputContexts"], report)
        get_session_output_contexts_report.assert_called_once_with(
            Path(base).resolve(),
            "run-1",
            max_commands=20,
            max_output_chars=20000,
            context_lines=5,
            max_contexts=20,
            max_bytes_per_context=20000,
        )
        format_session_output_contexts_report_text.assert_called_once_with(report)
        get_session_output_contexts_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_session_output_diagnostics_json_reports_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "session": "run-1",
                "exists": True,
                "ok": True,
                "diagnostics": {"shown": 1, "total": 1, "items": []},
                "contexts": {"ok": 0, "total": 1, "items": []},
            }
            text = "Session output diagnostics:\n  ok: yes\n  diagnostics: 1/1\n  contexts: 0/1"

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_output_diagnostics_report", return_value=report) as get_session_output_diagnostics_report,
                patch("vibeagent.cli.format_session_output_diagnostics_report_text", return_value=text) as format_session_output_diagnostics_report_text,
                patch("vibeagent.cli.get_session_output_diagnostics_text") as get_session_output_diagnostics_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--session-output-diagnostics", "run-1"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], text)
        self.assertEqual(payload["sessionOutputDiagnostics"], report)
        get_session_output_diagnostics_report.assert_called_once_with(
            Path(base).resolve(),
            "run-1",
            max_commands=20,
            max_output_chars=20000,
            context_lines=5,
            max_diagnostics=50,
            max_contexts=20,
            max_bytes_per_context=20000,
        )
        format_session_output_diagnostics_report_text.assert_called_once_with(report)
        get_session_output_diagnostics_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_files_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_files_report", return_value={"session": "run-1", "ok": True}) as get_session_files_report,
                patch("vibeagent.cli.get_session_files_text", return_value="Session files:\n  session: run-1") as get_session_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-files", "run-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session files:", stdout.getvalue())
        get_session_files_report.assert_not_called()
        get_session_files_text.assert_called_once_with(Path(base).resolve(), "run-1")
        create_chat_client.assert_not_called()

    def test_main_runs_session_files_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "files": {"total": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_files_report", return_value=report) as get_session_files_report,
                patch("vibeagent.cli.get_session_files_text", return_value="unused") as get_session_files_text,
                patch(
                    "vibeagent.cli.format_session_files_report_text",
                    return_value="Session files:\n  session: run-1",
                ) as format_session_files_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--session-files", "run-1", "--session-max-files", "3"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionFiles"], report)
        get_session_files_report.assert_called_once_with(Path(base).resolve(), "run-1", max_files=3)
        format_session_files_report_text.assert_called_once_with(report)
        get_session_files_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_failures_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_failures_report", return_value={"session": "run-1", "ok": True}) as get_session_failures_report,
                patch("vibeagent.cli.get_session_failures_text", return_value="Session failures:\n  session: run-1") as get_session_failures_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-failures", "run-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session failures:", stdout.getvalue())
        get_session_failures_report.assert_not_called()
        get_session_failures_text.assert_called_once_with(Path(base).resolve(), "run-1")
        create_chat_client.assert_not_called()

    def test_main_session_failures_exits_nonzero_when_failures_exist(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "session": "run-1",
                "exists": True,
                "ok": False,
                "status": "failed",
                "failures": {"total": 1, "shown": 1, "items": [{"name": "run_command"}]},
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_failures_report", return_value=report) as get_session_failures_report,
                patch(
                    "vibeagent.cli.format_session_failures_report_text",
                    return_value=(
                        "Session failures:\n"
                        "  session: run-1\n"
                        "  failures: 1\n"
                        "  shown: 1/1\n"
                        "  - #2 command: run_command\n"
                    ),
                ) as format_session_failures_report_text,
                patch(
                    "vibeagent.cli.get_session_failures_text",
                    return_value="old text path",
                ) as get_session_failures_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-failures", "run-1", "--json"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertIn("failures: 1", payload["text"])
        self.assertEqual(payload["sessionFailures"], report)
        get_session_failures_report.assert_called_once_with(Path(base).resolve(), "run-1")
        format_session_failures_report_text.assert_called_once_with(report)
        get_session_failures_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_verification_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_verification_report", return_value={"session": "run-1", "ok": True}) as get_session_verification_report,
                patch("vibeagent.cli.get_session_verification_text", return_value="Session verification:\n  session: run-1") as get_session_verification_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-verification", "run-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session verification:", stdout.getvalue())
        get_session_verification_report.assert_not_called()
        get_session_verification_text.assert_called_once_with(Path(base).resolve(), "run-1")
        create_chat_client.assert_not_called()

    def test_main_runs_session_verification_local_flag_with_max_checks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_verification_report", return_value={"session": "run-1", "ok": True}) as get_session_verification_report,
                patch("vibeagent.cli.get_session_verification_text", return_value="Session verification:\n  session: run-1") as get_session_verification_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-verification", "run-1", "--session-max-checks", "3"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session verification:", stdout.getvalue())
        get_session_verification_report.assert_not_called()
        get_session_verification_text.assert_called_once_with(Path(base).resolve(), "run-1", max_checks=3)
        create_chat_client.assert_not_called()

    def test_main_session_verification_exits_nonzero_with_pending_checks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "session": "run-1",
                "exists": True,
                "ok": False,
                "ready": False,
                "status": "blocked",
                "pending": {"total": 1, "items": ["npm test"]},
                "failed": {"total": 0, "items": []},
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_verification_report", return_value=report) as get_session_verification_report,
                patch(
                    "vibeagent.cli.format_session_verification_report_text",
                    return_value=(
                        "Session verification:\n"
                        "  verified: none\n"
                        "  pendingChecks: 1/1\n"
                        "    - npm test\n"
                        "  failedChecks: none"
                    ),
                ) as format_session_verification_report_text,
                patch(
                    "vibeagent.cli.get_session_verification_text",
                    return_value="old text path",
                ) as get_session_verification_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-verification", "run-1", "--json"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertIn("pendingChecks:", payload["text"])
        self.assertEqual(payload["sessionVerification"], report)
        get_session_verification_report.assert_called_once_with(Path(base).resolve(), "run-1")
        format_session_verification_report_text.assert_called_once_with(report)
        get_session_verification_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_run_session_verification_json_uses_local_flag(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "session": "run-1",
                "ok": False,
                "selectedCount": 1,
                "commands": {"shown": 1, "total": 1},
                "results": [{"command": "npm test", "exitCode": 1}],
                "message": "Ran 1/1 session verification command(s); one or more failed.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_session_verification_report", return_value=report) as get_report,
                patch(
                    "vibeagent.cli.format_run_session_verification_report_text",
                    return_value=(
                        "Run session verification:\n"
                        "  session: run-1\n"
                        "  ok: no\n"
                        "  commands: 1/1\n"
                        "  message: failed"
                    ),
                ) as format_text,
                patch("vibeagent.cli.get_run_session_verification_text", return_value="old text path") as get_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--run-session-verification",
                        "run-1",
                        "--session-max-checks",
                        "2",
                        "--run-session-no-pending",
                        "--run-timeout-ms",
                        "1000",
                        "--run-max-chars",
                        "2000",
                        "--run-output-contexts",
                        "--run-output-diagnostics",
                        "--run-output-context-lines",
                        "0",
                        "--run-output-diagnostic-max",
                        "3",
                        "--run-output-context-max",
                        "4",
                        "--run-output-context-max-bytes",
                        "1000",
                        "--json",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["runSessionVerification"], report)
        get_report.assert_called_once_with(
            Path(base).resolve(),
            "run-1",
            max_checks=2,
            timeout_ms=1000,
            max_output_chars=2000,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=0,
            max_diagnostics=3,
            max_contexts=4,
            max_bytes_per_context=1000,
            include_pending=False,
        )
        format_text.assert_called_once_with(report)
        get_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_audit_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_audit_report", return_value={"session": "run-1", "ok": True}) as get_session_audit_report,
                patch("vibeagent.cli.get_session_audit_text", return_value="Session audit:\n  session: run-1") as get_session_audit_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-audit", "run-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session audit:", stdout.getvalue())
        get_session_audit_report.assert_not_called()
        get_session_audit_text.assert_called_once_with(Path(base).resolve(), "run-1")
        create_chat_client.assert_not_called()

    def test_main_runs_session_audit_json_with_structured_payload(self) -> None:
        report = {
            "session": "run-1",
            "exists": True,
            "ok": False,
            "ready": False,
            "status": "blocked",
            "blockers": {"count": 1, "items": ["pending verification check(s)"]},
        }
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_audit_report", return_value=report) as get_session_audit_report,
                patch(
                    "vibeagent.cli.format_session_audit_report_text",
                    return_value="Session audit:\n  session: run-1\n  ready: no",
                ) as format_session_audit_report_text,
                patch("vibeagent.cli.get_session_audit_text", return_value="old text path") as get_session_audit_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--session-audit", "run-1", "--session-max-checks", "3"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["sessionAudit"], report)
        self.assertIn("ready: no", payload["text"])
        get_session_audit_report.assert_called_once_with(Path(base).resolve(), "run-1", max_checks=3)
        format_session_audit_report_text.assert_called_once_with(report)
        get_session_audit_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_handoff_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_handoff_report", return_value={"session": "run-1", "ok": True}) as get_session_handoff_report,
                patch("vibeagent.cli.get_session_handoff_text", return_value="Session handoff:\n  session: run-1") as get_session_handoff_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-handoff", "run-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session handoff:", stdout.getvalue())
        get_session_handoff_report.assert_not_called()
        get_session_handoff_text.assert_called_once_with(Path(base).resolve(), "run-1")
        create_chat_client.assert_not_called()

    def test_main_runs_session_handoff_json_with_structured_payload(self) -> None:
        report = {
            "session": "run-1",
            "exists": True,
            "ok": False,
            "ready": False,
            "status": "blocked",
            "audit": {"blockers": {"count": 1}},
            "sections": {"readiness": "Session readiness:\n  ready: no"},
        }
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_handoff_report", return_value=report) as get_session_handoff_report,
                patch(
                    "vibeagent.cli.format_session_handoff_report_text",
                    return_value="Session handoff:\n  session: run-1\n  readiness:\n    ready: no",
                ) as format_session_handoff_report_text,
                patch("vibeagent.cli.get_session_handoff_text", return_value="old text path") as get_session_handoff_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--session-handoff",
                        "run-1",
                        "--session-max-output-chars",
                        "4000",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionHandoff"], report)
        self.assertIn("ready: no", payload["text"])
        get_session_handoff_report.assert_called_once_with(Path(base).resolve(), "run-1", max_output_chars=4000)
        format_session_handoff_report_text.assert_called_once_with(report)
        get_session_handoff_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_session_detail_local_flags_pass_limit_options(self) -> None:
        cases = [
            (
                [
                    "--session-commands",
                    "run-1",
                    "--session-max-commands",
                    "3",
                    "--session-max-output-chars",
                    "4000",
                ],
                "vibeagent.cli.get_session_commands_text",
                "Command results:\n  session: run-1",
                {"max_commands": 3, "max_output_chars": 4000},
            ),
            (
                ["--session-files", "run-1", "--session-max-files", "7"],
                "vibeagent.cli.get_session_files_text",
                "Session files:\n  session: run-1",
                {"max_files": 7},
            ),
            (
                [
                    "--session-failures",
                    "run-1",
                    "--session-max-failures",
                    "4",
                    "--session-max-text",
                    "120",
                ],
                "vibeagent.cli.get_session_failures_text",
                "Session failures:\n  session: run-1",
                {"max_failures": 4, "max_text": 120},
            ),
            (
                [
                    "--session-audit",
                    "run-1",
                    "--session-max-failures",
                    "4",
                    "--session-max-files",
                    "7",
                    "--session-max-commands",
                    "3",
                    "--session-max-checks",
                    "11",
                    "--session-max-text",
                    "120",
                ],
                "vibeagent.cli.get_session_audit_text",
                "Session audit:\n  session: run-1",
                {"max_failures": 4, "max_files": 7, "max_commands": 3, "max_checks": 11, "max_text": 120},
            ),
            (
                [
                    "--session-handoff",
                    "run-1",
                    "--session-max-failures",
                    "4",
                    "--session-max-files",
                    "7",
                    "--session-max-commands",
                    "3",
                    "--session-max-checks",
                    "11",
                    "--session-max-output-chars",
                    "4000",
                    "--session-max-text",
                    "120",
                ],
                "vibeagent.cli.get_session_handoff_text",
                "Session handoff:\n  session: run-1",
                {
                    "max_failures": 4,
                    "max_files": 7,
                    "max_commands": 3,
                    "max_checks": 11,
                    "max_output_chars": 4000,
                    "max_text": 120,
                },
            ),
        ]

        for argv_tail, patch_target, text, expected_kwargs in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            getter.assert_called_once_with(Path(base).resolve(), "run-1", **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_session_local_flags_exit_nonzero_for_missing_or_invalid_sessions(self) -> None:
        cases = [
            (
                ["--session", "missing"],
                "vibeagent.cli.get_session_text",
                "Session not found: missing",
                ("missing", Path),
            ),
            (
                ["--plan", "missing"],
                "vibeagent.cli.get_plan_text",
                "Session not found: missing",
                (Path, "missing"),
            ),
            (
                ["--session-audit", "../bad"],
                "vibeagent.cli.get_session_audit_text",
                "Invalid session id: ../bad",
                (Path, "../bad"),
            ),
        ]

        for argv_tail, patch_target, text, expected_args in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
            getter.assert_called_once_with(*resolved_args)
            create_chat_client.assert_not_called()

    def test_main_session_plan_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_plan_text", return_value="Session not found: missing"),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--plan", "missing"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Session not found: missing")
        create_chat_client.assert_not_called()

    def test_main_session_summary_local_flags_exit_nonzero_for_unready_status(self) -> None:
        cases = [
            (
                ["--session", "run-1"],
                "vibeagent.cli.get_session_report",
                "Session: run-1\n  status: failed",
                {"session": "run-1", "exists": True, "ok": True, "status": "failed"},
                ("run-1", Path),
            ),
            (
                ["--last"],
                "vibeagent.cli.get_last_session_report",
                "Session: run-1\n  status: blocked",
                {"session": "run-1", "exists": True, "ok": True, "status": "blocked"},
                (Path,),
            ),
        ]

        for argv_tail, patch_target, text, report, expected_args in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_session_summary_report_text", return_value=text) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["success"])
            self.assertEqual(payload["status"], "failed")
            self.assertEqual(payload["text"], text)
            self.assertEqual(payload["sessionSummary"], report)
            resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
            getter.assert_called_once_with(*resolved_args)
            formatter.assert_called_once_with(report)
            create_chat_client.assert_not_called()

    def test_main_latest_session_local_flags_exit_nonzero_when_no_sessions_exist(self) -> None:
        cases = [
            (["--last"], "vibeagent.cli.get_last_session_text", (Path,)),
            (["--plan"], "vibeagent.cli.get_plan_text", (Path, None)),
            (["--session-search", "needle"], "vibeagent.cli.get_session_search_text", (Path, "needle", None)),
        ]

        for argv_tail, patch_target, expected_args in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value="No sessions found.") as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), "No sessions found.\n")
            resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
            getter.assert_called_once_with(*resolved_args)
            create_chat_client.assert_not_called()

    def test_main_sessions_list_exits_nonzero_when_no_sessions_exist(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_sessions_text", return_value="No sessions found.") as get_sessions_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--sessions"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "No sessions found.\n")
        get_sessions_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_local_inspection_flags_exit_nonzero_for_failed_results(self) -> None:
        cases = [
            (
                ["--todos", "../bad"],
                "vibeagent.cli.get_todos_text",
                "Path escapes the project directory: ../bad",
                (Path, "../bad"),
            ),
            (
                ["--repo-map", "../bad"],
                "vibeagent.cli.get_repo_map_text",
                "Repo map:\n  ok: no\n  message: Path escapes the project directory: ../bad",
                (Path, "../bad"),
            ),
            (
                ["--search", "needle", "--search-path", "../bad"],
                "vibeagent.cli.get_search_text",
                "Search:\n  ok: no\n  message: Path escapes the project directory: ../bad",
                (Path, "needle", "../bad"),
            ),
            (
                ["--glob", "../*"],
                "vibeagent.cli.get_glob_text",
                "Glob:\n  ok: no\n  message: Path escapes the project directory: ../*",
                (Path, "../*"),
            ),
            (
                ["--file-info", "../bad"],
                "vibeagent.cli.get_file_info_text",
                "File info:\n  paths: 0/1\n  message: Inspected 0/1 path(s).",
                (Path, ["../bad"]),
            ),
        ]

        for argv_tail, patch_target, text, expected_args in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
            getter.assert_called_once_with(*resolved_args)
            create_chat_client.assert_not_called()

    def test_main_local_inspection_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "pattern": "../*",
                "matches": {"shown": 0, "total": 0, "truncated": False, "files": []},
                "maxMatches": 200,
                "message": "bad pattern",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_glob_report", return_value=report) as get_glob_report,
                patch("vibeagent.cli.format_glob_report_text", return_value="Glob:\n  ok: no\n  message: bad pattern") as format_glob_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--glob", "../*"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Glob:\n  ok: no\n  message: bad pattern")
        self.assertEqual(payload["glob"], report)
        get_glob_report.assert_called_once_with(Path(base).resolve(), "../*")
        format_glob_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_checkpoint_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoint_text", return_value="Checkpoint:\n  created: yes") as get_checkpoint_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoint", "before tests"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoint:", stdout.getvalue())
        get_checkpoint_text.assert_called_once_with(Path(base).resolve(), "before tests")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoints_text", return_value="Checkpoints:\n  total: 1") as get_checkpoints_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoints"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoints:", stdout.getvalue())
        get_checkpoints_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoint_show_text", return_value="Checkpoint:\n  id: ckpt-1") as get_checkpoint_show_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoint-show", "ckpt-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoint:", stdout.getvalue())
        get_checkpoint_show_text.assert_called_once_with("ckpt-1", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoint_diff_text", return_value="Checkpoint diff:\n  id: ckpt-1") as get_checkpoint_diff_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoint-diff", "ckpt-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoint diff:", stdout.getvalue())
        get_checkpoint_diff_text.assert_called_once_with("ckpt-1", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoint_status_text", return_value="Checkpoint status:\n  matches: yes") as get_checkpoint_status_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoint-status", "ckpt-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoint status:", stdout.getvalue())
        get_checkpoint_status_text.assert_called_once_with("ckpt-1", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_checkpoint_restore_text", return_value="Check checkpoint restore:\n  ok: yes") as get_check_checkpoint_restore_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-checkpoint-restore", "ckpt-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check checkpoint restore:", stdout.getvalue())
        get_check_checkpoint_restore_text.assert_called_once_with("ckpt-1", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "canRestore": True,
                "restored": False,
                "matches": True,
                "id": "ckpt-1",
                "savedHead": "abc123",
                "currentHead": "abc123",
                "saved": {"untrackedFiles": 0, "stagedPatchChars": 0, "unstagedPatchChars": 0},
                "current": {"untrackedFiles": 0},
                "message": "Checkpoint can be restored.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_checkpoint_restore_report", return_value=report) as get_check_checkpoint_restore_report,
                patch("vibeagent.cli.format_check_checkpoint_restore_report_text", return_value="Check checkpoint restore:\n  ok: yes") as format_check_checkpoint_restore_report_text,
                patch("vibeagent.cli.get_check_checkpoint_restore_text") as get_check_checkpoint_restore_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--check-checkpoint-restore", "ckpt-1"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["checkCheckpointRestore"], report)
        self.assertEqual(payload["text"], "Check checkpoint restore:\n  ok: yes")
        get_check_checkpoint_restore_report.assert_called_once_with("ckpt-1", Path(base).resolve())
        format_check_checkpoint_restore_report_text.assert_called_once_with(report)
        get_check_checkpoint_restore_text.assert_not_called()
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoint_restore_text", return_value="Checkpoint restore:\n  restored: yes") as get_checkpoint_restore_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoint-restore", "ckpt-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoint restore:", stdout.getvalue())
        get_checkpoint_restore_text.assert_called_once_with("ckpt-1", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_checkpoint_delete_text", return_value="Check checkpoint delete:\n  canDelete: yes") as get_check_checkpoint_delete_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-checkpoint-delete", "ckpt-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check checkpoint delete:", stdout.getvalue())
        get_check_checkpoint_delete_text.assert_called_once_with("ckpt-1", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoint_delete_text", return_value="Checkpoint delete:\n  deleted: yes") as get_checkpoint_delete_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoint-delete", "ckpt-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoint delete:", stdout.getvalue())
        get_checkpoint_delete_text.assert_called_once_with("ckpt-1", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_checkpoint_prune_text", return_value="Check checkpoint prune:\n  deleteCount: 2") as get_check_checkpoint_prune_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-checkpoint-prune", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check checkpoint prune:", stdout.getvalue())
        get_check_checkpoint_prune_text.assert_called_once_with("2", Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checkpoint_prune_text", return_value="Checkpoint prune:\n  deleted: 2") as get_checkpoint_prune_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checkpoint-prune", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checkpoint prune:", stdout.getvalue())
        get_checkpoint_prune_text.assert_called_once_with("2", Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_checkpoint_local_flags_exit_nonzero_for_failed_results(self) -> None:
        cases = [
            (
                ["--checkpoint", "before tests"],
                "vibeagent.cli.get_checkpoint_text",
                "Checkpoint:\n  created: no\n  message: git status failed",
                1,
            ),
            (
                ["--checkpoint-show", "missing"],
                "vibeagent.cli.get_checkpoint_show_text",
                "Checkpoint not found: missing",
                1,
            ),
            (
                ["--checkpoint-status", "ckpt-1"],
                "vibeagent.cli.get_checkpoint_status_text",
                "Checkpoint status:\n  matches: no\n  message: Current worktree differs from checkpoint.",
                1,
            ),
            (
                ["--checkpoint-restore", "ckpt-1"],
                "vibeagent.cli.get_checkpoint_restore_text",
                "Checkpoint restore:\n  restored: no\n  message: Current worktree differs from checkpoint.",
                1,
            ),
            (
                ["--check-checkpoint-delete", "missing"],
                "vibeagent.cli.get_check_checkpoint_delete_text",
                "Check checkpoint delete:\n  canDelete: no\n  message: Checkpoint not found: missing",
                1,
            ),
            (
                ["--check-checkpoint-prune", "-1"],
                "vibeagent.cli.get_check_checkpoint_prune_text",
                "Usage: /check-checkpoint-prune <keep-last>\nError: keep-last must be at least 0.",
                2,
            ),
        ]

        for argv_tail, patch_target, text, expected_exit_code in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text),
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, expected_exit_code)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            create_chat_client.assert_not_called()

    def test_main_checkpoint_delete_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--checkpoint-delete", "missing"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertIn("Checkpoint delete:", payload["text"])
        self.assertIn("Checkpoint not found: missing", payload["text"])
        self.assertFalse(payload["checkpointDelete"]["ok"])
        self.assertFalse(payload["checkpointDelete"]["deleted"])
        self.assertEqual(payload["checkpointDelete"]["id"], "missing")
        create_chat_client.assert_not_called()

    def test_main_checkpoint_json_outputs_structured_payload_without_duplicate_create(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("old\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("new\n", encoding="utf-8")

            create_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(create_stdout),
            ):
                create_exit = main(["--json", "--cwd", base, "--checkpoint", "before json"])

            list_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as list_create_chat_client,
                redirect_stdout(list_stdout),
            ):
                list_exit = main(["--json", "--cwd", base, "--checkpoints"])

        create_payload = json.loads(create_stdout.getvalue())
        list_payload = json.loads(list_stdout.getvalue())
        checkpoint = create_payload["checkpoint"]["checkpoint"]
        checkpoint_id = checkpoint["id"]

        self.assertEqual(create_exit, 0)
        self.assertEqual(create_payload["kind"], "local")
        self.assertTrue(create_payload["success"])
        self.assertTrue(create_payload["checkpoint"]["created"])
        self.assertEqual(checkpoint["label"], "before json")
        self.assertEqual(checkpoint["changedFiles"], 1)
        self.assertEqual(list_exit, 0)
        self.assertEqual(list_payload["checkpoints"]["total"], 1)
        self.assertEqual(list_payload["checkpoints"]["checkpoints"][0]["id"], checkpoint_id)
        create_chat_client.assert_not_called()
        list_create_chat_client.assert_not_called()

    def test_main_checkpoint_restore_and_delete_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("checkpoint\n", encoding="utf-8")

            create_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(create_stdout),
            ):
                create_exit = main(["--json", "--cwd", base, "--checkpoint", "restore json"])
            checkpoint_id = json.loads(create_stdout.getvalue())["checkpoint"]["checkpoint"]["id"]
            (root / "app.py").write_text("broken\n", encoding="utf-8")

            restore_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as restore_create_chat_client,
                redirect_stdout(restore_stdout),
            ):
                restore_exit = main(["--json", "--cwd", base, "--checkpoint-restore", checkpoint_id])

            delete_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as delete_create_chat_client,
                redirect_stdout(delete_stdout),
            ):
                delete_exit = main(["--json", "--cwd", base, "--checkpoint-delete", checkpoint_id])

            final_content = (root / "app.py").read_text(encoding="utf-8")

        restore_payload = json.loads(restore_stdout.getvalue())
        delete_payload = json.loads(delete_stdout.getvalue())

        self.assertEqual(create_exit, 0)
        self.assertEqual(restore_exit, 0)
        self.assertTrue(restore_payload["checkpointRestore"]["restored"])
        self.assertTrue(restore_payload["checkpointRestore"]["matches"])
        self.assertEqual(restore_payload["checkpointRestore"]["id"], checkpoint_id)
        self.assertEqual(final_content, "checkpoint\n")
        self.assertEqual(delete_exit, 0)
        self.assertTrue(delete_payload["checkpointDelete"]["deleted"])
        self.assertEqual(delete_payload["checkpointDelete"]["id"], checkpoint_id)
        create_chat_client.assert_not_called()
        restore_create_chat_client.assert_not_called()
        delete_create_chat_client.assert_not_called()

    def test_main_checkpoint_prune_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "app.py").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            created_ids = []
            for index in range(3):
                (root / "app.py").write_text(f"change {index}\n", encoding="utf-8")
                create_stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(create_stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, "--checkpoint", f"prune {index}"])
                self.assertEqual(exit_code, 0)
                created_ids.append(json.loads(create_stdout.getvalue())["checkpoint"]["checkpoint"]["id"])
                create_chat_client.assert_not_called()
                time.sleep(0.002)

            prune_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as prune_create_chat_client,
                redirect_stdout(prune_stdout),
            ):
                prune_exit = main(["--json", "--cwd", base, "--checkpoint-prune", "1"])

            list_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as list_create_chat_client,
                redirect_stdout(list_stdout),
            ):
                list_exit = main(["--json", "--cwd", base, "--checkpoints"])

        prune_payload = json.loads(prune_stdout.getvalue())
        list_payload = json.loads(list_stdout.getvalue())

        self.assertEqual(prune_exit, 0)
        self.assertEqual(prune_payload["checkpointPrune"]["total"], 3)
        self.assertEqual(prune_payload["checkpointPrune"]["deleted"], 2)
        self.assertEqual([item["id"] for item in prune_payload["checkpointPrune"]["checkpoints"]], [created_ids[1], created_ids[0]])
        self.assertEqual(list_exit, 0)
        self.assertEqual(list_payload["checkpoints"]["total"], 1)
        self.assertEqual(list_payload["checkpoints"]["checkpoints"][0]["id"], created_ids[2])
        prune_create_chat_client.assert_not_called()
        list_create_chat_client.assert_not_called()

    def test_main_runs_tool_local_flag_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--tool", "read_file"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Tool: read_file", stdout.getvalue())
        self.assertIn("input:", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_runs_tool_local_flag_with_json_output(self) -> None:
        stdout = io.StringIO()
        report = {
            "ok": True,
            "found": True,
            "name": "write_file",
            "category": "edit",
            "description": "Write a file after approval.",
            "approvalRequired": True,
            "required": ["path", "content"],
            "properties": [{"name": "path", "type": "string", "required": True}],
            "schema": {"type": "object", "properties": {"path": {"type": "string"}}},
            "message": "Found tool: write_file.",
        }

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tool_report", return_value=report) as get_tool_report,
            patch("vibeagent.cli.format_tool_report_text", return_value="Tool: write_file\n  approvalRequired: yes"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--tool", "write_file"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertIn("Tool: write_file", payload["text"])
        self.assertIn("approvalRequired: yes", payload["text"])
        self.assertEqual(payload["tool"], report)
        get_tool_report.assert_called_once_with("write_file")
        create_chat_client.assert_not_called()

    def test_main_tool_local_flag_exits_nonzero_for_missing_tool(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tool_text", return_value="Tool not found: missing_tool."),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--tool", "missing_tool"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "Tool not found: missing_tool.\n")
        create_chat_client.assert_not_called()

    def test_main_tool_local_flag_reports_json_failure_for_missing_tool(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tool_report", return_value={"ok": False, "found": False, "name": "missing_tool", "suggestions": [], "message": "Tool not found: missing_tool."}),
            patch("vibeagent.cli.format_tool_report_text", return_value="Tool not found: missing_tool."),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--tool", "missing_tool"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Tool not found: missing_tool.")
        self.assertEqual(payload["tool"]["name"], "missing_tool")
        create_chat_client.assert_not_called()

    def test_main_runs_permissions_local_flag_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_permissions_report") as get_permissions_report,
            patch("vibeagent.cli.get_permissions_text", return_value="Permissions:\n  approvalPolicy: deny") as get_permissions_text,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--approval", "deny", "--permissions"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Permissions:", stdout.getvalue())
        get_permissions_report.assert_not_called()
        get_permissions_text.assert_called_once_with("deny", ".")
        create_chat_client.assert_not_called()

    def test_main_runs_permissions_json_with_structured_payload(self) -> None:
        report = {
            "approvalPolicy": "allow",
            "approvalRequiredTools": {"count": 1, "tools": ["write_file"], "byCategory": {"edit": ["write_file"]}},
            "readOnlyTools": {"count": 1, "tools": ["read_file"]},
            "commandHardBlocks": {"active": 1, "total": 1, "checks": [{"command": "code .", "active": True, "reason": "GUI application launch is blocked."}]},
        }
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_permissions_report", return_value=report) as get_permissions_report,
            patch("vibeagent.cli.format_permissions_report_text", return_value="Permissions:\n  approvalPolicy: allow") as format_permissions_report_text,
            patch("vibeagent.cli.get_permissions_text") as get_permissions_text,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--approval", "allow", "--permissions"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["success"])
        self.assertIn("Permissions:", payload["text"])
        permissions = payload["permissions"]
        self.assertEqual(permissions["approvalPolicy"], "allow")
        self.assertIn("write_file", permissions["approvalRequiredTools"]["tools"])
        self.assertIn("read_file", permissions["readOnlyTools"]["tools"])
        self.assertEqual(permissions["commandHardBlocks"]["active"], permissions["commandHardBlocks"]["total"])
        self.assertTrue(any(check["command"] == "code ." and check["active"] for check in permissions["commandHardBlocks"]["checks"]))
        get_permissions_report.assert_called_once_with("allow", ".")
        format_permissions_report_text.assert_called_once_with(report)
        get_permissions_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_checks_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checks_report", return_value={"suggestedChecks": {"shown": 1}}) as get_checks_report,
                patch("vibeagent.cli.get_checks_text", return_value="Checks:\n  suggestedChecks: 1/1") as get_checks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checks"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checks:", stdout.getvalue())
        get_checks_report.assert_not_called()
        get_checks_text.assert_called_once_with(Path(base).resolve(), max_checks=20)
        create_chat_client.assert_not_called()

    def test_main_runs_checks_local_flag_with_max_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checks_report", return_value={"suggestedChecks": {"shown": 1}}) as get_checks_report,
                patch("vibeagent.cli.get_checks_text", return_value="Checks:\n  suggestedChecks: 1/3") as get_checks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checks", "--checks-max", "1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checks:", stdout.getvalue())
        get_checks_report.assert_not_called()
        get_checks_text.assert_called_once_with(Path(base).resolve(), max_checks=1)
        create_chat_client.assert_not_called()

    def test_main_runs_checks_json_with_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            stdout = io.StringIO()
            report = {
                "projectRoot": str(root.resolve()),
                "suggestedChecks": {
                    "shown": 2,
                    "total": 2,
                    "truncated": False,
                    "commands": [
                        {"command": "npm run test"},
                        {"command": "python -m unittest discover -s tests"},
                    ],
                },
                "changedFiles": [],
                "message": "Suggested 2 check(s).",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checks_report", return_value=report) as get_checks_report,
                patch("vibeagent.cli.format_checks_report_text", return_value="Checks:\n  suggestedChecks: 2/2") as format_checks_report_text,
                patch("vibeagent.cli.get_checks_text") as get_checks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--checks", "--checks-max", "10"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["success"])
        self.assertIn("Checks:", payload["text"])
        checks = payload["checks"]
        self.assertEqual(checks["projectRoot"], str(root.resolve()))
        suggested = checks["suggestedChecks"]
        self.assertIsInstance(suggested["commands"], list)
        commands = [item["command"] for item in suggested["commands"] if isinstance(item, dict)]
        self.assertIn("npm run test", commands)
        self.assertIn("python -m unittest discover -s tests", commands)
        get_checks_report.assert_called_once_with(Path(base).resolve(), max_checks=10)
        format_checks_report_text.assert_called_once_with(report)
        get_checks_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_checks_max_without_checks_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--checks-max", "1", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--checks-max can only be used with --checks.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_check_suggested_checks_max_without_check_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--check-suggested-checks-max", "1", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--check-suggested-checks-max can only be used with --check-suggested-checks.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_run_suggested_checks_max_without_run_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--run-suggested-checks-max", "1", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--run-suggested-checks-max can only be used with --run-suggested-checks.\n")
        create_chat_client.assert_not_called()

    def test_main_runs_check_suggested_checks_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_suggested_checks_text", return_value="Check suggested checks:\n  ok: yes") as get_check_suggested_checks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-suggested-checks", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check suggested checks:", stdout.getvalue())
        get_check_suggested_checks_text.assert_called_once_with(Path(base).resolve(), "2", max_checks=10)
        create_chat_client.assert_not_called()

    def test_main_runs_check_suggested_checks_local_flag_with_named_max(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_suggested_checks_text", return_value="Check suggested checks:\n  ok: yes") as get_check_suggested_checks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-suggested-checks", "--check-suggested-checks-max", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check suggested checks:", stdout.getvalue())
        get_check_suggested_checks_text.assert_called_once_with(Path(base).resolve(), None, max_checks=2)
        create_chat_client.assert_not_called()

    def test_main_runs_run_suggested_checks_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_suggested_checks_text", return_value="Run suggested checks:\n  ok: yes") as get_run_suggested_checks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--run-suggested-checks",
                        "2",
                        "--run-timeout-ms",
                        "2000",
                        "--run-max-chars",
                        "3000",
                        "--run-continue-on-failure",
                        "--run-output-contexts",
                        "--run-output-diagnostics",
                        "--run-output-context-lines",
                        "2",
                        "--run-output-diagnostic-max",
                        "7",
                        "--run-output-context-max",
                        "5",
                        "--run-output-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Run suggested checks:", stdout.getvalue())
        get_run_suggested_checks_text.assert_called_once_with(
            Path(base).resolve(),
            "2",
            max_checks=10,
            timeout_ms=2000,
            max_output_chars=3000,
            stop_on_failure=False,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_run_suggested_checks_local_flag_with_named_max(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_suggested_checks_text", return_value="Run suggested checks:\n  ok: yes") as get_run_suggested_checks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--run-suggested-checks", "--run-suggested-checks-max", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Run suggested checks:", stdout.getvalue())
        get_run_suggested_checks_text.assert_called_once_with(
            Path(base).resolve(),
            None,
            max_checks=2,
            timeout_ms=30000,
            max_output_chars=12000,
            stop_on_failure=True,
            extract_output_contexts=False,
            extract_output_diagnostics=False,
            context_lines=5,
            max_diagnostics=50,
            max_contexts=20,
            max_bytes_per_context=20000,
        )
        create_chat_client.assert_not_called()

    def test_main_suggested_checks_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base).resolve()
            cases = [
                (
                    ["--check-suggested-checks", "2"],
                    "vibeagent.cli.get_check_suggested_checks_report",
                    "vibeagent.cli.format_check_suggested_checks_report_text",
                    "checkSuggestedChecks",
                    "Check suggested checks:\n  ok: yes",
                    {"argument": "2", "max_checks": 10},
                ),
                (
                    [
                        "--run-suggested-checks",
                        "2",
                        "--run-timeout-ms",
                        "2000",
                        "--run-max-chars",
                        "3000",
                        "--run-continue-on-failure",
                        "--run-output-contexts",
                        "--run-output-diagnostics",
                    ],
                    "vibeagent.cli.get_run_suggested_checks_report",
                    "vibeagent.cli.format_run_suggested_checks_report_text",
                    "runSuggestedChecks",
                    "Run suggested checks:\n  ok: yes",
                    {
                        "argument": "2",
                        "max_checks": 10,
                        "timeout_ms": 2000,
                        "max_output_chars": 3000,
                        "stop_on_failure": False,
                        "extract_output_contexts": True,
                        "extract_output_diagnostics": True,
                        "context_lines": 5,
                        "max_diagnostics": 50,
                        "max_contexts": 20,
                        "max_bytes_per_context": 20000,
                    },
                ),
            ]

            for argv_tail, report_target, format_target, payload_key, text, expected_kwargs in cases:
                with self.subTest(payload_key=payload_key):
                    stdout = io.StringIO()
                    report = {"projectRoot": str(root), "ok": True, "message": "ok"}
                    with (
                        patch("vibeagent.cli.create_chat_client") as create_chat_client,
                        patch(report_target, return_value=report) as get_report,
                        patch(format_target, return_value=text) as format_report,
                        redirect_stdout(stdout),
                    ):
                        exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], text)
                get_report.assert_called_once_with(root, **expected_kwargs)
                format_report.assert_called_once_with(report)
                create_chat_client.assert_not_called()

    def test_main_runs_commands_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_commands_text", return_value="Project commands:\n  commands: 1/1") as get_commands_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--commands"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Project commands:", stdout.getvalue())
        get_commands_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_commands_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_commands_text", return_value="Project commands:\n  commands: 1/2") as get_commands_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--commands", "--commands-max-commands", "2", "--commands-max-files", "3"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Project commands:", stdout.getvalue())
        get_commands_text.assert_called_once_with(Path(base).resolve(), max_commands=2, max_files=3)
        create_chat_client.assert_not_called()

    def test_main_rejects_commands_bounds_without_commands_local_flag(self) -> None:
        cases = [
            (["--commands-max-commands", "2"], "--commands-max-commands can only be used with --commands."),
            (["--commands-max-files", "3"], "--commands-max-files can only be used with --commands."),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with redirect_stdout(stdout):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertIn(expected, stdout.getvalue())

    def test_main_runs_related_tests_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_related_tests_text", return_value="Related tests:\n  candidates: 1/1") as get_related_tests_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--related-tests", "pkg/actions.py", "tests/test_actions.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Related tests:", stdout.getvalue())
        get_related_tests_text.assert_called_once_with(Path(base).resolve(), "pkg/actions.py tests/test_actions.py")
        create_chat_client.assert_not_called()

    def test_main_runs_related_tests_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_related_tests_text", return_value="Related tests:\n  candidates: 1/2") as get_related_tests_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--related-tests", "pkg/actions.py", "--related-tests-max-paths", "3", "--related-tests-max-candidates", "4"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Related tests:", stdout.getvalue())
        get_related_tests_text.assert_called_once_with(Path(base).resolve(), "pkg/actions.py", max_paths=3, max_candidates=4)
        create_chat_client.assert_not_called()

    def test_main_rejects_related_tests_bounds_without_related_tests_local_flag(self) -> None:
        cases = [
            (["--related-tests-max-paths", "3"], "--related-tests-max-paths can only be used with --related-tests."),
            (["--related-tests-max-candidates", "4"], "--related-tests-max-candidates can only be used with --related-tests."),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with redirect_stdout(stdout):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertIn(expected, stdout.getvalue())

    def test_main_project_discovery_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base).resolve()
            cases = [
                (
                    ["--commands", "--commands-max-commands", "2", "--commands-max-files", "3"],
                    "vibeagent.cli.get_commands_report",
                    "vibeagent.cli.format_commands_report_text",
                    "projectCommands",
                    "Project commands:\n  commands: 1/1",
                    {"max_commands": 2, "max_files": 3},
                ),
                (
                    ["--related-tests", "pkg/actions.py", "--related-tests-max-paths", "4", "--related-tests-max-candidates", "5"],
                    "vibeagent.cli.get_related_tests_report",
                    "vibeagent.cli.format_related_tests_report_text",
                    "relatedTests",
                    "Related tests:\n  candidates: 1/1",
                    {"argument": "pkg/actions.py", "max_paths": 4, "max_candidates": 5},
                ),
            ]

            for argv_tail, report_target, format_target, payload_key, text, expected_kwargs in cases:
                with self.subTest(payload_key=payload_key):
                    stdout = io.StringIO()
                    report = {"projectRoot": str(root), "ok": True, "message": "ok"}
                    with (
                        patch("vibeagent.cli.create_chat_client") as create_chat_client,
                        patch(report_target, return_value=report) as get_report,
                        patch(format_target, return_value=text) as format_report,
                        redirect_stdout(stdout),
                    ):
                        exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], text)
                get_report.assert_called_once_with(root, **expected_kwargs)
                format_report.assert_called_once_with(report)
                create_chat_client.assert_not_called()

    def test_main_runs_focused_tests_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_focused_test_commands_text", return_value="Focused test commands:\n  commands: 1/1") as get_focused_test_commands_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--focused-tests", "pkg/actions.py", "tests/test_actions.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Focused test commands:", stdout.getvalue())
        get_focused_test_commands_text.assert_called_once_with(Path(base).resolve(), "pkg/actions.py tests/test_actions.py")
        create_chat_client.assert_not_called()

    def test_main_runs_focused_tests_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_focused_test_commands_text", return_value="Focused test commands:\n  commands: 1/2") as get_focused_test_commands_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--focused-tests",
                        "pkg/actions.py",
                        "--focused-tests-max-paths",
                        "3",
                        "--focused-tests-max-candidates",
                        "4",
                        "--focused-tests-max-commands",
                        "5",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Focused test commands:", stdout.getvalue())
        get_focused_test_commands_text.assert_called_once_with(Path(base).resolve(), "pkg/actions.py", max_paths=3, max_candidates=4, max_commands=5)
        create_chat_client.assert_not_called()

    def test_main_runs_check_focused_tests_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_focused_test_commands_text", return_value="Check focused test commands:\n  ok: yes") as get_check_focused_test_commands_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-focused-tests", "pkg/actions.py", "tests/test_actions.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check focused test commands:", stdout.getvalue())
        get_check_focused_test_commands_text.assert_called_once_with(Path(base).resolve(), "pkg/actions.py tests/test_actions.py")
        create_chat_client.assert_not_called()

    def test_main_rejects_focused_tests_bounds_without_focused_tests_local_flag(self) -> None:
        cases = [
            (["--focused-tests-max-paths", "3"], "--focused-tests-max-paths can only be used with --focused-tests, --check-focused-tests, or --run-focused-tests."),
            (["--focused-tests-max-candidates", "4"], "--focused-tests-max-candidates can only be used with --focused-tests, --check-focused-tests, or --run-focused-tests."),
            (["--focused-tests-max-commands", "5"], "--focused-tests-max-commands can only be used with --focused-tests, --check-focused-tests, or --run-focused-tests."),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with redirect_stdout(stdout):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertIn(expected, stdout.getvalue())

    def test_main_runs_run_focused_tests_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_focused_test_commands_text", return_value="Run focused test commands:\n  ok: yes") as get_run_focused_test_commands_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--run-focused-tests",
                        "pkg/actions.py",
                        "tests/test_actions.py",
                        "--run-timeout-ms",
                        "2000",
                        "--run-max-chars",
                        "3000",
                        "--run-continue-on-failure",
                        "--run-output-contexts",
                        "--run-output-diagnostics",
                        "--run-output-context-lines",
                        "2",
                        "--run-output-diagnostic-max",
                        "7",
                        "--run-output-context-max",
                        "5",
                        "--run-output-context-max-bytes",
                        "1000",
                        "--focused-tests-max-paths",
                        "3",
                        "--focused-tests-max-candidates",
                        "4",
                        "--focused-tests-max-commands",
                        "5",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Run focused test commands:", stdout.getvalue())
        get_run_focused_test_commands_text.assert_called_once_with(
            Path(base).resolve(),
            "pkg/actions.py tests/test_actions.py",
            max_paths=3,
            max_candidates=4,
            max_commands=5,
            timeout_ms=2000,
            max_output_chars=3000,
            stop_on_failure=False,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_focused_tests_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base).resolve()
            cases = [
                (
                    ["--focused-tests", "pkg/actions.py", "--focused-tests-max-paths", "3", "--focused-tests-max-candidates", "4", "--focused-tests-max-commands", "5"],
                    "vibeagent.cli.get_focused_test_commands_report",
                    "vibeagent.cli.format_focused_test_commands_report_text",
                    "focusedTests",
                    "Focused test commands:\n  commands: 1/1",
                    {"argument": "pkg/actions.py", "max_paths": 3, "max_candidates": 4, "max_commands": 5},
                ),
                (
                    ["--check-focused-tests", "pkg/actions.py"],
                    "vibeagent.cli.get_check_focused_test_commands_report",
                    "vibeagent.cli.format_check_focused_test_commands_report_text",
                    "checkFocusedTests",
                    "Check focused test commands:\n  ok: yes",
                    {"argument": "pkg/actions.py"},
                ),
                (
                    [
                        "--run-focused-tests",
                        "pkg/actions.py",
                        "--run-timeout-ms",
                        "2000",
                        "--run-max-chars",
                        "3000",
                        "--run-continue-on-failure",
                        "--run-output-contexts",
                    ],
                    "vibeagent.cli.get_run_focused_test_commands_report",
                    "vibeagent.cli.format_run_focused_test_commands_report_text",
                    "runFocusedTests",
                    "Run focused test commands:\n  ok: yes",
                    {
                        "argument": "pkg/actions.py",
                        "timeout_ms": 2000,
                        "max_output_chars": 3000,
                        "stop_on_failure": False,
                        "extract_output_contexts": True,
                        "extract_output_diagnostics": False,
                        "context_lines": 5,
                        "max_diagnostics": 50,
                        "max_contexts": 20,
                        "max_bytes_per_context": 20000,
                    },
                ),
            ]

            for argv_tail, report_target, format_target, payload_key, text, expected_kwargs in cases:
                with self.subTest(payload_key=payload_key):
                    stdout = io.StringIO()
                    report = {"projectRoot": str(root), "ok": True, "message": "ok"}
                    with (
                        patch("vibeagent.cli.create_chat_client") as create_chat_client,
                        patch(report_target, return_value=report) as get_report,
                        patch(format_target, return_value=text) as format_report,
                        redirect_stdout(stdout),
                    ):
                        exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], text)
                get_report.assert_called_once_with(root, **expected_kwargs)
                format_report.assert_called_once_with(report)
                create_chat_client.assert_not_called()

    def test_main_runs_manifests_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_manifests_text", return_value="Manifests:\n  files: 1/1") as get_manifests_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--manifests"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Manifests:", stdout.getvalue())
        get_manifests_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_manifests_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_manifests_text", return_value="Manifests:\n  files: 1/2") as get_manifests_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--manifests", "--manifests-max-files", "2", "--manifests-max-items", "10"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Manifests:", stdout.getvalue())
        get_manifests_text.assert_called_once_with(Path(base).resolve(), max_files=2, max_items=10)
        create_chat_client.assert_not_called()

    def test_main_rejects_manifests_bounds_without_manifests_local_flag(self) -> None:
        cases = [
            (["--manifests-max-files", "2"], "--manifests-max-files can only be used with --manifests."),
            (["--manifests-max-items", "10"], "--manifests-max-items can only be used with --manifests."),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with redirect_stdout(stdout):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertIn(expected, stdout.getvalue())

    def test_main_runs_instructions_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_instructions_text", return_value="Project instructions:\n  files: 1/1") as get_instructions_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--instructions"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Project instructions:", stdout.getvalue())
        get_instructions_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_instructions_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_instructions_text", return_value="Project instructions:\n  files: 1/2") as get_instructions_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--instructions", "--instructions-max-files", "2", "--instructions-max-bytes", "1000"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Project instructions:", stdout.getvalue())
        get_instructions_text.assert_called_once_with(Path(base).resolve(), max_files=2, max_bytes=1000)
        create_chat_client.assert_not_called()

    def test_main_rejects_instructions_bounds_without_instructions_local_flag(self) -> None:
        cases = [
            (["--instructions-max-files", "2"], "--instructions-max-files can only be used with --instructions."),
            (["--instructions-max-bytes", "1000"], "--instructions-max-bytes can only be used with --instructions."),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with redirect_stdout(stdout):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertIn(expected, stdout.getvalue())

    def test_main_runs_todos_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_todos_text", return_value="Project TODOs:\n  todos: 1/1") as get_todos_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--todos", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Project TODOs:", stdout.getvalue())
        get_todos_text.assert_called_once_with(Path(base).resolve(), "src")
        create_chat_client.assert_not_called()

    def test_main_runs_todos_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_todos_text", return_value="Project TODOs:\n  todos: 1/3") as get_todos_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--todos", "src", "--todos-max-items", "3", "--todos-max-files", "20"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Project TODOs:", stdout.getvalue())
        get_todos_text.assert_called_once_with(Path(base).resolve(), "src", max_items=3, max_files=20)
        create_chat_client.assert_not_called()

    def test_main_rejects_todos_bounds_without_todos_local_flag(self) -> None:
        cases = [
            (["--todos-max-items", "3"], "--todos-max-items can only be used with --todos."),
            (["--todos-max-files", "20"], "--todos-max-files can only be used with --todos."),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), f"{expected}\n")
                create_chat_client.assert_not_called()

    def test_main_project_metadata_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base).resolve()
            cases = [
                (
                    ["--manifests", "--manifests-max-files", "2", "--manifests-max-items", "10"],
                    "vibeagent.cli.get_manifests_report",
                    "vibeagent.cli.format_manifests_report_text",
                    "manifests",
                    "Manifests:\n  files: 1/1",
                    {"max_files": 2, "max_items": 10},
                ),
                (
                    ["--instructions", "--instructions-max-files", "2", "--instructions-max-bytes", "1000"],
                    "vibeagent.cli.get_instructions_report",
                    "vibeagent.cli.format_instructions_report_text",
                    "instructions",
                    "Project instructions:\n  files: 1/1",
                    {"max_files": 2, "max_bytes": 1000},
                ),
                (
                    ["--todos", "src", "--todos-max-items", "3", "--todos-max-files", "20"],
                    "vibeagent.cli.get_todos_report",
                    "vibeagent.cli.format_todos_report_text",
                    "todos",
                    "Project TODOs:\n  todos: 1/1",
                    {"path": "src", "max_items": 3, "max_files": 20},
                ),
            ]

            for argv_tail, report_target, format_target, payload_key, text, expected_kwargs in cases:
                with self.subTest(payload_key=payload_key):
                    stdout = io.StringIO()
                    report = {"projectRoot": str(root), "ok": True, "message": "ok"}
                    with (
                        patch("vibeagent.cli.create_chat_client") as create_chat_client,
                        patch(report_target, return_value=report) as get_report,
                        patch(format_target, return_value=text) as format_report,
                        redirect_stdout(stdout),
                    ):
                        exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], text)
                get_report.assert_called_once_with(root, **expected_kwargs)
                format_report.assert_called_once_with(report)
                create_chat_client.assert_not_called()

    def test_main_runs_command_check_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_command_check_text", return_value="Command check:\n  ok: yes") as get_command_check_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--command-check", "python3 --version", "--command-cwd", "."])

        self.assertEqual(exit_code, 0)
        self.assertIn("Command check:", stdout.getvalue())
        get_command_check_text.assert_called_once_with(Path(base).resolve(), "python3 --version", ".")
        create_chat_client.assert_not_called()

    def test_main_runs_command_alias_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_command_check_text", return_value="Command check:\n  ok: yes") as get_command_check_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--command", "python3 --version", "--command-cwd", "."])

        self.assertEqual(exit_code, 0)
        self.assertIn("Command check:", stdout.getvalue())
        get_command_check_text.assert_called_once_with(Path(base).resolve(), "python3 --version", ".")
        create_chat_client.assert_not_called()

    def test_main_command_check_local_flag_exits_nonzero_when_not_ok(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch(
                    "vibeagent.cli.get_command_check_text",
                    return_value="Command check:\n  ok: no\n  message: blocked",
                ),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--command-check", "sudo reboot"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Command check:", stdout.getvalue())
        self.assertIn("ok: no", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_command_check_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "command": "sudo reboot",
                "cwd": ".",
                "ok": False,
                "cwdOk": True,
                "blocked": True,
                "executableAvailable": True,
                "blockReason": "high-risk command requires an explicit user-controlled approval flow",
                "missingTool": None,
                "message": "Command blocked.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_command_check_report", return_value=report) as get_command_check_report,
                patch("vibeagent.cli.format_command_check_report_text", return_value="Command check:\n  ok: no\n  blocked: yes") as format_command_check_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--command-check", "sudo reboot", "--command-cwd", "."])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["commandCheck"], report)
        get_command_check_report.assert_called_once_with(Path(base).resolve(), "sudo reboot", ".")
        format_command_check_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_run_command_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_text", return_value="Run:\n  ok: yes") as get_run_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--run-command",
                        "python3 --version",
                        "--run-cwd",
                        ".",
                        "--run-timeout-ms",
                        "2000",
                        "--run-max-chars",
                        "3000",
                        "--run-output-contexts",
                        "--run-output-diagnostics",
                        "--run-output-context-lines",
                        "2",
                        "--run-output-diagnostic-max",
                        "7",
                        "--run-output-context-max",
                        "5",
                        "--run-output-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Run:", stdout.getvalue())
        get_run_text.assert_called_once_with(
            Path(base).resolve(),
            command="python3 --version",
            cwd=".",
            timeout_ms=2000,
            max_output_chars=3000,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_run_alias_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_text", return_value="Run:\n  ok: yes") as get_run_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--run", "python3 --version", "--run-cwd", "."])

        self.assertEqual(exit_code, 0)
        self.assertIn("Run:", stdout.getvalue())
        get_run_text.assert_called_once_with(
            Path(base).resolve(),
            command="python3 --version",
            cwd=".",
            timeout_ms=30000,
            max_output_chars=12000,
            extract_output_contexts=False,
            extract_output_diagnostics=False,
            context_lines=5,
            max_diagnostics=50,
            max_contexts=20,
            max_bytes_per_context=20000,
        )
        create_chat_client.assert_not_called()

    def test_main_run_command_local_flag_exits_nonzero_when_command_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_text", return_value="Run:\n  ok: no\n  exitCode: 7") as get_run_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--run-command", "false"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Run:", stdout.getvalue())
        self.assertIn("ok: no", stdout.getvalue())
        get_run_text.assert_called_once()
        create_chat_client.assert_not_called()

    def test_main_run_command_allows_diagnostic_max_for_auto_failure_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_text", return_value="Run:\n  ok: no\n  outputDiagnostics: 1/2") as get_run_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--run-command",
                        "false",
                        "--run-output-context-lines",
                        "0",
                        "--run-output-context-max",
                        "1",
                        "--run-output-context-max-bytes",
                        "1000",
                        "--run-output-diagnostic-max",
                        "1",
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertIn("outputDiagnostics: 1/2", stdout.getvalue())
        get_run_text.assert_called_once_with(
            Path(base).resolve(),
            command="false",
            cwd=None,
            timeout_ms=30000,
            max_output_chars=12000,
            extract_output_contexts=False,
            extract_output_diagnostics=False,
            context_lines=0,
            max_diagnostics=1,
            max_contexts=1,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_run_command_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "command": "false",
                "cwd": ".",
                "exitCode": 7,
                "timedOut": False,
                "signal": None,
                "timeoutMs": 30000,
                "maxOutputChars": 12000,
                "stdout": "",
                "stderr": "failure\n",
                "stdoutTruncated": False,
                "stderrTruncated": False,
                "analysis": {"diagnostics": {"shown": 0, "total": 0, "items": []}, "diagnosticsTruncated": False, "contexts": {"shown": 0, "totalRefs": 0, "items": []}, "contextsTruncated": False},
                "message": "Command failed.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_report", return_value=report) as get_run_report,
                patch("vibeagent.cli.format_run_report_text", return_value="Run:\n  ok: no\n  exitCode: 7") as format_run_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--run-command", "false"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["run"], report)
        self.assertIn("ok: no", payload["text"])
        get_run_report.assert_called_once_with(
            Path(base).resolve(),
            command="false",
            cwd=None,
            timeout_ms=30000,
            max_output_chars=12000,
            extract_output_contexts=False,
            extract_output_diagnostics=False,
            context_lines=5,
            max_diagnostics=50,
            max_contexts=20,
            max_bytes_per_context=20000,
        )
        format_run_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_run_commands_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_sequence_text", return_value="Run sequence:\n  ok: yes") as get_run_sequence_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--run-commands",
                        "python3 --version",
                        "npm test",
                        "--run-cwd",
                        ".",
                        "--run-timeout-ms",
                        "2000",
                        "--run-max-chars",
                        "3000",
                        "--run-continue-on-failure",
                        "--run-output-contexts",
                        "--run-output-context-lines",
                        "2",
                        "--run-output-context-max",
                        "5",
                        "--run-output-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Run sequence:", stdout.getvalue())
        get_run_sequence_text.assert_called_once_with(
            Path(base).resolve(),
            commands=["python3 --version", "npm test"],
            cwd=".",
            timeout_ms=2000,
            max_output_chars=3000,
            stop_on_failure=False,
            extract_output_contexts=True,
            extract_output_diagnostics=False,
            context_lines=2,
            max_diagnostics=50,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_run_commands_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "commands": {"shown": 1, "total": 2, "requested": ["false", "python3 --version"]},
                "stopOnFailure": True,
                "stoppedEarly": True,
                "results": [
                    {
                        "index": 1,
                        "command": "false",
                        "cwd": ".",
                        "ok": False,
                        "exitCode": 1,
                        "timedOut": False,
                        "signal": None,
                        "timeoutMs": 30000,
                        "maxOutputChars": 12000,
                        "stdout": "",
                        "stderr": "",
                        "stdoutTruncated": False,
                        "stderrTruncated": False,
                        "analysis": {"diagnostics": {"shown": 0, "total": 0, "items": []}, "diagnosticsTruncated": False, "contexts": {"shown": 0, "totalRefs": 0, "items": []}, "contextsTruncated": False},
                    }
                ],
                "message": "Command 1 failed; stopped early.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_sequence_report", return_value=report) as get_run_sequence_report,
                patch("vibeagent.cli.format_run_sequence_report_text", return_value="Run sequence:\n  ok: no\n  stoppedEarly: yes") as format_run_sequence_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--run-commands", "false", "python3 --version"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["runCommands"], report)
        get_run_sequence_report.assert_called_once_with(
            Path(base).resolve(),
            commands=["false", "python3 --version"],
            cwd=None,
            timeout_ms=30000,
            max_output_chars=12000,
            stop_on_failure=True,
            extract_output_contexts=False,
            extract_output_diagnostics=False,
            context_lines=5,
            max_diagnostics=50,
            max_contexts=20,
            max_bytes_per_context=20000,
        )
        format_run_sequence_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_run_commands_local_flag_exits_nonzero_when_sequence_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_sequence_text", return_value="Run sequence:\n  ok: no\n  stoppedEarly: yes"),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--run-commands", "python3 --version", "false"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Run sequence:", stdout.getvalue())
        self.assertIn("ok: no", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_runs_check_run_commands_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_run_sequence_text", return_value="Check run sequence:\n  ok: yes") as get_check_run_sequence_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-run-commands", "python3 --version", "npm test", "--run-cwd", "."])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check run sequence:", stdout.getvalue())
        get_check_run_sequence_text.assert_called_once_with(
            Path(base).resolve(),
            commands=["python3 --version", "npm test"],
            cwd=".",
        )
        create_chat_client.assert_not_called()

    def test_main_check_run_commands_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "commands": {"shown": 2, "total": 2, "requested": ["python3 --version", "sudo reboot"]},
                "checks": [
                    {
                        "index": 1,
                        "command": "python3 --version",
                        "cwd": ".",
                        "ok": True,
                        "cwdOk": True,
                        "blocked": False,
                        "executableAvailable": True,
                        "blockReason": None,
                        "missingTool": None,
                        "message": "Command looks runnable.",
                    },
                    {
                        "index": 2,
                        "command": "sudo reboot",
                        "cwd": ".",
                        "ok": False,
                        "cwdOk": True,
                        "blocked": True,
                        "executableAvailable": True,
                        "blockReason": "high-risk command requires an explicit user-controlled approval flow",
                        "missingTool": None,
                        "message": "Command blocked.",
                    },
                ],
                "message": "One or more commands need attention.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_run_sequence_report", return_value=report) as get_check_run_sequence_report,
                patch("vibeagent.cli.format_check_run_sequence_report_text", return_value="Check run sequence:\n  ok: no") as format_check_run_sequence_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--check-run-commands", "python3 --version", "sudo reboot", "--run-cwd", "."])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["checkRunCommands"], report)
        get_check_run_sequence_report.assert_called_once_with(
            Path(base).resolve(),
            commands=["python3 --version", "sudo reboot"],
            cwd=".",
        )
        format_check_run_sequence_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_start_command_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_start_text", return_value="Check start:\n  ok: yes") as get_check_start_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-start-command", "npm run dev", "--start-cwd", "."])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check start:", stdout.getvalue())
        get_check_start_text.assert_called_once_with(Path(base).resolve(), "npm run dev", cwd=".")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "command": "sudo reboot",
                "cwd": ".",
                "cwdOk": True,
                "blocked": True,
                "executableAvailable": True,
                "blockReason": "high-risk command requires an explicit user-controlled approval flow",
                "missingTool": None,
                "message": "Command blocked.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_start_report", return_value=report) as get_check_start_report,
                patch("vibeagent.cli.format_check_start_report_text", return_value="Check start:\n  ok: no") as format_check_start_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--check-start-command", "sudo reboot", "--start-cwd", "."])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["checkStartCommand"], report)
        get_check_start_report.assert_called_once_with(Path(base).resolve(), "sudo reboot", cwd=".")
        format_check_start_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_start_text", return_value="Start:\n  ok: yes") as get_start_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--start-command", "npm run dev", "--start-cwd", "."])

        self.assertEqual(exit_code, 0)
        self.assertIn("Start:", stdout.getvalue())
        get_start_text.assert_called_once_with(Path(base).resolve(), "npm run dev", cwd=".")
        create_chat_client.assert_not_called()

    def test_main_runs_start_alias_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_start_text", return_value="Start:\n  ok: yes") as get_start_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--start", "npm run dev", "--start-cwd", "."])

        self.assertEqual(exit_code, 0)
        self.assertIn("Start:", stdout.getvalue())
        get_start_text.assert_called_once_with(Path(base).resolve(), "npm run dev", cwd=".")
        create_chat_client.assert_not_called()

    def test_main_start_command_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "command": "npm run dev",
                "cwd": ".",
                "processId": "bg-1",
                "pid": 1234,
                "stdoutPath": ".vibeagent/sessions/local-start/processes/bg-1.stdout.log",
                "stderrPath": ".vibeagent/sessions/local-start/processes/bg-1.stderr.log",
                "message": "Started process bg-1.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_start_report", return_value=report) as get_start_report,
                patch("vibeagent.cli.format_start_report_text", return_value="Start:\n  ok: yes\n  processId: bg-1") as format_start_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--start-command", "npm run dev", "--start-cwd", "."])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["startCommand"], report)
        get_start_report.assert_called_once_with(Path(base).resolve(), "npm run dev", cwd=".")
        format_start_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_port_check_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_port_text", return_value="Port:\n  ok: yes") as get_port_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--port-check", "5173", "--port-host", "127.0.0.1", "--port-timeout-ms", "1500"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Port:", stdout.getvalue())
        get_port_text.assert_called_once_with(Path(base).resolve(), port=5173, host="127.0.0.1", timeout_ms=1500)
        create_chat_client.assert_not_called()

    def test_main_port_check_local_flag_exits_nonzero_when_not_ok(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_port_text", return_value="Port:\n  ok: yes\n  reachable: no"),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--port-check", "5173"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Port:", stdout.getvalue())
        self.assertIn("reachable: no", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_port_check_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "host": "127.0.0.1",
                "port": 5173,
                "reachable": True,
                "timeoutMs": 1500,
                "error": None,
                "message": "Port is reachable.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_port_report", return_value=report) as get_port_report,
                patch("vibeagent.cli.format_port_report_text", return_value="Port:\n  ok: yes\n  reachable: yes") as format_port_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--port-check", "5173", "--port-host", "127.0.0.1", "--port-timeout-ms", "1500"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["port"], report)
        get_port_report.assert_called_once_with(Path(base).resolve(), port=5173, host="127.0.0.1", timeout_ms=1500)
        format_port_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_http_check_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_http_text", return_value="HTTP:\n  ok: yes") as get_http_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--http-check",
                        "http://127.0.0.1:5173",
                        "--http-contains",
                        "ready",
                        "--http-timeout-ms",
                        "1500",
                        "--http-max-body-chars",
                        "1000",
                        "--http-regex",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("HTTP:", stdout.getvalue())
        get_http_text.assert_called_once_with(
            Path(base).resolve(),
            url="http://127.0.0.1:5173",
            contains="ready",
            timeout_ms=1500,
            max_body_chars=1000,
            regex=True,
        )
        create_chat_client.assert_not_called()

    def test_main_http_check_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "url": "http://127.0.0.1:5173",
                "finalUrl": "http://127.0.0.1:5173/",
                "status": 200,
                "reason": "OK",
                "reachable": True,
                "matched": False,
                "matchedPattern": "ready",
                "timeoutMs": 2000,
                "maxBodyChars": 2000,
                "body": "not ready\n",
                "bodyTruncated": False,
                "error": None,
                "message": "HTTP URL is reachable but did not match.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_http_report", return_value=report) as get_http_report,
                patch("vibeagent.cli.format_http_report_text", return_value="HTTP:\n  ok: no\n  reachable: yes\n  matched: no") as format_http_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--http-check",
                        "http://127.0.0.1:5173",
                        "--http-contains",
                        "ready",
                    ]
                )

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertIn("matched: no", payload["text"])
        self.assertEqual(payload["http"], report)
        get_http_report.assert_called_once_with(
            Path(base).resolve(),
            url="http://127.0.0.1:5173",
            contains="ready",
            timeout_ms=2000,
            max_body_chars=2000,
            regex=False,
        )
        format_http_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_http_fetch_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_http_fetch_text", return_value="HTTP fetch:\n  ok: yes") as get_http_fetch_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--http-fetch",
                        "http://127.0.0.1:5173/app",
                        "--http-timeout-ms",
                        "2500",
                        "--http-max-body-chars",
                        "4000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("HTTP fetch:", stdout.getvalue())
        get_http_fetch_text.assert_called_once_with(
            Path(base).resolve(),
            url="http://127.0.0.1:5173/app",
            timeout_ms=2500,
            max_body_chars=4000,
        )
        create_chat_client.assert_not_called()

    def test_main_http_fetch_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "url": "http://127.0.0.1:5173/app",
                "finalUrl": "http://127.0.0.1:5173/app",
                "status": 200,
                "reason": "OK",
                "contentType": "text/html; charset=utf-8",
                "reachable": True,
                "timeoutMs": 2500,
                "maxBodyChars": 4000,
                "body": "<main>ready</main>\n",
                "bodyTruncated": False,
                "error": None,
                "message": "HTTP URL was fetched.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_http_fetch_report", return_value=report) as get_http_fetch_report,
                patch("vibeagent.cli.format_http_fetch_report_text", return_value="HTTP fetch:\n  ok: yes") as format_http_fetch_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--http-fetch",
                        "http://127.0.0.1:5173/app",
                        "--http-timeout-ms",
                        "2500",
                        "--http-max-body-chars",
                        "4000",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["httpFetch"], report)
        get_http_fetch_report.assert_called_once_with(
            Path(base).resolve(),
            url="http://127.0.0.1:5173/app",
            timeout_ms=2500,
            max_body_chars=4000,
        )
        format_http_fetch_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_reports_command_cwd_without_command_check_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--command-cwd", "src", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--command-cwd can only be used with --command-check or --command.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_start_cwd_without_start_command_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--start-cwd", "src", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--start-cwd can only be used with --check-start-command, --start-command, or --start.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_run_options_without_run_command_as_local_flag_error(self) -> None:
        cases = [
            (["--run-cwd", "src", "fix"], "--run-cwd can only be used with --run-command, --run, --run-commands, or --check-run-commands.\n"),
            (["--run-timeout-ms", "2000", "fix"], "--run-timeout-ms can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-max-chars", "2000", "fix"], "--run-max-chars can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-continue-on-failure", "fix"], "--run-continue-on-failure can only be used with --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-contexts", "fix"], "--run-output-contexts can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-diagnostics", "fix"], "--run-output-diagnostics can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-context-lines", "2", "fix"], "--run-output-context-lines can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-context-max", "5", "fix"], "--run-output-context-max can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-context-max-bytes", "1000", "fix"], "--run-output-context-max-bytes can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-diagnostic-max", "5", "fix"], "--run-output-diagnostic-max can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_port_and_http_options_without_matching_local_flag(self) -> None:
        cases = [
            (["--port-host", "0.0.0.0", "fix"], "--port-host can only be used with --port-check.\n"),
            (["--port-timeout-ms", "1500", "fix"], "--port-timeout-ms can only be used with --port-check.\n"),
            (["--http-timeout-ms", "1500", "fix"], "--http-timeout-ms can only be used with --http-check or --http-fetch.\n"),
            (["--http-max-body-chars", "1000", "fix"], "--http-max-body-chars can only be used with --http-check or --http-fetch.\n"),
            (["--http-contains", "ready", "fix"], "--http-contains can only be used with --http-check.\n"),
            (["--http-regex", "fix"], "--http-regex can only be used with --http-check.\n"),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_runs_overview_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_overview_text", return_value="Overview:\n  files: 1/1") as get_overview_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--overview"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Overview:", stdout.getvalue())
        get_overview_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_overview_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_overview_text", return_value="Overview:\n  files: 1/1") as get_overview_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--overview",
                        "--overview-max-files",
                        "7",
                        "--overview-max-commands",
                        "3",
                        "--overview-max-checks",
                        "2",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Overview:", stdout.getvalue())
        get_overview_text.assert_called_once_with(Path(base).resolve(), max_files=7, max_commands=3, max_checks=2)
        create_chat_client.assert_not_called()

    def test_main_runs_repo_map_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_repo_map_text", return_value="Repo map:\n  files: 1/1") as get_repo_map_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--repo-map", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Repo map:", stdout.getvalue())
        get_repo_map_text.assert_called_once_with(Path(base).resolve(), "src")
        create_chat_client.assert_not_called()

    def test_main_runs_repo_map_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_repo_map_text", return_value="Repo map:\n  files: 1/1") as get_repo_map_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--repo-map",
                        "src",
                        "--repo-map-max-depth",
                        "2",
                        "--repo-map-max-files",
                        "8",
                        "--repo-map-max-symbols",
                        "9",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Repo map:", stdout.getvalue())
        get_repo_map_text.assert_called_once_with(Path(base).resolve(), "src", max_depth=2, max_files=8, max_symbols=9)
        create_chat_client.assert_not_called()

    def test_main_rejects_overview_repo_map_bounds_without_matching_local_flag(self) -> None:
        cases = [
            (["--overview-max-files", "7"], "--overview-max-files can only be used with --overview."),
            (["--overview-max-commands", "3"], "--overview-max-commands can only be used with --overview."),
            (["--overview-max-checks", "2"], "--overview-max-checks can only be used with --overview."),
            (["--repo-map-max-depth", "2"], "--repo-map-max-depth can only be used with --repo-map."),
            (["--repo-map-max-files", "8"], "--repo-map-max-files can only be used with --repo-map."),
            (["--repo-map-max-symbols", "9"], "--repo-map-max-symbols can only be used with --repo-map."),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), f"{expected}\n")
                create_chat_client.assert_not_called()

    def test_main_runs_search_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_search_text", return_value="Search:\n  matches: 1/1") as get_search_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--search", "needle", "--search-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Search:", stdout.getvalue())
        get_search_text.assert_called_once_with(Path(base).resolve(), "needle", "src")
        create_chat_client.assert_not_called()

    def test_main_runs_search_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_search_text", return_value="Search:\n  matches: 1/1") as get_search_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--search",
                        "needle.+",
                        "--search-path",
                        "src",
                        "--search-max-matches",
                        "5",
                        "--search-regex",
                        "--search-ignore-case",
                        "--search-context-lines",
                        "1",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Search:", stdout.getvalue())
        get_search_text.assert_called_once_with(
            Path(base).resolve(),
            "needle.+",
            "src",
            max_matches=5,
            regex=True,
            case_sensitive=False,
            context_lines=1,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_search_contexts_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_search_contexts_text", return_value="Search contexts:\n  contexts: 1/1") as get_search_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--search-contexts", "needle", "--search-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Search contexts:", stdout.getvalue())
        get_search_contexts_text.assert_called_once_with(Path(base).resolve(), "needle", "src")
        create_chat_client.assert_not_called()

    def test_main_runs_search_contexts_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_search_contexts_text", return_value="Search contexts:\n  contexts: 1/1") as get_search_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--search-contexts",
                        "needle.+",
                        "--search-path",
                        "src",
                        "--search-max-matches",
                        "4",
                        "--search-regex",
                        "--search-ignore-case",
                        "--search-context-lines",
                        "2",
                        "--search-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Search contexts:", stdout.getvalue())
        get_search_contexts_text.assert_called_once_with(
            Path(base).resolve(),
            "needle.+",
            "src",
            max_matches=4,
            regex=True,
            case_sensitive=False,
            context_lines=2,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_find_files_local_flag_with_options(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_find_files_text", return_value="Find Files:\n  matches: 1/1") as get_find_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--find-files",
                        "app.+",
                        "--find-files-path",
                        "src",
                        "--find-files-max-matches",
                        "5",
                        "--find-files-regex",
                        "--find-files-case-sensitive",
                        "--find-files-include-dirs",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Find Files:", stdout.getvalue())
        get_find_files_text.assert_called_once_with(
            Path(base).resolve(),
            "app.+",
            path="src",
            max_matches=5,
            regex=True,
            case_sensitive=True,
            include_dirs=True,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_project_orientation_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--overview", "--overview-max-files", "7"],
                "vibeagent.cli.get_overview_report",
                "vibeagent.cli.format_overview_report_text",
                "overview",
                (Path, ),
                {"max_files": 7},
            ),
            (
                ["--repo-map", "src", "--repo-map-max-depth", "2"],
                "vibeagent.cli.get_repo_map_report",
                "vibeagent.cli.format_repo_map_report_text",
                "repoMap",
                (Path, "src"),
                {"max_depth": 2},
            ),
            (
                ["--search", "needle", "--search-path", "src", "--search-max-matches", "5"],
                "vibeagent.cli.get_search_report",
                "vibeagent.cli.format_search_report_text",
                "search",
                (Path, "needle", "src"),
                {"max_matches": 5},
            ),
            (
                ["--search-contexts", "needle", "--search-path", "src", "--search-context-max-bytes", "1000"],
                "vibeagent.cli.get_search_contexts_report",
                "vibeagent.cli.format_search_contexts_report_text",
                "searchContexts",
                (Path, "needle", "src"),
                {"max_bytes_per_context": 1000},
            ),
            (
                ["--find-files", "app", "--find-files-path", "src", "--find-files-include-dirs"],
                "vibeagent.cli.get_find_files_report",
                "vibeagent.cli.format_find_files_report_text",
                "findFiles",
                (Path, "app"),
                {"path": "src", "include_dirs": True},
            ),
        ]
        for argv_tail, getter_target, formatter_target, payload_key, expected_args, expected_kwargs in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{payload_key}: ok"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch(formatter_target, return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(*resolved_args, **expected_kwargs)
                formatter.assert_called_once_with(report)
                create_chat_client.assert_not_called()

    def test_main_rejects_search_options_without_matching_local_flag(self) -> None:
        cases = [
            (["--search-max-matches", "5"], "--search-max-matches can only be used with --search or --search-contexts."),
            (["--search-regex"], "--search-regex can only be used with --search or --search-contexts."),
            (["--search-ignore-case"], "--search-ignore-case can only be used with --search or --search-contexts."),
            (["--search-context-lines", "2"], "--search-context-lines can only be used with --search or --search-contexts."),
            (["--search-context-max-bytes", "1000"], "--search-context-max-bytes can only be used with --search-contexts."),
            (["--search", "needle", "--search-context-max-bytes", "1000"], "--search-context-max-bytes can only be used with --search-contexts."),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), f"{expected}\n")
                create_chat_client.assert_not_called()

    def test_main_rejects_find_files_options_without_matching_local_flag(self) -> None:
        cases = [
            (["--find-files-path", "src"], "--find-files-path can only be used with --find-files."),
            (["--find-files-max-matches", "5"], "--find-files-max-matches can only be used with --find-files."),
            (["--find-files-regex"], "--find-files-regex can only be used with --find-files."),
            (["--find-files-case-sensitive"], "--find-files-case-sensitive can only be used with --find-files."),
            (["--find-files-include-dirs"], "--find-files-include-dirs can only be used with --find-files."),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), f"{expected}\n")
                create_chat_client.assert_not_called()

    def test_main_runs_glob_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_glob_text", return_value="Glob:\n  matches: 1/1") as get_glob_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--glob", "**/*.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Glob:", stdout.getvalue())
        get_glob_text.assert_called_once_with(Path(base).resolve(), "**/*.py")
        create_chat_client.assert_not_called()

    def test_main_runs_glob_local_flag_with_max_matches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_glob_text", return_value="Glob:\n  matches: 1/1") as get_glob_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--glob", "**/*.py", "--glob-max-matches", "4"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Glob:", stdout.getvalue())
        get_glob_text.assert_called_once_with(Path(base).resolve(), "**/*.py", max_matches=4)
        create_chat_client.assert_not_called()

    def test_main_runs_glob_local_flag_with_include_dirs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_glob_text", return_value="Glob:\n  matches: 1/1") as get_glob_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--glob", "src*", "--glob-include-dirs"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Glob:", stdout.getvalue())
        get_glob_text.assert_called_once_with(Path(base).resolve(), "src*", include_dirs=True)
        create_chat_client.assert_not_called()

    def test_main_runs_tree_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_tree_text", return_value="Tree:\n  entries: 1/1") as get_tree_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--tree", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Tree:", stdout.getvalue())
        get_tree_text.assert_called_once_with(Path(base).resolve(), "src")
        create_chat_client.assert_not_called()

    def test_main_runs_tree_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_tree_text", return_value="Tree:\n  entries: 1/1") as get_tree_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--tree", "src", "--tree-max-depth", "2", "--tree-max-entries", "30"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Tree:", stdout.getvalue())
        get_tree_text.assert_called_once_with(Path(base).resolve(), "src", max_depth=2, max_entries=30)
        create_chat_client.assert_not_called()

    def test_main_rejects_glob_tree_bounds_without_matching_local_flag(self) -> None:
        cases = [
            (["--glob-max-matches", "4"], "--glob-max-matches can only be used with --glob."),
            (["--glob-include-dirs"], "--glob-include-dirs can only be used with --glob."),
            (["--tree-max-depth", "2"], "--tree-max-depth can only be used with --tree."),
            (["--tree-max-entries", "30"], "--tree-max-entries can only be used with --tree."),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), f"{expected}\n")
                create_chat_client.assert_not_called()

    def test_main_inspection_local_flags_exit_nonzero_for_failed_results(self) -> None:
        cases = [
            (
                ["--tree", "missing-dir"],
                "vibeagent.cli.get_tree_text",
                "Tree:\n  ok: no\n  message: Path does not exist: missing-dir",
                (Path, "missing-dir"),
            ),
            (
                ["--image-info", "missing.png"],
                "vibeagent.cli.get_image_info_text",
                "Image info:\n  images: 0/1",
                (Path, ["missing.png"]),
            ),
        ]

        for argv_tail, patch_target, text, expected_args in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
            getter.assert_called_once_with(*resolved_args)
            create_chat_client.assert_not_called()

    def test_main_runs_symbols_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_symbols_text", return_value="Symbols:\n  files: 1/1") as get_symbols_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--symbols", "src/app.py", "web/app.ts"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Symbols:", stdout.getvalue())
        get_symbols_text.assert_called_once_with(Path(base).resolve(), ["src/app.py", "web/app.ts"])
        create_chat_client.assert_not_called()

    def test_main_runs_symbols_local_flag_with_max_symbols(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_symbols_text", return_value="Symbols:\n  files: 1/1") as get_symbols_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--symbols", "src/app.py", "web/app.ts", "--symbols-max", "12"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Symbols:", stdout.getvalue())
        get_symbols_text.assert_called_once_with(Path(base).resolve(), ["src/app.py", "web/app.ts"], max_symbols=12)
        create_chat_client.assert_not_called()

    def test_main_project_inspection_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "pkg").mkdir()
            (root / "web").mkdir()
            (root / "src" / "app.py").write_text(
                "import os\n\nclass App:\n    pass\n\ndef main():\n    return os.getcwd()\n",
                encoding="utf-8",
            )
            (root / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (root / "web" / "app.ts").write_text(
                "import { readFile } from 'fs';\nexport class View {}\nexport function render() {}\n",
                encoding="utf-8",
            )

            def run_json(*argv: str) -> tuple[int, dict[str, object]]:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(["--json", "--cwd", base, *argv])
                return exit_code, json.loads(stdout.getvalue())

            with patch("vibeagent.cli.create_chat_client") as create_chat_client:
                glob_exit, glob_payload = run_json("--glob", "**/*.py", "--glob-max-matches", "5", "--glob-include-dirs")
                tree_exit, tree_payload = run_json("--tree", "src", "--tree-max-depth", "3", "--tree-max-entries", "20")
                symbols_exit, symbols_payload = run_json("--symbols", "src/app.py", "web/app.ts", "--symbols-max", "20")

        self.assertEqual(glob_exit, 0)
        self.assertEqual(glob_payload["glob"]["pattern"], "**/*.py")
        self.assertTrue(glob_payload["glob"]["includeDirs"])
        self.assertEqual(glob_payload["glob"]["matches"]["shown"], 2)
        self.assertIn("src/app.py", glob_payload["glob"]["matches"]["files"])
        self.assertEqual(tree_exit, 0)
        self.assertEqual(tree_payload["tree"]["path"], "src")
        self.assertEqual(tree_payload["tree"]["entries"]["shown"], 3)
        self.assertIn("src/pkg/", tree_payload["tree"]["entries"]["items"])
        self.assertEqual(symbols_exit, 0)
        self.assertEqual(symbols_payload["symbols"]["files"]["ok"], 2)
        self.assertEqual(symbols_payload["symbols"]["counts"], {"symbols": 4, "imports": 2})
        self.assertEqual(symbols_payload["symbols"]["files"]["items"][0]["symbols"][0]["name"], "App")
        self.assertEqual(symbols_payload["symbols"]["files"]["items"][1]["language"], "typescript")
        create_chat_client.assert_not_called()

    def test_main_rejects_symbols_max_without_symbols_local_flag(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--symbols-max", "12"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--symbols-max can only be used with --symbols.\n")
        create_chat_client.assert_not_called()

    def test_main_source_analysis_local_flags_exit_nonzero_for_failed_results(self) -> None:
        cases = [
            (
                ["--symbols", "src/app.py", "missing.py"],
                "vibeagent.cli.get_symbols_text",
                "Symbols:\n  files: 1/2",
                (Path, ["src/app.py", "missing.py"]),
            ),
            (
                ["--python-deps", "missing.py"],
                "vibeagent.cli.get_python_deps_text",
                "Python dependencies:\n  ok: no\n  message: Path does not exist: missing.py",
                (Path, "missing.py"),
            ),
            (
                ["--code-deps", "missing.ts"],
                "vibeagent.cli.get_code_deps_text",
                "Code dependencies:\n  ok: no\n  message: Path does not exist: missing.ts",
                (Path, "missing.ts"),
            ),
        ]

        for argv_tail, patch_target, text, expected_args in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
            getter.assert_called_once_with(*resolved_args)
            create_chat_client.assert_not_called()

    def test_main_source_analysis_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "paths": ["missing.py"],
                "maxSymbols": 200,
                "files": {"ok": 0, "total": 1, "items": [{"path": "missing.py", "ok": False, "message": "Path does not exist: missing.py"}]},
                "counts": {"symbols": 0, "imports": 0},
                "message": "Read outlines for 0/1 source file(s).",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_symbols_report", return_value=report) as get_symbols_report,
                patch("vibeagent.cli.format_symbols_report_text", return_value="Symbols:\n  files: 0/1") as format_symbols_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--symbols", "missing.py"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Symbols:\n  files: 0/1")
        self.assertEqual(payload["symbols"], report)
        get_symbols_report.assert_called_once_with(Path(base).resolve(), ["missing.py"])
        format_symbols_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_scoped_symbol_local_flags_exit_nonzero_for_failed_results(self) -> None:
        cases = [
            (
                ["--python-defs", "main", "--python-path", "missing.py"],
                "vibeagent.cli.get_python_defs_text",
                "Python definitions:\n  ok: no\n  message: Path does not exist: missing.py",
                {"symbol": "main", "path": "missing.py"},
            ),
            (
                ["--python-refs", "main", "--python-path", "missing.py"],
                "vibeagent.cli.get_python_refs_text",
                "Python references:\n  ok: no\n  message: Path does not exist: missing.py",
                {"symbol": "main", "path": "missing.py"},
            ),
            (
                ["--python-ref-contexts", "main", "--python-path", "missing.py"],
                "vibeagent.cli.get_python_ref_contexts_text",
                "Python reference contexts:\n  ok: no\n  message: Path does not exist: missing.py",
                {"symbol": "main", "path": "missing.py"},
            ),
            (
                ["--python-calls", "main", "--python-path", "missing.py"],
                "vibeagent.cli.get_python_calls_text",
                "Python calls:\n  ok: no\n  message: Path does not exist: missing.py",
                {"symbol": "main", "path": "missing.py"},
            ),
            (
                ["--python-call-graph", "missing.py"],
                "vibeagent.cli.get_python_call_graph_text",
                "Python call graph:\n  ok: no\n  message: Path does not exist: missing.py",
                {},
            ),
            (
                ["--python-rename-preview", "main", "other", "--python-path", "missing.py"],
                "vibeagent.cli.get_python_rename_preview_text",
                "Python rename preview:\n  ok: no\n  message: Path does not exist: missing.py",
                {"symbol": "main", "new_name": "other", "path": "missing.py"},
            ),
            (
                ["--code-refs", "main", "--code-path", "missing.ts"],
                "vibeagent.cli.get_code_refs_text",
                "Code references:\n  ok: no\n  message: Path does not exist: missing.ts",
                {"symbol": "main", "path": "missing.ts"},
            ),
            (
                ["--code-ref-contexts", "main", "--code-path", "missing.ts"],
                "vibeagent.cli.get_code_ref_contexts_text",
                "Code reference contexts:\n  ok: no\n  message: Path does not exist: missing.ts",
                {"symbol": "main", "path": "missing.ts"},
            ),
            (
                ["--code-defs", "main", "--code-path", "missing.ts"],
                "vibeagent.cli.get_code_defs_text",
                "Code definitions:\n  ok: no\n  message: Path does not exist: missing.ts",
                {"symbol": "main", "path": "missing.ts"},
            ),
            (
                ["--code-rename-preview", "main", "other", "--code-path", "missing.ts"],
                "vibeagent.cli.get_code_rename_preview_text",
                "Code rename preview:\n  ok: no\n  message: Path does not exist: missing.ts",
                {"symbol": "main", "new_name": "other", "path": "missing.ts"},
            ),
        ]

        for argv_tail, patch_target, text, expected_kwargs in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            if argv_tail[0] == "--python-call-graph":
                getter.assert_called_once_with(Path(base).resolve(), "missing.py")
            else:
                getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_runs_file_info_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_file_info_text", return_value="File info:\n  paths: 1/1") as get_file_info_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--file-info", "src/app.py", "asset.bin"])

        self.assertEqual(exit_code, 0)
        self.assertIn("File info:", stdout.getvalue())
        get_file_info_text.assert_called_once_with(Path(base).resolve(), ["src/app.py", "asset.bin"])
        create_chat_client.assert_not_called()

    def test_main_runs_image_info_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_image_info_text", return_value="Image info:\n  images: 1/1") as get_image_info_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--image-info", "assets/logo.png"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Image info:", stdout.getvalue())
        get_image_info_text.assert_called_once_with(Path(base).resolve(), ["assets/logo.png"])
        create_chat_client.assert_not_called()

    def test_main_file_and_image_info_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "assets").mkdir()
            (root / "src" / "app.py").write_text("one\ntwo\n", encoding="utf-8")
            (root / "asset.bin").write_bytes(b"\x00\x01")
            (root / "assets" / "logo.png").write_bytes(
                b"\x89PNG\r\n\x1a\n"
                b"\x00\x00\x00\rIHDR"
                + (13).to_bytes(4, "big")
                + (17).to_bytes(4, "big")
                + b"\x08\x02\x00\x00\x00\x00\x00\x00\x00"
            )

            def run_json(*argv: str) -> tuple[int, dict[str, object]]:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(["--json", "--cwd", base, *argv])
                return exit_code, json.loads(stdout.getvalue())

            with patch("vibeagent.cli.create_chat_client") as create_chat_client:
                file_exit, file_payload = run_json("--file-info", "src/app.py", "src", "asset.bin")
                image_exit, image_payload = run_json("--image-info", "assets/logo.png", "assets")

        self.assertEqual(file_exit, 0)
        self.assertEqual(file_payload["fileInfo"]["paths"]["ok"], 3)
        self.assertEqual(file_payload["fileInfo"]["paths"]["items"][0]["path"], "src/app.py")
        self.assertEqual(file_payload["fileInfo"]["paths"]["items"][0]["type"], "file")
        self.assertEqual(file_payload["fileInfo"]["paths"]["items"][0]["lineCount"], 2)
        self.assertEqual(file_payload["fileInfo"]["paths"]["items"][1]["type"], "directory")
        self.assertTrue(file_payload["fileInfo"]["paths"]["items"][2]["binary"])
        self.assertEqual(image_exit, 1)
        self.assertEqual(image_payload["status"], "failed")
        self.assertEqual(image_payload["imageInfo"]["images"]["ok"], 1)
        self.assertEqual(image_payload["imageInfo"]["images"]["total"], 2)
        self.assertEqual(image_payload["imageInfo"]["images"]["items"][0]["format"], "png")
        self.assertEqual(image_payload["imageInfo"]["images"]["items"][0]["width"], 13)
        self.assertIn("Path is not a file", image_payload["imageInfo"]["images"]["items"][1]["message"])
        create_chat_client.assert_not_called()

    def test_main_runs_read_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_read_text", return_value="Read:\n  ok: yes") as get_read_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--read",
                        "src/app.py",
                        "--read-lines",
                        "2:4",
                        "--read-max-bytes",
                        "1000",
                        "--read-line-numbers",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Read:", stdout.getvalue())
        get_read_text.assert_called_once_with(
            Path(base).resolve(),
            "src/app.py",
            "2:4",
            max_bytes=1000,
            show_line_numbers=True,
        )
        create_chat_client.assert_not_called()

    def test_main_read_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\nfour\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

            def run_json(*argv: str) -> tuple[int, dict[str, object]]:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(["--json", "--cwd", base, *argv])
                return exit_code, json.loads(stdout.getvalue())

            with patch("vibeagent.cli.create_chat_client") as create_chat_client:
                read_exit, read_payload = run_json("--read", "src/app.py", "--read-lines", "2:3")
                files_exit, files_payload = run_json("--read-files", "src/app.py", "tests/test_app.py")
                ranges_exit, ranges_payload = run_json("--read-ranges", "src/app.py:2:3", "tests/test_app.py:1")

        self.assertEqual(read_exit, 0)
        self.assertEqual(read_payload["read"]["path"], "src/app.py")
        self.assertEqual(read_payload["read"]["range"], "2:3")
        self.assertIn("2: Two", read_payload["read"]["read"]["content"])
        self.assertEqual(files_exit, 0)
        self.assertEqual(files_payload["readFiles"]["files"]["ok"], 2)
        self.assertIn("alpha", files_payload["readFiles"]["files"]["items"][1]["content"])
        self.assertEqual(ranges_exit, 0)
        self.assertEqual(ranges_payload["readRanges"]["ranges"]["ok"], 2)
        self.assertEqual(ranges_payload["readRanges"]["ranges"]["items"][0]["endLine"], 3)
        self.assertIn("1: alpha", ranges_payload["readRanges"]["ranges"]["items"][1]["content"])
        create_chat_client.assert_not_called()

    def test_main_runs_tail_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_tail_text", return_value="Tail:\n  ok: yes") as get_tail_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--tail", "logs/app.log", "--tail-lines", "3", "--tail-max-bytes", "1000"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Tail:", stdout.getvalue())
        get_tail_text.assert_called_once_with(Path(base).resolve(), "logs/app.log", 3, max_bytes=1000)
        create_chat_client.assert_not_called()

    def test_main_runs_around_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_around_text", return_value="Around:\n  ok: yes") as get_around_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--around", "src/app.py", "42", "--around-lines", "8", "--around-max-bytes", "1200"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Around:", stdout.getvalue())
        get_around_text.assert_called_once_with(Path(base).resolve(), "src/app.py 42", 8, max_bytes=1200)
        create_chat_client.assert_not_called()

    def test_main_runs_around_many_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_around_many_text", return_value="Around many:\n  contexts: 2/2") as get_around_many_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--around-many", "src/app.py:42:8", "tests/test_app.py:17", "--around-many-max-bytes", "1400"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Around many:", stdout.getvalue())
        get_around_many_text.assert_called_once_with(Path(base).resolve(), ["src/app.py:42:8", "tests/test_app.py:17"], max_bytes_per_context=1400)
        create_chat_client.assert_not_called()

    def test_main_context_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nthree\nfour\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
            (root / "logs").mkdir()
            (root / "logs" / "app.log").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")

            def run_json(*argv: str) -> tuple[int, dict[str, object]]:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(["--json", "--cwd", base, *argv])
                return exit_code, json.loads(stdout.getvalue())

            with patch("vibeagent.cli.create_chat_client") as create_chat_client:
                tail_exit, tail_payload = run_json("--tail", "logs/app.log", "--tail-lines", "2")
                around_exit, around_payload = run_json("--around", "src/app.py", "3", "--around-lines", "1")
                many_exit, many_payload = run_json("--around-many", "src/app.py:3:1", "tests/test_app.py:2")

        self.assertEqual(tail_exit, 0)
        self.assertEqual(tail_payload["tail"]["path"], "logs/app.log")
        self.assertEqual(tail_payload["tail"]["tail"]["startLine"], 3)
        self.assertIn("3: three", tail_payload["tail"]["tail"]["content"])
        self.assertEqual(around_exit, 0)
        self.assertEqual(around_payload["around"]["path"], "src/app.py")
        self.assertEqual(around_payload["around"]["context"]["startLine"], 2)
        self.assertEqual(around_payload["around"]["context"]["endLine"], 4)
        self.assertIn("2: Two", around_payload["around"]["context"]["content"])
        self.assertEqual(many_exit, 0)
        self.assertEqual(many_payload["aroundMany"]["contexts"]["ok"], 2)
        self.assertEqual(many_payload["aroundMany"]["contexts"]["items"][1]["path"], "tests/test_app.py")
        self.assertIn("2: beta", many_payload["aroundMany"]["contexts"]["items"][1]["content"])
        create_chat_client.assert_not_called()

    def test_main_batch_read_local_flags_exit_nonzero_for_incomplete_results(self) -> None:
        cases = [
            (
                ["--around-many", "src/app.py:42:8", "missing.py:1"],
                "vibeagent.cli.get_around_many_text",
                "Around many:\n  contexts: 1/2",
                (Path, ["src/app.py:42:8", "missing.py:1"]),
            ),
            (
                ["--read-files", "src/app.py", "missing.py"],
                "vibeagent.cli.get_read_files_text",
                "Read files:\n  files: 1/2",
                (Path, ["src/app.py", "missing.py"]),
            ),
            (
                ["--read-ranges", "src/app.py:1:5", "missing.py:1:3"],
                "vibeagent.cli.get_read_ranges_text",
                "Read ranges:\n  ranges: 1/2",
                (Path, ["src/app.py:1:5", "missing.py:1:3"]),
            ),
        ]

        for argv_tail, patch_target, text, expected_args in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
            getter.assert_called_once_with(*resolved_args)
            create_chat_client.assert_not_called()

    def test_main_batch_read_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "files": {"ok": 0, "total": 2, "items": []},
                "maxBytesPerFile": 20000,
                "message": "Read 0/2 file(s).",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_read_files_report", return_value=report) as get_read_files_report,
                patch(
                    "vibeagent.cli.format_read_files_report_text",
                    return_value="Read files:\n  files: 0/2",
                ) as format_read_files_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--read-files", "missing-a.py", "missing-b.py"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Read files:\n  files: 0/2")
        self.assertEqual(payload["readFiles"], report)
        get_read_files_report.assert_called_once_with(Path(base).resolve(), ["missing-a.py", "missing-b.py"])
        format_read_files_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_output_contexts_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_output_contexts_text", return_value="Output contexts:\n  contexts: 1/1") as get_output_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--output-contexts",
                        "src/app.py:42:8",
                        "--output-context-lines",
                        "2",
                        "--output-context-max",
                        "5",
                        "--output-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Output contexts:", stdout.getvalue())
        get_output_contexts_text.assert_called_once_with(
            Path(base).resolve(),
            "src/app.py:42:8",
            context_lines=2,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_output_diagnostics_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_output_diagnostics_text", return_value="Output diagnostics:\n  diagnostics: 1/1") as get_output_diagnostics_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--output-diagnostics",
                        "ERROR src/app.py:42:8 failed",
                        "--output-diagnostic-lines",
                        "2",
                        "--output-diagnostic-max",
                        "5",
                        "--output-diagnostic-context-max",
                        "6",
                        "--output-diagnostic-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Output diagnostics:", stdout.getvalue())
        get_output_diagnostics_text.assert_called_once_with(
            Path(base).resolve(),
            "ERROR src/app.py:42:8 failed",
            context_lines=2,
            max_diagnostics=5,
            max_contexts=6,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_python_traceback_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_traceback_text", return_value="Python traceback:\n  diagnostics: 1/1") as get_python_traceback_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--python-traceback",
                        "ValueError: bad",
                        "--output-diagnostic-lines",
                        "2",
                        "--output-diagnostic-max",
                        "5",
                        "--output-diagnostic-context-max",
                        "6",
                        "--output-diagnostic-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Python traceback:", stdout.getvalue())
        get_python_traceback_text.assert_called_once_with(
            Path(base).resolve(),
            "ValueError: bad",
            context_lines=2,
            max_diagnostics=5,
            max_contexts=6,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_output_analysis_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nraise ValueError('bad')\nfour\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

            def run_json(*argv: str) -> tuple[int, dict[str, object]]:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(["--json", "--cwd", base, *argv])
                return exit_code, json.loads(stdout.getvalue())

            with patch("vibeagent.cli.create_chat_client") as create_chat_client:
                contexts_exit, contexts_payload = run_json(
                    "--output-contexts",
                    "src/app.py:3: boom\ntests/test_app.py:2:5: assertion failed",
                    "--output-context-lines",
                    "1",
                    "--output-context-max-bytes",
                    "1000",
                )
                diagnostics_exit, diagnostics_payload = run_json(
                    "--output-diagnostics",
                    "warning: src/app.py:2:3 check this\nERROR src/app.py:3 failed",
                    "--output-diagnostic-lines",
                    "0",
                    "--output-diagnostic-context-max-bytes",
                    "1000",
                )
                traceback_exit, traceback_payload = run_json(
                    "--python-traceback",
                    'Traceback (most recent call last):\n  File "src/app.py", line 3, in run\nValueError: bad',
                    "--output-diagnostic-lines",
                    "0",
                    "--output-diagnostic-context-max-bytes",
                    "1000",
                )

        self.assertEqual(contexts_exit, 0)
        self.assertEqual(contexts_payload["outputContexts"]["contexts"]["ok"], 2)
        self.assertEqual(contexts_payload["outputContexts"]["contexts"]["items"][0]["path"], "src/app.py")
        self.assertIn("3: raise ValueError('bad')", contexts_payload["outputContexts"]["contexts"]["items"][0]["content"])
        self.assertEqual(diagnostics_exit, 0)
        self.assertEqual(diagnostics_payload["outputDiagnostics"]["diagnostics"]["shown"], 2)
        self.assertEqual(diagnostics_payload["outputDiagnostics"]["diagnostics"]["items"][0]["severity"], "warning")
        self.assertEqual(diagnostics_payload["outputDiagnostics"]["contexts"]["ok"], 2)
        self.assertEqual(traceback_exit, 0)
        self.assertEqual(traceback_payload["pythonTraceback"]["diagnostics"]["shown"], 3)
        self.assertEqual(traceback_payload["pythonTraceback"]["contexts"]["ok"], 1)
        self.assertIn("3: raise ValueError('bad')", traceback_payload["pythonTraceback"]["contexts"]["items"][0]["content"])
        create_chat_client.assert_not_called()

    def test_main_output_context_local_flags_exit_nonzero_for_unreadable_contexts(self) -> None:
        cases = [
            (
                [
                    "--output-contexts",
                    "ERROR missing.py:1: boom",
                    "--output-context-lines",
                    "2",
                    "--output-context-max",
                    "5",
                    "--output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_output_contexts_text",
                "Output contexts:\n  contexts: 0/1",
                ("ERROR missing.py:1: boom",),
                {"context_lines": 2, "max_contexts": 5, "max_bytes_per_context": 1000},
            ),
            (
                [
                    "--output-diagnostics",
                    "ERROR missing.py:1: boom",
                    "--output-diagnostic-lines",
                    "2",
                    "--output-diagnostic-max",
                    "5",
                    "--output-diagnostic-context-max",
                    "6",
                    "--output-diagnostic-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_output_diagnostics_text",
                "Output diagnostics:\n  diagnostics: 1/1\n  contexts: 0/1",
                ("ERROR missing.py:1: boom",),
                {"context_lines": 2, "max_diagnostics": 5, "max_contexts": 6, "max_bytes_per_context": 1000},
            ),
            (
                [
                    "--python-traceback",
                    'File "missing.py", line 1\nValueError: boom',
                    "--output-diagnostic-lines",
                    "2",
                    "--output-diagnostic-max",
                    "5",
                    "--output-diagnostic-context-max",
                    "6",
                    "--output-diagnostic-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_python_traceback_text",
                "Python traceback:\n  diagnostics: 2/2\n  contexts: 0/1",
                ('File "missing.py", line 1\nValueError: boom',),
                {"context_lines": 2, "max_diagnostics": 5, "max_contexts": 6, "max_bytes_per_context": 1000},
            ),
        ]

        for argv_tail, patch_target, text, expected_args, expected_kwargs in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            getter.assert_called_once_with(Path(base).resolve(), *expected_args, **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_output_context_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "contexts": {"ok": 0, "total": 1, "items": []},
                "totalRefs": 1,
                "contextLines": 5,
                "maxContexts": 20,
                "maxBytesPerContext": 20000,
                "truncated": False,
                "message": "Read 0/1 referenced context(s).",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_output_contexts_report", return_value=report) as get_output_contexts_report,
                patch(
                    "vibeagent.cli.format_output_contexts_report_text",
                    return_value="Output contexts:\n  contexts: 0/1",
                ) as format_output_contexts_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--output-contexts", "ERROR missing.py:1: boom"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Output contexts:\n  contexts: 0/1")
        self.assertEqual(payload["outputContexts"], report)
        get_output_contexts_report.assert_called_once_with(
            Path(base).resolve(),
            "ERROR missing.py:1: boom",
            context_lines=5,
            max_contexts=20,
            max_bytes_per_context=20000,
        )
        format_output_contexts_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_read_files_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_read_files_text", return_value="Read files:\n  files: 2/2") as get_read_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--read-files",
                        "src/app.py",
                        "tests/test_app.py",
                        "--read-files-max-bytes",
                        "1000",
                        "--read-files-line-numbers",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Read files:", stdout.getvalue())
        get_read_files_text.assert_called_once_with(
            Path(base).resolve(),
            ["src/app.py", "tests/test_app.py"],
            max_bytes_per_file=1000,
            show_line_numbers=True,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_read_ranges_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_read_ranges_text", return_value="Read ranges:\n  ranges: 2/2") as get_read_ranges_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--read-ranges", "src/app.py:2:4", "tests/test_app.py:1", "--read-ranges-max-bytes", "1000"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Read ranges:", stdout.getvalue())
        get_read_ranges_text.assert_called_once_with(Path(base).resolve(), ["src/app.py:2:4", "tests/test_app.py:1"], max_bytes_per_range=1000)
        create_chat_client.assert_not_called()

    def test_main_runs_python_check_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_check_text", return_value="Python check:\n  ok: yes") as get_python_check_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-check", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python check:", stdout.getvalue())
        get_python_check_text.assert_called_once_with(Path(base).resolve(), "src")
        create_chat_client.assert_not_called()

    def test_main_runs_python_deps_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_deps_text", return_value="Python dependencies:\n  files: 1/1") as get_python_deps_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-deps", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python dependencies:", stdout.getvalue())
        get_python_deps_text.assert_called_once_with(Path(base).resolve(), "src")
        create_chat_client.assert_not_called()

    def test_main_runs_python_deps_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_deps_text", return_value="Python dependencies:\n  files: 1/1") as get_python_deps_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--python-deps",
                        "src",
                        "--python-deps-max-files",
                        "7",
                        "--python-deps-max-imports",
                        "8",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Python dependencies:", stdout.getvalue())
        get_python_deps_text.assert_called_once_with(Path(base).resolve(), "src", max_files=7, max_imports=8)
        create_chat_client.assert_not_called()

    def test_main_runs_python_defs_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_defs_text", return_value="Python definitions:\n  definitions: 1/1") as get_python_defs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-defs", "Runner.run", "--python-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python definitions:", stdout.getvalue())
        get_python_defs_text.assert_called_once_with(Path(base).resolve(), symbol="Runner.run", path="src")
        create_chat_client.assert_not_called()

    def test_main_runs_python_refs_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_refs_text", return_value="Python references:\n  references: 1/1") as get_python_refs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-refs", "run_agent", "--python-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python references:", stdout.getvalue())
        get_python_refs_text.assert_called_once_with(Path(base).resolve(), symbol="run_agent", path="src")
        create_chat_client.assert_not_called()

    def test_main_runs_python_ref_contexts_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_ref_contexts_text", return_value="Python reference contexts:\n  contexts: 1/1") as get_python_ref_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-ref-contexts", "run_agent", "--python-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python reference contexts:", stdout.getvalue())
        get_python_ref_contexts_text.assert_called_once_with(Path(base).resolve(), symbol="run_agent", path="src")
        create_chat_client.assert_not_called()

    def test_main_runs_python_calls_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_calls_text", return_value="Python calls:\n  calls: 1/1") as get_python_calls_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-calls", "helper", "--python-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python calls:", stdout.getvalue())
        get_python_calls_text.assert_called_once_with(Path(base).resolve(), symbol="helper", path="src")
        create_chat_client.assert_not_called()

    def test_main_runs_python_symbol_local_flags_with_bounds(self) -> None:
        cases = [
            (
                ["--python-defs", "Runner.run", "--python-path", "src", "--python-max-matches", "3", "--python-def-max-lines", "40"],
                "vibeagent.cli.get_python_defs_text",
                "Python definitions:\n  definitions: 1/1",
                {"symbol": "Runner.run", "path": "src", "max_matches": 3, "max_lines": 40},
            ),
            (
                ["--python-refs", "run_agent", "--python-path", "src", "--python-max-matches", "4"],
                "vibeagent.cli.get_python_refs_text",
                "Python references:\n  references: 1/1",
                {"symbol": "run_agent", "path": "src", "max_matches": 4},
            ),
            (
                [
                    "--python-ref-contexts",
                    "run_agent",
                    "--python-path",
                    "src",
                    "--python-max-matches",
                    "5",
                    "--python-context-lines",
                    "1",
                    "--python-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_python_ref_contexts_text",
                "Python reference contexts:\n  contexts: 1/1",
                {"symbol": "run_agent", "path": "src", "max_matches": 5, "context_lines": 1, "max_bytes_per_context": 1000},
            ),
            (
                ["--python-calls", "helper", "--python-path", "src", "--python-max-matches", "6"],
                "vibeagent.cli.get_python_calls_text",
                "Python calls:\n  calls: 1/1",
                {"symbol": "helper", "path": "src", "max_matches": 6},
            ),
        ]

        for argv_tail, patch_target, text, expected_kwargs in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_rejects_python_symbol_bounds_without_matching_local_flag(self) -> None:
        cases = [
            (
                ["--python-max-matches", "3"],
                "--python-max-matches can only be used with --python-defs, --python-refs, --python-ref-contexts, or --python-calls.",
            ),
            (
                ["--python-def-max-lines", "40"],
                "--python-def-max-lines can only be used with --python-defs.",
            ),
            (
                ["--python-refs", "run_agent", "--python-def-max-lines", "40"],
                "--python-def-max-lines can only be used with --python-defs.",
            ),
            (
                ["--python-context-lines", "1"],
                "--python-context-lines can only be used with --python-ref-contexts.",
            ),
            (
                ["--python-refs", "run_agent", "--python-context-lines", "1"],
                "--python-context-lines can only be used with --python-ref-contexts.",
            ),
            (
                ["--python-context-max-bytes", "1000"],
                "--python-context-max-bytes can only be used with --python-ref-contexts.",
            ),
            (
                ["--python-deps-max-files", "5"],
                "--python-deps-max-files can only be used with --python-deps.",
            ),
            (
                ["--python-deps-max-imports", "20"],
                "--python-deps-max-imports can only be used with --python-deps.",
            ),
            (
                ["--python-call-graph-max-files", "5"],
                "--python-call-graph-max-files can only be used with --python-call-graph.",
            ),
            (
                ["--python-call-graph-max-edges", "20"],
                "--python-call-graph-max-edges can only be used with --python-call-graph.",
            ),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), f"{expected}\n")
                create_chat_client.assert_not_called()

    def test_main_runs_python_call_graph_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_call_graph_text", return_value="Python call graph:\n  edges: 3/3") as get_python_call_graph_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--python-call-graph",
                        "src",
                        "--python-call-graph-max-files",
                        "7",
                        "--python-call-graph-max-edges",
                        "9",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Python call graph:", stdout.getvalue())
        get_python_call_graph_text.assert_called_once_with(Path(base).resolve(), "src", max_files=7, max_edges=9)
        create_chat_client.assert_not_called()

    def test_main_runs_python_code_intelligence_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--python-check", "src"],
                "vibeagent.cli.get_python_check_report",
                "vibeagent.cli.format_python_check_report_text",
                "pythonCheck",
                (Path, "src"),
                {},
            ),
            (
                ["--python-deps", "src", "--python-deps-max-files", "7", "--python-deps-max-imports", "8"],
                "vibeagent.cli.get_python_deps_report",
                "vibeagent.cli.format_python_deps_report_text",
                "pythonDependencies",
                (Path, "src"),
                {"max_files": 7, "max_imports": 8},
            ),
            (
                ["--python-defs", "Runner.run", "--python-path", "src", "--python-max-matches", "3", "--python-def-max-lines", "40"],
                "vibeagent.cli.get_python_defs_report",
                "vibeagent.cli.format_python_defs_report_text",
                "pythonDefinitions",
                (Path, ),
                {"symbol": "Runner.run", "path": "src", "max_matches": 3, "max_lines": 40},
            ),
            (
                ["--python-refs", "run_agent", "--python-path", "src", "--python-max-matches", "4"],
                "vibeagent.cli.get_python_refs_report",
                "vibeagent.cli.format_python_refs_report_text",
                "pythonReferences",
                (Path, ),
                {"symbol": "run_agent", "path": "src", "max_matches": 4},
            ),
            (
                [
                    "--python-ref-contexts",
                    "run_agent",
                    "--python-path",
                    "src",
                    "--python-max-matches",
                    "5",
                    "--python-context-lines",
                    "1",
                    "--python-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_python_ref_contexts_report",
                "vibeagent.cli.format_python_ref_contexts_report_text",
                "pythonReferenceContexts",
                (Path, ),
                {"symbol": "run_agent", "path": "src", "max_matches": 5, "context_lines": 1, "max_bytes_per_context": 1000},
            ),
            (
                ["--python-calls", "helper", "--python-path", "src", "--python-max-matches", "6"],
                "vibeagent.cli.get_python_calls_report",
                "vibeagent.cli.format_python_calls_report_text",
                "pythonCalls",
                (Path, ),
                {"symbol": "helper", "path": "src", "max_matches": 6},
            ),
            (
                ["--python-call-graph", "src", "--python-call-graph-max-files", "7", "--python-call-graph-max-edges", "8"],
                "vibeagent.cli.get_python_call_graph_report",
                "vibeagent.cli.format_python_call_graph_report_text",
                "pythonCallGraph",
                (Path, "src"),
                {"max_files": 7, "max_edges": 8},
            ),
        ]
        for argv_tail, getter_target, formatter_target, payload_key, expected_args, expected_kwargs in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{payload_key}: ok"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch(formatter_target, return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(*resolved_args, **expected_kwargs)
                formatter.assert_called_once_with(report)
                create_chat_client.assert_not_called()

    def test_main_runs_python_rename_preview_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_rename_preview_text", return_value="Python rename preview:\n  replacements: 2") as get_python_rename_preview_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-rename-preview", "run_agent", "execute_agent", "--python-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python rename preview:", stdout.getvalue())
        get_python_rename_preview_text.assert_called_once_with(Path(base).resolve(), symbol="run_agent", new_name="execute_agent", path="src")
        create_chat_client.assert_not_called()

    def test_main_runs_python_rename_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_rename_text", return_value="Python rename:\n  replacements: 2") as get_python_rename_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-rename", "run_agent", "execute_agent", "--python-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python rename:", stdout.getvalue())
        get_python_rename_text.assert_called_once_with(Path(base).resolve(), symbol="run_agent", new_name="execute_agent", path="src")
        create_chat_client.assert_not_called()

    def test_main_runs_replace_python_definition_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_replace_python_definition_text", return_value="Check replace Python definition:\n  ok: yes") as get_check_replace_python_definition_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--check-replace-python-def",
                        "Runner.run",
                        "    def run(self):\n        return 2\n",
                        "--python-path",
                        "src",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Check replace Python definition:", stdout.getvalue())
        get_check_replace_python_definition_text.assert_called_once_with(
            Path(base).resolve(),
            symbol="Runner.run",
            content="    def run(self):\n        return 2\n",
            path="src",
        )
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_replace_python_definition_text", return_value="Replace Python definition:\n  ok: yes") as get_replace_python_definition_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--replace-python-def",
                        "Runner.run",
                        "    def run(self):\n        return 2\n",
                        "--python-path",
                        "src",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Replace Python definition:", stdout.getvalue())
        get_replace_python_definition_text.assert_called_once_with(
            Path(base).resolve(),
            symbol="Runner.run",
            content="    def run(self):\n        return 2\n",
            path="src",
        )
        create_chat_client.assert_not_called()

    def test_main_runs_python_refactor_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--python-rename-preview", "run_agent", "execute_agent", "--python-path", "src"],
                "vibeagent.cli.get_python_rename_preview_report",
                "vibeagent.cli.format_python_rename_report_text",
                "Python rename preview:",
                "pythonRenamePreview",
                {"symbol": "run_agent", "new_name": "execute_agent", "path": "src"},
            ),
            (
                ["--python-rename", "run_agent", "execute_agent", "--python-path", "src"],
                "vibeagent.cli.get_python_rename_report",
                "vibeagent.cli.format_python_rename_report_text",
                "Python rename:",
                "pythonRename",
                {"symbol": "run_agent", "new_name": "execute_agent", "path": "src"},
            ),
            (
                ["--check-replace-python-def", "Runner.run", "    def run(self):\n        return 2\n", "--python-path", "src"],
                "vibeagent.cli.get_check_replace_python_definition_report",
                "vibeagent.cli.format_replace_python_definition_report_text",
                "Check replace Python definition:",
                "checkReplacePythonDefinition",
                {"symbol": "Runner.run", "content": "    def run(self):\n        return 2\n", "path": "src"},
            ),
            (
                ["--replace-python-def", "Runner.run", "    def run(self):\n        return 2\n", "--python-path", "src"],
                "vibeagent.cli.get_replace_python_definition_report",
                "vibeagent.cli.format_replace_python_definition_report_text",
                "Replace Python definition:",
                "replacePythonDefinition",
                {"symbol": "Runner.run", "content": "    def run(self):\n        return 2\n", "path": "src"},
            ),
        ]

        for argv_tail, getter_target, formatter_target, title, payload_key, expected_kwargs in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{payload_key}: ok"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch(formatter_target, return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_check_replace_python_definition_local_flag_exits_nonzero_for_failed_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch(
                    "vibeagent.cli.get_check_replace_python_definition_text",
                    return_value="Check replace Python definition:\n  ok: no\n  message: Path does not exist: missing.py",
                ) as get_check_replace_python_definition_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--check-replace-python-def",
                        "Runner.run",
                        "    def run(self):\n        return 2\n",
                        "--python-path",
                        "missing.py",
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "Check replace Python definition:\n  ok: no\n  message: Path does not exist: missing.py\n")
        get_check_replace_python_definition_text.assert_called_once_with(
            Path(base).resolve(),
            symbol="Runner.run",
            content="    def run(self):\n        return 2\n",
            path="missing.py",
        )
        create_chat_client.assert_not_called()

    def test_main_check_replace_python_definition_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"ok": False, "message": "Python definition not found: Runner.run"}

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_replace_python_definition_report", return_value=report) as get_check_replace_python_definition_report,
                patch("vibeagent.cli.format_replace_python_definition_report_text", return_value="Check replace Python definition:\n  ok: no") as formatter,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--check-replace-python-def", "Runner.run", "content"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Check replace Python definition:\n  ok: no")
        self.assertEqual(payload["checkReplacePythonDefinition"], report)
        get_check_replace_python_definition_report.assert_called_once_with(Path(base).resolve(), symbol="Runner.run", content="content", path=None)
        formatter.assert_called_once_with("Check replace Python definition:", report)
        create_chat_client.assert_not_called()

    def test_main_runs_config_check_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_config_check_text", return_value="Config check:\n  ok: yes") as get_config_check_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--config-check", "pyproject.toml"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Config check:", stdout.getvalue())
        get_config_check_text.assert_called_once_with(Path(base).resolve(), "pyproject.toml")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "path": "pyproject.toml",
                "files": {"shown": 1, "total": 1, "items": [{"path": "pyproject.toml", "ok": True, "format": "toml", "line": None, "column": None, "message": "ok"}]},
                "truncated": False,
                "message": "Checked 1/1 config file(s); 0 failed.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_config_check_report", return_value=report) as get_config_check_report,
                patch("vibeagent.cli.format_config_check_report_text", return_value="Config check:\n  ok: yes") as format_config_check_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--config-check", "pyproject.toml"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["configCheck"], report)
        self.assertEqual(payload["text"], "Config check:\n  ok: yes")
        get_config_check_report.assert_called_once_with(Path(base).resolve(), "pyproject.toml")
        format_config_check_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_config_check_local_flag_exits_nonzero_when_not_ok(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_config_check_text", return_value="Config check:\n  ok: no\n  message: invalid"),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--config-check", "pyproject.toml"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Config check:", stdout.getvalue())
        self.assertIn("ok: no", stdout.getvalue())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "path": "pyproject.toml",
                "files": {"shown": 1, "total": 1, "items": [{"path": "pyproject.toml", "ok": False, "format": "toml", "line": 1, "column": 1, "message": "invalid"}]},
                "truncated": False,
                "message": "Checked 1/1 config file(s); 1 failed.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_config_check_report", return_value=report) as get_config_check_report,
                patch("vibeagent.cli.format_config_check_report_text", return_value="Config check:\n  ok: no\n  message: invalid") as format_config_check_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--config-check", "pyproject.toml"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["configCheck"], report)
        self.assertIn("ok: no", payload["text"])
        get_config_check_report.assert_called_once_with(Path(base).resolve(), "pyproject.toml")
        format_config_check_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_json_set_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_json_set_text", return_value="Check JSON set:\n  ok: yes") as get_check_json_set_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-json-set", "package.json", "/private", "true", "--json-create-missing"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check JSON set:", stdout.getvalue())
        get_check_json_set_text.assert_called_once_with(
            Path(base).resolve(),
            path="package.json",
            pointer="/private",
            value=True,
            create_missing=True,
        )
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_json_set_text", return_value="JSON set:\n  ok: yes") as get_json_set_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--json-set", "package.json", "/scripts/test", '"npm test"'])

        self.assertEqual(exit_code, 0)
        self.assertIn("JSON set:", stdout.getvalue())
        get_json_set_text.assert_called_once_with(
            Path(base).resolve(),
            path="package.json",
            pointer="/scripts/test",
            value="npm test",
            create_missing=False,
        )
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"projectRoot": str(Path(base).resolve()), "kind": "check_json_set", "ok": True, "path": "package.json", "pointer": "/private", "value": True, "createMissing": True, "message": "JSON set preview succeeded.", "diff": ""}

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_json_set_report", return_value=report) as get_check_json_set_report,
                patch("vibeagent.cli.format_json_pointer_report_text", return_value="Check JSON set:\n  ok: yes") as format_json_pointer_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--check-json-set", "package.json", "/private", "true", "--json-create-missing"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["checkJsonSet"], report)
        self.assertEqual(payload["text"], "Check JSON set:\n  ok: yes")
        get_check_json_set_report.assert_called_once_with(
            Path(base).resolve(),
            path="package.json",
            pointer="/private",
            value=True,
            create_missing=True,
        )
        format_json_pointer_report_text.assert_called_once_with("Check JSON set:", report)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"projectRoot": str(Path(base).resolve()), "kind": "json_set", "ok": True, "path": "package.json", "pointer": "/scripts/test", "value": "npm test", "createMissing": False, "message": "JSON value set.", "diff": ""}

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_json_set_report", return_value=report) as get_json_set_report,
                patch("vibeagent.cli.format_json_pointer_report_text", return_value="JSON set:\n  ok: yes") as format_json_pointer_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--json-set", "package.json", "/scripts/test", '"npm test"'])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["jsonSet"], report)
        self.assertEqual(payload["text"], "JSON set:\n  ok: yes")
        get_json_set_report.assert_called_once_with(
            Path(base).resolve(),
            path="package.json",
            pointer="/scripts/test",
            value="npm test",
            create_missing=False,
        )
        format_json_pointer_report_text.assert_called_once_with("JSON set:", report)
        create_chat_client.assert_not_called()

    def test_main_check_json_set_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "kind": "check_json_set",
                "ok": False,
                "path": "missing.json",
                "pointer": "/a",
                "value": 1,
                "createMissing": False,
                "message": "File does not exist",
                "diff": "",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_json_set_report", return_value=report) as get_check_json_set_report,
                patch("vibeagent.cli.format_json_pointer_report_text", return_value="Check JSON set:\n  ok: no\n  message: File does not exist") as format_json_pointer_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--check-json-set", "missing.json", "/a", "1"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["checkJsonSet"], report)
        self.assertIn("ok: no", payload["text"])
        get_check_json_set_report.assert_called_once_with(
            Path(base).resolve(),
            path="missing.json",
            pointer="/a",
            value=1,
            create_missing=False,
        )
        format_json_pointer_report_text.assert_called_once_with("Check JSON set:", report)
        create_chat_client.assert_not_called()

    def test_main_runs_json_remove_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_json_remove_text", return_value="Check JSON remove:\n  ok: yes") as get_check_json_remove_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-json-remove", "package.json", "/scripts/dev"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check JSON remove:", stdout.getvalue())
        get_check_json_remove_text.assert_called_once_with(Path(base).resolve(), path="package.json", pointer="/scripts/dev")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_json_remove_text", return_value="JSON remove:\n  ok: yes") as get_json_remove_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--json-remove", "package.json", "/keywords/0"])

        self.assertEqual(exit_code, 0)
        self.assertIn("JSON remove:", stdout.getvalue())
        get_json_remove_text.assert_called_once_with(Path(base).resolve(), path="package.json", pointer="/keywords/0")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"projectRoot": str(Path(base).resolve()), "kind": "check_json_remove", "ok": True, "path": "package.json", "pointer": "/scripts/dev", "message": "JSON remove preview succeeded.", "diff": ""}

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_json_remove_report", return_value=report) as get_check_json_remove_report,
                patch("vibeagent.cli.format_json_pointer_report_text", return_value="Check JSON remove:\n  ok: yes") as format_json_pointer_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--check-json-remove", "package.json", "/scripts/dev"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["checkJsonRemove"], report)
        self.assertEqual(payload["text"], "Check JSON remove:\n  ok: yes")
        get_check_json_remove_report.assert_called_once_with(Path(base).resolve(), path="package.json", pointer="/scripts/dev")
        format_json_pointer_report_text.assert_called_once_with("Check JSON remove:", report)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"projectRoot": str(Path(base).resolve()), "kind": "json_remove", "ok": True, "path": "package.json", "pointer": "/keywords/0", "message": "JSON value removed.", "diff": ""}

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_json_remove_report", return_value=report) as get_json_remove_report,
                patch("vibeagent.cli.format_json_pointer_report_text", return_value="JSON remove:\n  ok: yes") as format_json_pointer_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--json-remove", "package.json", "/keywords/0"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["jsonRemove"], report)
        self.assertEqual(payload["text"], "JSON remove:\n  ok: yes")
        get_json_remove_report.assert_called_once_with(Path(base).resolve(), path="package.json", pointer="/keywords/0")
        format_json_pointer_report_text.assert_called_once_with("JSON remove:", report)
        create_chat_client.assert_not_called()

    def test_main_runs_json_patch_local_flags_without_creating_client(self) -> None:
        operations = '[{"op":"replace","path":"/private","value":true}]'
        parsed_operations = [{"op": "replace", "path": "/private", "value": True}]
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_json_patch_text", return_value="Check JSON patch:\n  ok: yes") as get_check_json_patch_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-json-patch", "package.json", operations])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check JSON patch:", stdout.getvalue())
        get_check_json_patch_text.assert_called_once_with(Path(base).resolve(), path="package.json", operations=parsed_operations)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_json_patch_text", return_value="JSON patch:\n  ok: yes") as get_json_patch_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--json-patch", "package.json", operations])

        self.assertEqual(exit_code, 0)
        self.assertIn("JSON patch:", stdout.getvalue())
        get_json_patch_text.assert_called_once_with(Path(base).resolve(), path="package.json", operations=parsed_operations)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"projectRoot": str(Path(base).resolve()), "kind": "check_json_patch", "ok": True, "path": "package.json", "operations": {"total": 1, "items": parsed_operations}, "message": "JSON patch preview succeeded.", "diff": ""}

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_json_patch_report", return_value=report) as get_check_json_patch_report,
                patch("vibeagent.cli.format_json_patch_report_text", return_value="Check JSON patch:\n  ok: yes") as format_json_patch_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--check-json-patch", "package.json", operations])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["checkJsonPatch"], report)
        self.assertEqual(payload["text"], "Check JSON patch:\n  ok: yes")
        get_check_json_patch_report.assert_called_once_with(Path(base).resolve(), path="package.json", operations=parsed_operations)
        format_json_patch_report_text.assert_called_once_with("Check JSON patch:", report)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"projectRoot": str(Path(base).resolve()), "kind": "json_patch", "ok": True, "path": "package.json", "operations": {"total": 1, "items": parsed_operations}, "message": "JSON patch applied.", "diff": ""}

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_json_patch_report", return_value=report) as get_json_patch_report,
                patch("vibeagent.cli.format_json_patch_report_text", return_value="JSON patch:\n  ok: yes") as format_json_patch_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--json-patch", "package.json", operations])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["jsonPatch"], report)
        self.assertEqual(payload["text"], "JSON patch:\n  ok: yes")
        get_json_patch_report.assert_called_once_with(Path(base).resolve(), path="package.json", operations=parsed_operations)
        format_json_patch_report_text.assert_called_once_with("JSON patch:", report)
        create_chat_client.assert_not_called()

    def test_main_runs_line_edit_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_replace_lines_text", return_value="Check replace lines:\n  ok: yes") as get_check_replace_lines_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-replace-lines", "app.py", "2", "3", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check replace lines:", stdout.getvalue())
        get_check_replace_lines_text.assert_called_once_with(Path(base).resolve(), path="app.py", start_line="2", end_line="3", content="new\\n")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_replace_lines_text", return_value="Replace lines:\n  ok: yes") as get_replace_lines_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--replace-lines", "app.py", "2", "2", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Replace lines:", stdout.getvalue())
        get_replace_lines_text.assert_called_once_with(Path(base).resolve(), path="app.py", start_line="2", end_line="2", content="new\\n")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-replace-lines",
                "vibeagent.cli.get_check_replace_lines_report",
                "Check replace lines:",
                "checkReplaceLines",
            ),
            (
                "--replace-lines",
                "vibeagent.cli.get_replace_lines_report",
                "Replace lines:",
                "replaceLines",
            ),
        ]
        for flag, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": "app.py",
                    "startLine": 2,
                    "endLine": 2,
                    "message": "ok",
                    "diff": {"text": "+new", "lines": ["+new"], "lineCount": 1},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_line_edit_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, "app.py", "2", "2", "new\\n"])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path="app.py", start_line="2", end_line="2", content="new\\n")
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_insert_lines_text", return_value="Check insert lines:\n  ok: yes") as get_check_insert_lines_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-insert-lines", "app.py", "2", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check insert lines:", stdout.getvalue())
        get_check_insert_lines_text.assert_called_once_with(Path(base).resolve(), path="app.py", line="2", content="new\\n")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_insert_lines_text", return_value="Insert lines:\n  ok: yes") as get_insert_lines_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--insert-lines", "app.py", "2", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Insert lines:", stdout.getvalue())
        get_insert_lines_text.assert_called_once_with(Path(base).resolve(), path="app.py", line="2", content="new\\n")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_append_file_text", return_value="Check append:\n  ok: yes") as get_check_append_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-append", "app.py", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check append:", stdout.getvalue())
        get_check_append_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", content="new\\n")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_append_file_text", return_value="Append:\n  ok: yes") as get_append_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--append", "app.py", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Append:", stdout.getvalue())
        get_append_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", content="new\\n")
        create_chat_client.assert_not_called()

        json_cases = [
            (
                "--check-insert-lines",
                "vibeagent.cli.get_check_insert_lines_report",
                "Check insert lines:",
                "checkInsertLines",
                ["app.py", "2", "new\\n"],
                {"path": "app.py", "line": "2", "content": "new\\n"},
                {"line": 2},
            ),
            (
                "--insert-lines",
                "vibeagent.cli.get_insert_lines_report",
                "Insert lines:",
                "insertLines",
                ["app.py", "2", "new\\n"],
                {"path": "app.py", "line": "2", "content": "new\\n"},
                {"line": 2},
            ),
            (
                "--check-append",
                "vibeagent.cli.get_check_append_file_report",
                "Check append:",
                "checkAppend",
                ["app.py", "tail\\n"],
                {"path": "app.py", "content": "tail\\n"},
                {},
            ),
            (
                "--append",
                "vibeagent.cli.get_append_file_report",
                "Append:",
                "append",
                ["app.py", "tail\\n"],
                {"path": "app.py", "content": "tail\\n"},
                {},
            ),
        ]
        for flag, getter_target, title, payload_key, cli_args, expected_kwargs, report_extra in json_cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": "app.py",
                    "message": "ok",
                    "diff": {"text": "+new", "lines": ["+new"], "lineCount": 1},
                    **report_extra,
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_line_edit_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, *cli_args])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_write_file_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_write_file_text", return_value="Check write:\n  ok: yes") as get_check_write_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-write", "app.py", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check write:", stdout.getvalue())
        get_check_write_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", content="new\\n")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_write_file_text", return_value="Write:\n  ok: yes") as get_write_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--write", "app.py", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Write:", stdout.getvalue())
        get_write_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", content="new\\n")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-write",
                "vibeagent.cli.get_check_write_file_report",
                "Check write:",
                "checkWrite",
            ),
            (
                "--write",
                "vibeagent.cli.get_write_file_report",
                "Write:",
                "write",
            ),
        ]
        for flag, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": "app.py",
                    "message": "ok",
                    "diff": {"text": "+new", "lines": ["+new"], "lineCount": 1},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_line_edit_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, "app.py", "new\\n"])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path="app.py", content="new\\n")
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_check_write_local_flag_exits_nonzero_when_not_ok(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch(
                    "vibeagent.cli.get_check_write_file_text",
                    return_value="Check write:\n  ok: no\n  message: Path is protected",
                ),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-write", ".git/config", "new\\n"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Check write:", stdout.getvalue())
        self.assertIn("ok: no", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_runs_write_files_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_write_files_text", return_value="Check write files:\n  ok: yes") as get_check_write_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-write-files", "app.py", "a\\n", "test.py", "b\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check write files:", stdout.getvalue())
        get_check_write_files_text.assert_called_once_with(Path(base).resolve(), files=["app.py", "a\\n", "test.py", "b\\n"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_write_files_text", return_value="Write files:\n  ok: yes") as get_write_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--write-files", "app.py", "a\\n", "test.py", "b\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Write files:", stdout.getvalue())
        get_write_files_text.assert_called_once_with(Path(base).resolve(), files=["app.py", "a\\n", "test.py", "b\\n"])
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-write-files",
                "vibeagent.cli.get_check_write_files_report",
                "Check write files:",
                "checkWriteFiles",
            ),
            (
                "--write-files",
                "vibeagent.cli.get_write_files_report",
                "Write files:",
                "writeFiles",
            ),
        ]
        for flag, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "files": {
                        "total": 2,
                        "items": [
                            {"path": "app.py", "ok": True, "message": "ok", "diff": {"text": "+a", "lines": ["+a"], "lineCount": 1}},
                            {"path": "test.py", "ok": True, "message": "ok", "diff": {"text": "+b", "lines": ["+b"], "lineCount": 1}},
                        ],
                    },
                    "message": "ok",
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_write_files_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, "app.py", "a\\n", "test.py", "b\\n"])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), files=["app.py", "a\\n", "test.py", "b\\n"])
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_edit_file_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_edit_file_text", return_value="Check edit:\n  ok: yes") as get_check_edit_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-edit", "app.py", "old", "new"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check edit:", stdout.getvalue())
        get_check_edit_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", old="old", new="new")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_edit_file_text", return_value="Edit:\n  ok: yes") as get_edit_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--edit", "app.py", "old", "new"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Edit:", stdout.getvalue())
        get_edit_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", old="old", new="new")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-edit",
                "vibeagent.cli.get_check_edit_file_report",
                "Check edit:",
                "checkEdit",
            ),
            (
                "--edit",
                "vibeagent.cli.get_edit_file_report",
                "Edit:",
                "edit",
            ),
        ]
        for flag, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": "app.py",
                    "message": "ok",
                    "diff": {"text": "-old\n+new", "lines": ["-old", "+new"], "lineCount": 2},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_line_edit_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, "app.py", "old", "new"])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path="app.py", old="old", new="new")
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_multi_edit_file_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_multi_edit_file_text", return_value="Check multi edit:\n  ok: yes") as get_check_multi_edit_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-multi-edit", "app.py", "old", "new", "print", "log"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check multi edit:", stdout.getvalue())
        get_check_multi_edit_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", edits=["old", "new", "print", "log"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_multi_edit_file_text", return_value="Multi edit:\n  ok: yes") as get_multi_edit_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--multi-edit", "app.py", "old", "new", "print", "log"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Multi edit:", stdout.getvalue())
        get_multi_edit_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", edits=["old", "new", "print", "log"])
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-multi-edit",
                "vibeagent.cli.get_check_multi_edit_file_report",
                "Check multi edit:",
                "checkMultiEdit",
            ),
            (
                "--multi-edit",
                "vibeagent.cli.get_multi_edit_file_report",
                "Multi edit:",
                "multiEdit",
            ),
        ]
        for flag, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": "app.py",
                    "message": "ok",
                    "diff": {"text": "-old\n+new", "lines": ["-old", "+new"], "lineCount": 2},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_line_edit_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, "app.py", "old", "new", "print", "log"])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path="app.py", edits=["old", "new", "print", "log"])
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_delete_file_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_delete_file_text", return_value="Check delete:\n  ok: yes") as get_check_delete_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-delete", "old.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check delete:", stdout.getvalue())
        get_check_delete_file_text.assert_called_once_with(Path(base).resolve(), path="old.py")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_delete_file_text", return_value="Delete:\n  ok: yes") as get_delete_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--delete", "old.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Delete:", stdout.getvalue())
        get_delete_file_text.assert_called_once_with(Path(base).resolve(), path="old.py")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-delete",
                "vibeagent.cli.get_check_delete_file_report",
                "Check delete:",
                "checkDelete",
            ),
            (
                "--delete",
                "vibeagent.cli.get_delete_file_report",
                "Delete:",
                "delete",
            ),
        ]
        for flag, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": "old.py",
                    "message": "ok",
                    "diff": {"text": "-old", "lines": ["-old"], "lineCount": 1},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_line_edit_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, "old.py"])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path="old.py")
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_delete_files_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_delete_files_text", return_value="Check delete files:\n  ok: yes") as get_check_delete_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-delete-files", "old.py", "other.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check delete files:", stdout.getvalue())
        get_check_delete_files_text.assert_called_once_with(Path(base).resolve(), paths=["old.py", "other.py"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_delete_files_text", return_value="Delete files:\n  ok: yes") as get_delete_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--delete-files", "old.py", "other.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Delete files:", stdout.getvalue())
        get_delete_files_text.assert_called_once_with(Path(base).resolve(), paths=["old.py", "other.py"])
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-delete-files",
                "vibeagent.cli.get_check_delete_files_report",
                "Check delete files:",
                "checkDeleteFiles",
            ),
            (
                "--delete-files",
                "vibeagent.cli.get_delete_files_report",
                "Delete files:",
                "deleteFiles",
            ),
        ]
        for flag, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "paths": {"total": 2, "items": ["old.py", "other.py"]},
                    "message": "ok",
                    "diff": {"text": "-old", "lines": ["-old"], "lineCount": 1},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_path_list_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, "old.py", "other.py"])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), paths=["old.py", "other.py"])
                formatter.assert_called_once_with(title, report, include_diff=True)
                create_chat_client.assert_not_called()

    def test_main_runs_move_and_copy_file_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_move_file_text", return_value="Check move:\n  ok: yes") as get_check_move_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-move", "old.py", "new.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check move:", stdout.getvalue())
        get_check_move_file_text.assert_called_once_with(Path(base).resolve(), source="old.py", destination="new.py")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_move_file_text", return_value="Move:\n  ok: yes") as get_move_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--move", "old.py", "new.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Move:", stdout.getvalue())
        get_move_file_text.assert_called_once_with(Path(base).resolve(), source="old.py", destination="new.py")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_copy_file_text", return_value="Check copy:\n  ok: yes") as get_check_copy_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-copy", "template.py", "new.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check copy:", stdout.getvalue())
        get_check_copy_file_text.assert_called_once_with(Path(base).resolve(), source="template.py", destination="new.py")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_copy_file_text", return_value="Copy:\n  ok: yes") as get_copy_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--copy", "template.py", "new.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Copy:", stdout.getvalue())
        get_copy_file_text.assert_called_once_with(Path(base).resolve(), source="template.py", destination="new.py")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-move",
                "vibeagent.cli.get_check_move_file_report",
                "Check move:",
                "checkMove",
                ["old.py", "new.py"],
            ),
            (
                "--move",
                "vibeagent.cli.get_move_file_report",
                "Move:",
                "move",
                ["old.py", "new.py"],
            ),
            (
                "--check-copy",
                "vibeagent.cli.get_check_copy_file_report",
                "Check copy:",
                "checkCopy",
                ["template.py", "new.py"],
            ),
            (
                "--copy",
                "vibeagent.cli.get_copy_file_report",
                "Copy:",
                "copy",
                ["template.py", "new.py"],
            ),
        ]
        for flag, getter_target, title, payload_key, cli_args in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "source": cli_args[0],
                    "destination": cli_args[1],
                    "message": "ok",
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_file_transfer_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, *cli_args])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), source=cli_args[0], destination=cli_args[1])
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_move_and_copy_files_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_move_files_text", return_value="Check move files:\n  ok: yes") as get_check_move_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-move-files", "old.py", "new.py", "other.py", "other-new.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check move files:", stdout.getvalue())
        get_check_move_files_text.assert_called_once_with(Path(base).resolve(), transfers=["old.py", "new.py", "other.py", "other-new.py"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_move_files_text", return_value="Move files:\n  ok: yes") as get_move_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--move-files", "old.py", "new.py", "other.py", "other-new.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Move files:", stdout.getvalue())
        get_move_files_text.assert_called_once_with(Path(base).resolve(), transfers=["old.py", "new.py", "other.py", "other-new.py"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_copy_files_text", return_value="Check copy files:\n  ok: yes") as get_check_copy_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-copy-files", "template.py", "new.py", "config.py", "config-copy.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check copy files:", stdout.getvalue())
        get_check_copy_files_text.assert_called_once_with(Path(base).resolve(), transfers=["template.py", "new.py", "config.py", "config-copy.py"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_copy_files_text", return_value="Copy files:\n  ok: yes") as get_copy_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--copy-files", "template.py", "new.py", "config.py", "config-copy.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Copy files:", stdout.getvalue())
        get_copy_files_text.assert_called_once_with(Path(base).resolve(), transfers=["template.py", "new.py", "config.py", "config-copy.py"])
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-move-files",
                "vibeagent.cli.get_check_move_files_report",
                "Check move files:",
                "checkMoveFiles",
                ["old.py", "new.py", "other.py", "other-new.py"],
            ),
            (
                "--move-files",
                "vibeagent.cli.get_move_files_report",
                "Move files:",
                "moveFiles",
                ["old.py", "new.py", "other.py", "other-new.py"],
            ),
            (
                "--check-copy-files",
                "vibeagent.cli.get_check_copy_files_report",
                "Check copy files:",
                "checkCopyFiles",
                ["template.py", "new.py", "config.py", "config-copy.py"],
            ),
            (
                "--copy-files",
                "vibeagent.cli.get_copy_files_report",
                "Copy files:",
                "copyFiles",
                ["template.py", "new.py", "config.py", "config-copy.py"],
            ),
        ]
        for flag, getter_target, title, payload_key, cli_args in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "transfers": {
                        "total": 2,
                        "items": [
                            {"source": cli_args[0], "destination": cli_args[1]},
                            {"source": cli_args[2], "destination": cli_args[3]},
                        ],
                    },
                    "message": "ok",
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_file_transfer_list_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, *cli_args])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), transfers=cli_args)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_move_and_copy_dir_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_move_dir_text", return_value="Check move dir:\n  ok: yes") as get_check_move_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-move-dir", "old_pkg", "new_pkg"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check move dir:", stdout.getvalue())
        get_check_move_dir_text.assert_called_once_with(Path(base).resolve(), source="old_pkg", destination="new_pkg")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_move_dir_text", return_value="Move dir:\n  ok: yes") as get_move_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--move-dir", "old_pkg", "new_pkg"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Move dir:", stdout.getvalue())
        get_move_dir_text.assert_called_once_with(Path(base).resolve(), source="old_pkg", destination="new_pkg")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_copy_dir_text", return_value="Check copy dir:\n  ok: yes") as get_check_copy_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-copy-dir", "template_pkg", "copy_pkg"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check copy dir:", stdout.getvalue())
        get_check_copy_dir_text.assert_called_once_with(Path(base).resolve(), source="template_pkg", destination="copy_pkg")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_copy_dir_text", return_value="Copy dir:\n  ok: yes") as get_copy_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--copy-dir", "template_pkg", "copy_pkg"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Copy dir:", stdout.getvalue())
        get_copy_dir_text.assert_called_once_with(Path(base).resolve(), source="template_pkg", destination="copy_pkg")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-move-dir",
                "vibeagent.cli.get_check_move_dir_report",
                "Check move dir:",
                "checkMoveDir",
                ["old_pkg", "new_pkg"],
            ),
            (
                "--move-dir",
                "vibeagent.cli.get_move_dir_report",
                "Move dir:",
                "moveDir",
                ["old_pkg", "new_pkg"],
            ),
            (
                "--check-copy-dir",
                "vibeagent.cli.get_check_copy_dir_report",
                "Check copy dir:",
                "checkCopyDir",
                ["template_pkg", "copy_pkg"],
            ),
            (
                "--copy-dir",
                "vibeagent.cli.get_copy_dir_report",
                "Copy dir:",
                "copyDir",
                ["template_pkg", "copy_pkg"],
            ),
        ]
        for flag, getter_target, title, payload_key, cli_args in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "source": cli_args[0],
                    "destination": cli_args[1],
                    "message": "ok",
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_file_transfer_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, *cli_args])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), source=cli_args[0], destination=cli_args[1])
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_move_and_copy_dirs_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_move_dirs_text", return_value="Check move dirs:\n  ok: yes") as get_check_move_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-move-dirs", "old_a", "new_a", "old_b", "new_b"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check move dirs:", stdout.getvalue())
        get_check_move_dirs_text.assert_called_once_with(Path(base).resolve(), transfers=["old_a", "new_a", "old_b", "new_b"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_move_dirs_text", return_value="Move dirs:\n  ok: yes") as get_move_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--move-dirs", "old_a", "new_a", "old_b", "new_b"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Move dirs:", stdout.getvalue())
        get_move_dirs_text.assert_called_once_with(Path(base).resolve(), transfers=["old_a", "new_a", "old_b", "new_b"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_copy_dirs_text", return_value="Check copy dirs:\n  ok: yes") as get_check_copy_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-copy-dirs", "template_a", "copy_a", "template_b", "copy_b"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check copy dirs:", stdout.getvalue())
        get_check_copy_dirs_text.assert_called_once_with(Path(base).resolve(), transfers=["template_a", "copy_a", "template_b", "copy_b"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_copy_dirs_text", return_value="Copy dirs:\n  ok: yes") as get_copy_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--copy-dirs", "template_a", "copy_a", "template_b", "copy_b"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Copy dirs:", stdout.getvalue())
        get_copy_dirs_text.assert_called_once_with(Path(base).resolve(), transfers=["template_a", "copy_a", "template_b", "copy_b"])
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-move-dirs",
                "vibeagent.cli.get_check_move_dirs_report",
                "Check move dirs:",
                "checkMoveDirs",
                ["old_a", "new_a", "old_b", "new_b"],
            ),
            (
                "--move-dirs",
                "vibeagent.cli.get_move_dirs_report",
                "Move dirs:",
                "moveDirs",
                ["old_a", "new_a", "old_b", "new_b"],
            ),
            (
                "--check-copy-dirs",
                "vibeagent.cli.get_check_copy_dirs_report",
                "Check copy dirs:",
                "checkCopyDirs",
                ["template_a", "copy_a", "template_b", "copy_b"],
            ),
            (
                "--copy-dirs",
                "vibeagent.cli.get_copy_dirs_report",
                "Copy dirs:",
                "copyDirs",
                ["template_a", "copy_a", "template_b", "copy_b"],
            ),
        ]
        for flag, getter_target, title, payload_key, cli_args in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "transfers": {
                        "total": 2,
                        "items": [
                            {"source": cli_args[0], "destination": cli_args[1]},
                            {"source": cli_args[2], "destination": cli_args[3]},
                        ],
                    },
                    "message": "ok",
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_file_transfer_list_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, *cli_args])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), transfers=cli_args)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_directory_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_create_dir_text", return_value="Check mkdir:\n  ok: yes") as get_check_create_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-mkdir", "pkg/generated"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check mkdir:", stdout.getvalue())
        get_check_create_dir_text.assert_called_once_with(Path(base).resolve(), path="pkg/generated")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_create_dir_text", return_value="Mkdir:\n  ok: yes") as get_create_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--mkdir", "pkg/generated"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Mkdir:", stdout.getvalue())
        get_create_dir_text.assert_called_once_with(Path(base).resolve(), path="pkg/generated")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_delete_empty_dir_text", return_value="Check rmdir:\n  ok: yes") as get_check_delete_empty_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-rmdir", "pkg/generated"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check rmdir:", stdout.getvalue())
        get_check_delete_empty_dir_text.assert_called_once_with(Path(base).resolve(), path="pkg/generated")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_delete_empty_dir_text", return_value="Rmdir:\n  ok: yes") as get_delete_empty_dir_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--rmdir", "pkg/generated"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Rmdir:", stdout.getvalue())
        get_delete_empty_dir_text.assert_called_once_with(Path(base).resolve(), path="pkg/generated")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-mkdir",
                "vibeagent.cli.get_check_create_dir_report",
                "Check mkdir:",
                "checkCreateDir",
                "pkg/generated",
            ),
            (
                "--mkdir",
                "vibeagent.cli.get_create_dir_report",
                "Mkdir:",
                "createDir",
                "pkg/generated",
            ),
            (
                "--check-rmdir",
                "vibeagent.cli.get_check_delete_empty_dir_report",
                "Check rmdir:",
                "checkDeleteEmptyDir",
                "pkg/generated",
            ),
            (
                "--rmdir",
                "vibeagent.cli.get_delete_empty_dir_report",
                "Rmdir:",
                "deleteEmptyDir",
                "pkg/generated",
            ),
        ]
        for flag, getter_target, title, payload_key, cli_path in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": cli_path,
                    "message": "ok",
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_path_action_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, cli_path])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path=cli_path)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_batch_directory_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_create_dirs_text", return_value="Check mkdirs:\n  ok: yes") as get_check_create_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-mkdirs", "pkg/generated", "assets/icons"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check mkdirs:", stdout.getvalue())
        get_check_create_dirs_text.assert_called_once_with(Path(base).resolve(), paths=["pkg/generated", "assets/icons"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_create_dirs_text", return_value="Mkdirs:\n  ok: yes") as get_create_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--mkdirs", "pkg/generated", "assets/icons"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Mkdirs:", stdout.getvalue())
        get_create_dirs_text.assert_called_once_with(Path(base).resolve(), paths=["pkg/generated", "assets/icons"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_delete_empty_dirs_text", return_value="Check rmdirs:\n  ok: yes") as get_check_delete_empty_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-rmdirs", "pkg/generated", "assets/icons"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check rmdirs:", stdout.getvalue())
        get_check_delete_empty_dirs_text.assert_called_once_with(Path(base).resolve(), paths=["pkg/generated", "assets/icons"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_delete_empty_dirs_text", return_value="Rmdirs:\n  ok: yes") as get_delete_empty_dirs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--rmdirs", "pkg/generated", "assets/icons"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Rmdirs:", stdout.getvalue())
        get_delete_empty_dirs_text.assert_called_once_with(Path(base).resolve(), paths=["pkg/generated", "assets/icons"])
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-mkdirs",
                "vibeagent.cli.get_check_create_dirs_report",
                "Check mkdirs:",
                "checkCreateDirs",
            ),
            (
                "--mkdirs",
                "vibeagent.cli.get_create_dirs_report",
                "Mkdirs:",
                "createDirs",
            ),
            (
                "--check-rmdirs",
                "vibeagent.cli.get_check_delete_empty_dirs_report",
                "Check rmdirs:",
                "checkDeleteEmptyDirs",
            ),
            (
                "--rmdirs",
                "vibeagent.cli.get_delete_empty_dirs_report",
                "Rmdirs:",
                "deleteEmptyDirs",
            ),
        ]
        cli_paths = ["pkg/generated", "assets/icons"]
        for flag, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "paths": {"total": 2, "items": cli_paths},
                    "message": "ok",
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_path_list_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, *cli_paths])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), paths=cli_paths)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_executable_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_set_executable_text", return_value="Check executable:\n  ok: yes") as get_check_set_executable_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-executable", "tool.sh", "false"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check executable:", stdout.getvalue())
        get_check_set_executable_text.assert_called_once_with(Path(base).resolve(), path="tool.sh", executable="false")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_set_executable_text", return_value="Set executable:\n  ok: yes") as get_set_executable_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--set-executable", "tool.sh"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Set executable:", stdout.getvalue())
        get_set_executable_text.assert_called_once_with(Path(base).resolve(), path="tool.sh", executable=None)
        create_chat_client.assert_not_called()

        cases = [
            (
                ["--check-executable", "tool.sh", "false"],
                "vibeagent.cli.get_check_set_executable_report",
                "Check executable:",
                "checkSetExecutable",
                "false",
            ),
            (
                ["--set-executable", "tool.sh"],
                "vibeagent.cli.get_set_executable_report",
                "Set executable:",
                "setExecutable",
                None,
            ),
        ]
        for cli_args, getter_target, title, payload_key, expected_executable in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": "tool.sh",
                    "executable": expected_executable != "false",
                    "modeBefore": "-rw-r--r--",
                    "modeAfter": "-rwxr-xr-x",
                    "message": "ok",
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_executable_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *cli_args])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path="tool.sh", executable=expected_executable)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_patch_local_flags_without_creating_client(self) -> None:
        patch_text = "@@ -1 +1 @@\n-old\n+new\n"
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_patch_text", return_value="Check patch:\n  ok: yes") as get_check_patch_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-patch", "app.py", patch_text])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check patch:", stdout.getvalue())
        get_check_patch_text.assert_called_once_with(Path(base).resolve(), path="app.py", patch=patch_text)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_patch_text", return_value="Patch:\n  ok: yes") as get_patch_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--patch", "app.py", "-"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Patch:", stdout.getvalue())
        get_patch_text.assert_called_once_with(Path(base).resolve(), path="app.py", patch="-")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-patch",
                "vibeagent.cli.get_check_patch_report",
                "Check patch:",
                "checkPatch",
                patch_text,
            ),
            (
                "--patch",
                "vibeagent.cli.get_patch_report",
                "Patch:",
                "patch",
                "-",
            ),
        ]
        for flag, getter_target, title, payload_key, cli_patch in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": "app.py",
                    "message": "ok",
                    "diff": {"text": "+new\n", "lines": ["+new"], "lineCount": 1},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_patch_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, "app.py", cli_patch])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path="app.py", patch=cli_patch)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_patches_local_flags_without_creating_client(self) -> None:
        patch_text = "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new\n"
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_patches_text", return_value="Check patches:\n  ok: yes") as get_check_patches_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-patches", patch_text])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check patches:", stdout.getvalue())
        get_check_patches_text.assert_called_once_with(Path(base).resolve(), patch=patch_text)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_patches_text", return_value="Patches:\n  ok: yes") as get_patches_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--patches", "-"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Patches:", stdout.getvalue())
        get_patches_text.assert_called_once_with(Path(base).resolve(), patch="-")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-patches",
                "vibeagent.cli.get_check_patches_report",
                "Check patches:",
                "checkPatches",
                patch_text,
            ),
            (
                "--patches",
                "vibeagent.cli.get_patches_report",
                "Patches:",
                "patches",
                "-",
            ),
        ]
        for flag, getter_target, title, payload_key, cli_patch in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "files": {"total": 2, "items": ["app.py", "config.py"]},
                    "message": "ok",
                    "diff": {"text": "+new\n", "lines": ["+new"], "lineCount": 1},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_patches_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, cli_patch])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), patch=cli_patch)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_regex_replace_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_regex_replace_text", return_value="Check regex replace:\n  ok: yes") as get_check_regex_replace_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--check-regex-replace",
                        "app.py",
                        "old",
                        "new\\n",
                        "--regex-count",
                        "1",
                        "--regex-ignore-case",
                        "--regex-multiline",
                        "--regex-max-replacements",
                        "5",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Check regex replace:", stdout.getvalue())
        get_check_regex_replace_text.assert_called_once_with(
            Path(base).resolve(),
            path="app.py",
            pattern="old",
            replacement="new\\n",
            count=1,
            case_sensitive=False,
            multiline=True,
            max_replacements=5,
        )
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_regex_replace_text", return_value="Regex replace:\n  ok: yes") as get_regex_replace_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--regex-replace", "app.py", "old", "new"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Regex replace:", stdout.getvalue())
        get_regex_replace_text.assert_called_once_with(
            Path(base).resolve(),
            path="app.py",
            pattern="old",
            replacement="new",
            count=0,
            case_sensitive=True,
            multiline=False,
            max_replacements=100,
        )
        create_chat_client.assert_not_called()

        cases = [
            (
                [
                    "--check-regex-replace",
                    "app.py",
                    "old",
                    "new\\n",
                    "--regex-count",
                    "1",
                    "--regex-ignore-case",
                    "--regex-multiline",
                    "--regex-max-replacements",
                    "5",
                ],
                "vibeagent.cli.get_check_regex_replace_report",
                "Check regex replace:",
                "checkRegexReplace",
                {
                    "path": "app.py",
                    "pattern": "old",
                    "replacement": "new\\n",
                    "count": 1,
                    "case_sensitive": False,
                    "multiline": True,
                    "max_replacements": 5,
                },
            ),
            (
                ["--regex-replace", "app.py", "old", "new"],
                "vibeagent.cli.get_regex_replace_report",
                "Regex replace:",
                "regexReplace",
                {
                    "path": "app.py",
                    "pattern": "old",
                    "replacement": "new",
                    "count": 0,
                    "case_sensitive": True,
                    "multiline": False,
                    "max_replacements": 100,
                },
            ),
        ]
        for cli_args, getter_target, title, payload_key, expected_kwargs in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": expected_kwargs["path"],
                    "pattern": expected_kwargs["pattern"],
                    "replacement": expected_kwargs["replacement"],
                    "count": expected_kwargs["count"],
                    "caseSensitive": expected_kwargs["case_sensitive"],
                    "multiline": expected_kwargs["multiline"],
                    "maxReplacements": expected_kwargs["max_replacements"],
                    "replacements": 1,
                    "message": "ok",
                    "diff": {"text": "+new\n", "lines": ["+new"], "lineCount": 1},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_regex_replace_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *cli_args])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_code_deps_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_code_deps_text", return_value="Code dependencies:\n  files: 1/1") as get_code_deps_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--code-deps", "web"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Code dependencies:", stdout.getvalue())
        get_code_deps_text.assert_called_once_with(Path(base).resolve(), "web")
        create_chat_client.assert_not_called()

    def test_main_runs_code_refs_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_code_refs_text", return_value="Code references:\n  references: 1/1") as get_code_refs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--code-refs", "runAgent", "--code-path", "web"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Code references:", stdout.getvalue())
        get_code_refs_text.assert_called_once_with(Path(base).resolve(), symbol="runAgent", path="web")
        create_chat_client.assert_not_called()

    def test_main_runs_code_ref_contexts_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_code_ref_contexts_text", return_value="Code reference contexts:\n  contexts: 1/1") as get_code_ref_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--code-ref-contexts", "runAgent", "--code-path", "web"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Code reference contexts:", stdout.getvalue())
        get_code_ref_contexts_text.assert_called_once_with(Path(base).resolve(), symbol="runAgent", path="web")
        create_chat_client.assert_not_called()

    def test_main_runs_code_defs_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_code_defs_text", return_value="Code definitions:\n  definitions: 1/1") as get_code_defs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--code-defs", "runAgent", "--code-path", "web"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Code definitions:", stdout.getvalue())
        get_code_defs_text.assert_called_once_with(Path(base).resolve(), symbol="runAgent", path="web")
        create_chat_client.assert_not_called()

    def test_main_runs_code_intelligence_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--code-deps", "web"],
                "vibeagent.cli.get_code_deps_report",
                "vibeagent.cli.format_code_deps_report_text",
                "codeDependencies",
                (Path, "web"),
                {},
            ),
            (
                ["--code-refs", "runAgent", "--code-path", "web", "--code-max-matches", "4"],
                "vibeagent.cli.get_code_refs_report",
                "vibeagent.cli.format_code_refs_report_text",
                "codeReferences",
                (Path,),
                {"symbol": "runAgent", "path": "web", "max_matches": 4},
            ),
            (
                [
                    "--code-ref-contexts",
                    "runAgent",
                    "--code-path",
                    "web",
                    "--code-max-matches",
                    "5",
                    "--code-context-lines",
                    "1",
                    "--code-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_code_ref_contexts_report",
                "vibeagent.cli.format_code_ref_contexts_report_text",
                "codeReferenceContexts",
                (Path,),
                {"symbol": "runAgent", "path": "web", "max_matches": 5, "context_lines": 1, "max_bytes_per_context": 1000},
            ),
            (
                ["--code-defs", "runAgent", "--code-path", "web", "--code-max-matches", "6", "--code-def-max-lines", "40"],
                "vibeagent.cli.get_code_defs_report",
                "vibeagent.cli.format_code_defs_report_text",
                "codeDefinitions",
                (Path,),
                {"symbol": "runAgent", "path": "web", "max_matches": 6, "max_lines": 40},
            ),
        ]

        for argv_tail, getter_target, formatter_target, payload_key, expected_args, expected_kwargs in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{payload_key}: ok"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch(formatter_target, return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(*resolved_args, **expected_kwargs)
                formatter.assert_called_once_with(report)
                create_chat_client.assert_not_called()

    def test_main_runs_code_symbol_local_flags_with_bounds(self) -> None:
        cases = [
            (
                ["--code-refs", "runAgent", "--code-path", "web", "--code-max-matches", "4"],
                "vibeagent.cli.get_code_refs_text",
                "Code references:\n  references: 1/1",
                {"symbol": "runAgent", "path": "web", "max_matches": 4},
            ),
            (
                [
                    "--code-ref-contexts",
                    "runAgent",
                    "--code-path",
                    "web",
                    "--code-max-matches",
                    "5",
                    "--code-context-lines",
                    "1",
                    "--code-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_code_ref_contexts_text",
                "Code reference contexts:\n  contexts: 1/1",
                {"symbol": "runAgent", "path": "web", "max_matches": 5, "context_lines": 1, "max_bytes_per_context": 1000},
            ),
            (
                ["--code-defs", "runAgent", "--code-path", "web", "--code-max-matches", "6", "--code-def-max-lines", "40"],
                "vibeagent.cli.get_code_defs_text",
                "Code definitions:\n  definitions: 1/1",
                {"symbol": "runAgent", "path": "web", "max_matches": 6, "max_lines": 40},
            ),
        ]

        for argv_tail, patch_target, text, expected_kwargs in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_rejects_code_symbol_bounds_without_matching_local_flag(self) -> None:
        cases = [
            (
                ["--code-max-matches", "3"],
                "--code-max-matches can only be used with --code-refs, --code-ref-contexts, or --code-defs.",
            ),
            (
                ["--code-def-max-lines", "40"],
                "--code-def-max-lines can only be used with --code-defs.",
            ),
            (
                ["--code-refs", "runAgent", "--code-def-max-lines", "40"],
                "--code-def-max-lines can only be used with --code-defs.",
            ),
            (
                ["--code-context-lines", "1"],
                "--code-context-lines can only be used with --code-ref-contexts.",
            ),
            (
                ["--code-refs", "runAgent", "--code-context-lines", "1"],
                "--code-context-lines can only be used with --code-ref-contexts.",
            ),
            (
                ["--code-context-max-bytes", "1000"],
                "--code-context-max-bytes can only be used with --code-ref-contexts.",
            ),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), f"{expected}\n")
                create_chat_client.assert_not_called()

    def test_main_runs_code_rename_preview_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_code_rename_preview_text", return_value="Code rename preview:\n  replacements: 1") as get_code_rename_preview_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--code-rename-preview", "runAgent", "executeAgent", "--code-path", "web"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Code rename preview:", stdout.getvalue())
        get_code_rename_preview_text.assert_called_once_with(Path(base).resolve(), symbol="runAgent", new_name="executeAgent", path="web")
        create_chat_client.assert_not_called()

    def test_main_runs_code_rename_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_code_rename_text", return_value="Code rename:\n  replacements: 1") as get_code_rename_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--code-rename", "runAgent", "executeAgent", "--code-path", "web"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Code rename:", stdout.getvalue())
        get_code_rename_text.assert_called_once_with(Path(base).resolve(), symbol="runAgent", new_name="executeAgent", path="web")
        create_chat_client.assert_not_called()

    def test_main_runs_code_rename_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--code-rename-preview", "runAgent", "executeAgent", "--code-path", "web"],
                "vibeagent.cli.get_code_rename_preview_report",
                "Code rename preview:",
                "codeRenamePreview",
            ),
            (
                ["--code-rename", "runAgent", "executeAgent", "--code-path", "web"],
                "vibeagent.cli.get_code_rename_report",
                "Code rename:",
                "codeRename",
            ),
        ]

        for argv_tail, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{payload_key}: ok"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_code_rename_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(Path(base).resolve(), symbol="runAgent", new_name="executeAgent", path="web")
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_git_info_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_git_status_text", return_value="Git status:\n  ok: yes") as get_git_status_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-status"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Git status:", stdout.getvalue())
        get_git_status_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_git_conflicts_text", return_value="Git conflicts:\n  ok: yes") as get_git_conflicts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--conflicts", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Git conflicts:", stdout.getvalue())
        get_git_conflicts_text.assert_called_once_with(Path(base).resolve(), "src")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "path": "src",
                "unmerged": {"shown": 1, "total": 1, "items": [{"status": "UU", "path": "src/app.py"}]},
                "markers": {"shown": 1, "total": 1, "items": [{"path": "src/app.py", "line": 1, "marker": "<<<<<<<", "text": "<<<<<<< HEAD"}]},
                "scannedFiles": 1,
                "totalFiles": 1,
                "truncated": False,
                "message": "Found conflicts.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_git_conflicts_report", return_value=report) as get_git_conflicts_report,
                patch("vibeagent.cli.format_git_conflicts_report_text", return_value="Git conflicts:\n  ok: yes") as formatter,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--conflicts", "src"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["gitConflicts"], report)
        self.assertIn("Git conflicts:", payload["text"])
        get_git_conflicts_report.assert_called_once_with(Path(base).resolve(), "src")
        formatter.assert_called_once_with(report)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_git_info_text", return_value="Git info:\n  branch: main") as get_git_info_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-info"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Git info:", stdout.getvalue())
        get_git_info_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_branches_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_branches_text", return_value="Branches:\n  current: main") as get_branches_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--branches"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Branches:", stdout.getvalue())
        get_branches_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_log_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_log_text", return_value="Log:\n  ok: yes") as get_log_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--log", "app.py", "--log-count", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Log:", stdout.getvalue())
        get_log_text.assert_called_once_with(Path(base).resolve(), "app.py", 2)
        create_chat_client.assert_not_called()

    def test_main_runs_show_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_show_text", return_value="Show:\n  ok: yes") as get_show_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--show", "HEAD", "--show-path", "app.py", "--show-max-chars", "2000"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Show:", stdout.getvalue())
        get_show_text.assert_called_once_with(Path(base).resolve(), rev="HEAD", path="app.py", max_output_chars=2000)
        create_chat_client.assert_not_called()

    def test_main_runs_blame_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_blame_text", return_value="Blame:\n  ok: yes") as get_blame_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--blame", "app.py", "--blame-lines", "2:4", "--blame-max-chars", "2000"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Blame:", stdout.getvalue())
        get_blame_text.assert_called_once_with(Path(base).resolve(), "app.py", "2:4", 2000)
        create_chat_client.assert_not_called()

    def test_main_runs_stashes_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stashes_text", return_value="Stashes:\n  entries: 1/1") as get_stashes_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--stashes", "--stash-count", "3"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Stashes:", stdout.getvalue())
        get_stashes_text.assert_called_once_with(Path(base).resolve(), max_entries=3)
        create_chat_client.assert_not_called()

    def test_main_read_only_git_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            subprocess.run(["git", "init", "--initial-branch", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("alpha\nbeta\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial app"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("alpha\nbeta changed\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "update beta"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "branch", "feature/work"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "app.py").write_text("alpha\nbeta stashed\n", encoding="utf-8")
            subprocess.run(["git", "stash", "push", "-m", "save local app"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (root / "notes.txt").write_text("local note\n", encoding="utf-8")

            def run_json(*argv: str) -> tuple[int, dict[str, object]]:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(["--json", "--cwd", base, *argv])
                return exit_code, json.loads(stdout.getvalue())

            with patch("vibeagent.cli.create_chat_client") as create_chat_client:
                status_exit, status_payload = run_json("--git-status")
                info_exit, info_payload = run_json("--git-info")
                branches_exit, branches_payload = run_json("--branches")
                log_exit, log_payload = run_json("--log", "app.py", "--log-count", "2")
                show_exit, show_payload = run_json("--show", "HEAD", "--show-path", "app.py")
                blame_exit, blame_payload = run_json("--blame", "app.py", "--blame-lines", "2:2")
                stashes_exit, stashes_payload = run_json("--stashes", "--stash-count", "1")

        self.assertEqual(status_exit, 0)
        self.assertIn("gitStatus", status_payload)
        self.assertEqual(status_payload["gitStatus"]["status"]["count"], 1)
        self.assertIn("?? notes.txt", status_payload["gitStatus"]["status"]["lines"])
        self.assertEqual(info_exit, 0)
        self.assertEqual(info_payload["gitInfo"]["branch"], "main")
        self.assertEqual(info_payload["gitInfo"]["status"]["count"], 1)
        self.assertEqual(branches_exit, 0)
        self.assertEqual(branches_payload["branches"]["branches"]["shown"], 2)
        self.assertEqual(log_exit, 0)
        self.assertEqual(log_payload["log"]["commits"]["shown"], 2)
        self.assertIn("update beta", log_payload["log"]["commits"]["items"][0]["subject"])
        self.assertEqual(show_exit, 0)
        self.assertIn("+beta changed", show_payload["show"]["output"]["text"])
        self.assertEqual(blame_exit, 0)
        self.assertIn("beta changed", blame_payload["blame"]["output"]["text"])
        self.assertEqual(stashes_exit, 0)
        self.assertEqual(stashes_payload["stashes"]["entries"]["items"][0]["name"], "stash@{0}")
        create_chat_client.assert_not_called()

    def test_main_read_only_git_local_flags_exit_nonzero_for_failed_results(self) -> None:
        cases = [
            (["--git-status"], "vibeagent.cli.get_git_status_text", "Git status:\n  ok: no", (Path,), {}),
            (["--conflicts", "src"], "vibeagent.cli.get_git_conflicts_text", "Git conflicts:\n  ok: no", (Path, "src"), {}),
            (["--git-info"], "vibeagent.cli.get_git_info_text", "Git info:\n  ok: no", (Path,), {}),
            (["--branches"], "vibeagent.cli.get_branches_text", "Branches:\n  ok: no", (Path,), {}),
            (["--log", "app.py", "--log-count", "2"], "vibeagent.cli.get_log_text", "Log:\n  ok: no", (Path, "app.py", 2), {}),
            (
                ["--show", "badrev", "--show-path", "app.py", "--show-max-chars", "2000"],
                "vibeagent.cli.get_show_text",
                "Show:\n  ok: no",
                (Path,),
                {"rev": "badrev", "path": "app.py", "max_output_chars": 2000},
            ),
            (["--blame", "missing.py", "--blame-lines", "2:4", "--blame-max-chars", "2000"], "vibeagent.cli.get_blame_text", "Blame:\n  ok: no", (Path, "missing.py", "2:4", 2000), {}),
            (["--stashes", "--stash-count", "3"], "vibeagent.cli.get_stashes_text", "Stashes:\n  ok: no", (Path,), {"max_entries": 3}),
            (["--diff"], "vibeagent.cli.get_diff_text", "Diff:\n  error: git diff failed", (Path, None), {"max_chars": 12000}),
            (
                ["--diff-hunks"],
                "vibeagent.cli.get_diff_hunks_text",
                "Diff hunks:\n  ok: no",
                (Path, None),
                {"max_hunks": 80, "max_lines_per_hunk": 80},
            ),
            (
                ["--diff-contexts"],
                "vibeagent.cli.get_diff_contexts_text",
                "Diff contexts:\n  ok: no",
                (Path, None),
                {"context_lines": 5, "max_hunks": 80, "max_bytes_per_context": 20000},
            ),
        ]

        for argv_tail, patch_target, text, expected_args, expected_kwargs in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
            getter.assert_called_once_with(*resolved_args, **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_changes_local_flag_exit_nonzero_for_failed_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "changedFiles": {"shown": 0, "total": 0, "truncated": False, "files": []},
                "counts": {"staged": 0, "unstaged": 0, "untracked": 0, "binary": 0, "insertions": 0, "deletions": 0},
                "message": "git status failed",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_changes_report", return_value=report) as get_changes_report,
                patch("vibeagent.cli.format_changes_report_text", return_value="Changes:\n  ok: no") as format_changes_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--changes"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "Changes:\n  ok: no\n")
        get_changes_report.assert_called_once_with(Path(base).resolve(), max_files=200)
        format_changes_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_read_only_git_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "rev": "badrev",
                "path": ".",
                "output": {"text": "", "chars": 0, "lines": 0, "truncated": False, "maxOutputChars": 12000},
                "message": "git show failed.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_show_report", return_value=report) as get_show_report,
                patch("vibeagent.cli.format_show_report_text", return_value="Show:\n  ok: no") as format_show_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--show", "badrev"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Show:\n  ok: no")
        self.assertEqual(payload["show"], report)
        get_show_report.assert_called_once_with(Path(base).resolve(), rev="badrev", path=None, max_output_chars=12000)
        format_show_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_env_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_env_text", return_value="Environment:\n  tools: 3/9") as get_env_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--env"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Environment:", stdout.getvalue())
        get_env_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_env_local_flag_as_json_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "platform": "linux",
                "pythonVersion": "3.11",
                "pythonExecutable": "/usr/bin/python3",
                "gitRepo": False,
                "tools": {"available": 2, "total": 2, "items": []},
                "message": "Environment inspected.",
            }
            rendered = "Environment:\n  tools: 2/2"

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_env_report", return_value=report) as get_env_report,
                patch("vibeagent.cli.format_env_report_text", return_value=rendered) as format_env_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--env"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["text"], rendered)
        self.assertEqual(payload["env"], report)
        get_env_report.assert_called_once_with(Path(base).resolve())
        format_env_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_processes_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_processes_text", return_value="Processes:\n  processes: 0") as get_processes_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--processes"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Processes:", stdout.getvalue())
        get_processes_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_processes_local_flag_exits_nonzero_for_failed_process_state(self) -> None:
        cases = [
            ("Processes:\n  processes: 1\n  running: 0\n  items:\n    - bg-1: pid=123; status=exited(7); cwd=.; command=pytest", 1),
            ("Processes:\n  processes: 1\n  running: 0\n  items:\n    - bg-1: pid=123; status=signaled(SIGTERM); cwd=.; command=server", 1),
            ("Processes:\n  processes: 1\n  running: 0\n  items:\n    - bg-1: pid=123; status=exited(0); cwd=.; command=pytest", 0),
            ("Processes:\n  processes: 1\n  running: 1\n  items:\n    - bg-1: pid=123; status=running; cwd=.; command=server", 0),
        ]

        for text, expected_exit_code in cases:
            with self.subTest(text=text), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch("vibeagent.cli.get_processes_text", return_value=text),
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, "--processes"])

            self.assertEqual(exit_code, expected_exit_code)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            create_chat_client.assert_not_called()

    def test_main_processes_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "processes": {
                    "total": 1,
                    "running": 1,
                    "items": [
                        {
                            "processId": "bg-1",
                            "pid": 1234,
                            "command": "npm run dev",
                            "cwd": ".",
                            "running": True,
                            "exitCode": None,
                            "signal": None,
                            "status": "running",
                        }
                    ],
                },
                "message": "Found 1 background process(es).",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_processes_report", return_value=report) as get_processes_report,
                patch("vibeagent.cli.format_processes_report_text", return_value="Processes:\n  processes: 1\n  running: 1") as format_processes_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--processes"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["processes"], report)
        get_processes_report.assert_called_once_with(Path(base).resolve())
        format_processes_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_process_output_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_text", return_value="Process:\n  ok: no") as get_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--process-output", "bg-1", "--process-max-chars", "2000"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Process:", stdout.getvalue())
        get_process_text.assert_called_once_with(Path(base).resolve(), process_id="bg-1", max_output_chars=2000)
        create_chat_client.assert_not_called()

    def test_main_process_output_local_flag_exits_nonzero_for_failed_process_state(self) -> None:
        cases = [
            ("Process:\n  ok: yes\n  status: exited(7)", 1),
            ("Process:\n  ok: yes\n  status: signaled(SIGTERM)", 1),
            ("Process:\n  ok: yes\n  status: exited(0)", 0),
            ("Process:\n  ok: yes\n  status: running", 0),
        ]

        for text, expected_exit_code in cases:
            with self.subTest(text=text), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch("vibeagent.cli.get_process_text", return_value=text),
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, "--process-output", "bg-1"])

            self.assertEqual(exit_code, expected_exit_code)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            create_chat_client.assert_not_called()

    def test_main_process_output_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 1234,
                "status": "running",
                "running": True,
                "exitCode": None,
                "signal": None,
                "maxOutputChars": 2000,
                "stdout": "ready\n",
                "stderr": "",
                "analysis": {"diagnostics": {"shown": 0, "total": 0, "items": []}, "diagnosticsTruncated": False, "contexts": {"shown": 0, "totalRefs": 0, "items": []}, "contextsTruncated": False},
                "message": "Process bg-1 is running.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_report", return_value=report) as get_process_report,
                patch("vibeagent.cli.format_process_report_text", return_value="Process:\n  ok: yes\n  status: running") as format_process_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--process-output", "bg-1", "--process-max-chars", "2000"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["process"], report)
        get_process_report.assert_called_once_with(Path(base).resolve(), process_id="bg-1", max_output_chars=2000)
        format_process_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_process_output_contexts_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_output_contexts_text", return_value="Process output contexts:\n  contexts: 1/1") as get_process_output_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--process-output-contexts",
                        "bg-1",
                        "--process-max-chars",
                        "2000",
                        "--process-output-context-lines",
                        "2",
                        "--process-output-context-max",
                        "5",
                        "--process-output-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Process output contexts:", stdout.getvalue())
        get_process_output_contexts_text.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            max_output_chars=2000,
            context_lines=2,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_process_output_diagnostics_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_output_diagnostics_text", return_value="Process output diagnostics:\n  diagnostics: 1/1") as get_process_output_diagnostics_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--process-output-diagnostics",
                        "bg-1",
                        "--process-max-chars",
                        "2000",
                        "--process-output-context-lines",
                        "2",
                        "--process-output-diagnostic-max",
                        "7",
                        "--process-output-context-max",
                        "5",
                        "--process-output-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Process output diagnostics:", stdout.getvalue())
        get_process_output_diagnostics_text.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            max_output_chars=2000,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_process_output_analysis_local_flags_exit_nonzero_for_failed_results(self) -> None:
        cases = [
            (
                [
                    "--process-output-contexts",
                    "missing-proc",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_contexts_text",
                "Process output contexts:\n  ok: no\n  message: Unknown background process id.",
            ),
            (
                [
                    "--process-output-diagnostics",
                    "bg-1",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_diagnostics_text",
                "Process output diagnostics:\n  diagnostics: 1/1\n  contexts: 0/1",
            ),
        ]

        for argv_tail, patch_target, text in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            expected_kwargs = {
                "process_id": argv_tail[1],
                "max_output_chars": 2000,
                "context_lines": 2,
                "max_contexts": 5,
                "max_bytes_per_context": 1000,
            }
            if "diagnostics" in patch_target:
                expected_kwargs["max_diagnostics"] = 50
            getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_process_output_analysis_local_flags_exit_nonzero_for_failed_process_state(self) -> None:
        cases = [
            (
                [
                    "--process-output-contexts",
                    "bg-1",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_contexts_text",
                "Process output contexts:\n  ok: yes\n  status: exited(7)\n  contexts: 1/1",
                1,
            ),
            (
                [
                    "--process-output-diagnostics",
                    "bg-1",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_diagnostics_text",
                "Process output diagnostics:\n  ok: yes\n  status: signaled(SIGTERM)\n  diagnostics: 1/1\n  contexts: 1/1",
                1,
            ),
            (
                [
                    "--process-output-contexts",
                    "bg-1",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_contexts_text",
                "Process output contexts:\n  ok: yes\n  status: exited(0)\n  contexts: 1/1",
                0,
            ),
            (
                [
                    "--process-output-diagnostics",
                    "bg-1",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_diagnostics_text",
                "Process output diagnostics:\n  ok: yes\n  status: running\n  diagnostics: 1/1\n  contexts: 1/1",
                0,
            ),
        ]

        for argv_tail, patch_target, text, expected_exit_code in cases:
            with self.subTest(argv=argv_tail, text=text), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, expected_exit_code)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            expected_kwargs = {
                "process_id": "bg-1",
                "max_output_chars": 2000,
                "context_lines": 2,
                "max_contexts": 5,
                "max_bytes_per_context": 1000,
            }
            if "diagnostics" in patch_target:
                expected_kwargs["max_diagnostics"] = 50
            getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_process_output_analysis_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            contexts_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 1234,
                "status": "running",
                "contexts": {"ok": 1, "total": 1, "items": [{"path": "src/app.py", "line": 2, "content": "2: print('ok')"}]},
                "totalRefs": 1,
                "maxOutputChars": 2000,
                "stdoutChars": 24,
                "stderrChars": 0,
                "truncated": False,
                "message": "Extracted 1/1 output context(s) from process bg-1.",
            }
            diagnostics_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 1234,
                "status": "running",
                "diagnostics": {"shown": 1, "total": 1, "items": [{"severity": "error", "outputLine": 1, "path": "src/app.py"}]},
                "contexts": {"ok": 1, "total": 1, "items": [{"path": "src/app.py", "line": 2, "content": "2: print('ok')"}]},
                "totalRefs": 1,
                "maxOutputChars": 2000,
                "stdoutChars": 32,
                "stderrChars": 0,
                "contextLines": 2,
                "maxDiagnostics": 7,
                "maxContexts": 5,
                "maxBytesPerContext": 1000,
                "diagnosticsTruncated": False,
                "contextsTruncated": False,
                "message": "Extracted 1/1 diagnostic(s) and 1/1 source context(s) from process bg-1.",
            }
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_output_contexts_report", return_value=contexts_report) as get_contexts_report,
                patch(
                    "vibeagent.cli.format_process_output_contexts_report_text",
                    return_value="Process output contexts:\n  contexts: 1/1",
                ) as format_contexts_report,
                redirect_stdout(stdout),
            ):
                contexts_exit = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--process-output-contexts",
                        "bg-1",
                        "--process-max-chars",
                        "2000",
                        "--process-output-context-lines",
                        "2",
                        "--process-output-context-max",
                        "5",
                        "--process-output-context-max-bytes",
                        "1000",
                    ]
                )
            contexts_payload = json.loads(stdout.getvalue())
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client_diagnostics,
                patch("vibeagent.cli.get_process_output_diagnostics_report", return_value=diagnostics_report) as get_diagnostics_report,
                patch(
                    "vibeagent.cli.format_process_output_diagnostics_report_text",
                    return_value="Process output diagnostics:\n  diagnostics: 1/1\n  contexts: 1/1",
                ) as format_diagnostics_report,
                redirect_stdout(stdout),
            ):
                diagnostics_exit = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--process-output-diagnostics",
                        "bg-1",
                        "--process-max-chars",
                        "2000",
                        "--process-output-context-lines",
                        "2",
                        "--process-output-diagnostic-max",
                        "7",
                        "--process-output-context-max",
                        "5",
                        "--process-output-context-max-bytes",
                        "1000",
                    ]
                )
            diagnostics_payload = json.loads(stdout.getvalue())

        self.assertEqual(contexts_exit, 0)
        self.assertEqual(contexts_payload["processOutputContexts"], contexts_report)
        get_contexts_report.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            max_output_chars=2000,
            context_lines=2,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        format_contexts_report.assert_called_once_with(contexts_report)
        create_chat_client.assert_not_called()
        self.assertEqual(diagnostics_exit, 0)
        self.assertEqual(diagnostics_payload["processOutputDiagnostics"], diagnostics_report)
        get_diagnostics_report.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            max_output_chars=2000,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        format_diagnostics_report.assert_called_once_with(diagnostics_report)
        create_chat_client_diagnostics.assert_not_called()

    def test_main_process_output_analysis_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "processId": "missing-proc",
                "pid": None,
                "status": "unknown",
                "contexts": {"ok": 0, "total": 0, "items": []},
                "totalRefs": 0,
                "maxOutputChars": 4000,
                "stdoutChars": 0,
                "stderrChars": 0,
                "truncated": False,
                "message": "Unknown background process id.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_output_contexts_report", return_value=report) as get_process_output_contexts_report,
                patch(
                    "vibeagent.cli.format_process_output_contexts_report_text",
                    return_value="Process output contexts:\n  ok: no",
                ) as format_process_output_contexts_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--process-output-contexts", "missing-proc"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Process output contexts:\n  ok: no")
        self.assertEqual(payload["processOutputContexts"], report)
        get_process_output_contexts_report.assert_called_once_with(
            Path(base).resolve(),
            process_id="missing-proc",
            max_output_chars=4000,
            context_lines=5,
            max_contexts=20,
            max_bytes_per_context=20000,
        )
        format_process_output_contexts_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_runs_wait_process_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_wait_process_text", return_value="Wait process:\n  ok: no") as get_wait_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--wait-process",
                        "bg-1",
                        "--wait-timeout-ms",
                        "2000",
                        "--wait-max-chars",
                        "3000",
                        "--wait-stdout",
                        "ready",
                        "--wait-regex",
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertIn("Wait process:", stdout.getvalue())
        get_wait_process_text.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            timeout_ms=2000,
            max_output_chars=3000,
            stdout_contains="ready",
            stderr_contains=None,
            regex=True,
        )
        create_chat_client.assert_not_called()

    def test_main_wait_process_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 1234,
                "status": "running",
                "running": True,
                "timedOut": False,
                "matched": True,
                "matchedStream": "stdout",
                "matchedPattern": "ready",
                "timeoutMs": 5000,
                "exitCode": None,
                "signal": None,
                "maxOutputChars": 2000,
                "stdout": "ready\n",
                "stderr": "",
                "analysis": {"diagnostics": {"shown": 0, "total": 0, "items": []}, "diagnosticsTruncated": False, "contexts": {"shown": 0, "totalRefs": 0, "items": []}, "contextsTruncated": False},
                "message": "Matched stdout pattern.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_wait_process_report", return_value=report) as get_wait_process_report,
                patch("vibeagent.cli.format_wait_process_report_text", return_value="Wait process:\n  matched: yes") as format_wait_process_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--wait-process",
                        "bg-1",
                        "--wait-timeout-ms",
                        "5000",
                        "--wait-max-chars",
                        "2000",
                        "--wait-stdout",
                        "ready",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["waitProcess"], report)
        get_wait_process_report.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            timeout_ms=5000,
            max_output_chars=2000,
            stdout_contains="ready",
            stderr_contains=None,
            regex=False,
        )
        format_wait_process_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_wait_process_local_flag_exits_nonzero_for_failed_process_state(self) -> None:
        cases = [
            ("Wait process:\n  ok: yes\n  status: exited(7)\n  timedOut: no", 1),
            ("Wait process:\n  ok: yes\n  status: running\n  timedOut: yes", 1),
            ("Wait process:\n  ok: yes\n  status: signaled(SIGTERM)\n  timedOut: no", 1),
            ("Wait process:\n  ok: yes\n  status: exited(0)\n  timedOut: no", 0),
        ]

        for text, expected_exit_code in cases:
            with self.subTest(text=text), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch("vibeagent.cli.get_wait_process_text", return_value=text),
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, "--wait-process", "bg-1"])

            self.assertEqual(exit_code, expected_exit_code)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            create_chat_client.assert_not_called()

    def test_main_runs_write_process_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_write_process_text", return_value="Write process:\n  ok: no") as get_write_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--write-process", "bg-1", "--write-stdin", "hello\\n"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Write process:", stdout.getvalue())
        get_write_process_text.assert_called_once_with(Path(base).resolve(), process_id="bg-1", content="hello\\n")
        create_chat_client.assert_not_called()

    def test_main_runs_check_write_process_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_write_process_text", return_value="Check write process:\n  ok: yes") as get_check_write_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-write-process", "bg-1", "--write-stdin", "hello\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check write process:", stdout.getvalue())
        get_check_write_process_text.assert_called_once_with(Path(base).resolve(), process_id="bg-1", content="hello\\n")
        create_chat_client.assert_not_called()

    def test_main_write_process_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            check_stdout = io.StringIO()
            check_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 123,
                "running": True,
                "command": "python3 repl.py",
                "cwd": ".",
                "contentChars": 6,
                "message": "Can write 6 character(s) to process bg-1.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_write_process_report", return_value=check_report) as get_check_write_process_report,
                patch("vibeagent.cli.format_check_write_process_report_text", return_value="Check write process:\n  ok: yes") as format_check_write_process_report,
                redirect_stdout(check_stdout),
            ):
                check_exit = main(["--json", "--cwd", base, "--check-write-process", "bg-1", "--write-stdin", "hello\\n"])

            write_stdout = io.StringIO()
            write_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "processId": "missing",
                "pid": None,
                "running": False,
                "command": "",
                "cwd": "",
                "contentChars": 6,
                "message": "Unknown background process id.",
            }
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client_write,
                patch("vibeagent.cli.get_write_process_report", return_value=write_report) as get_write_process_report,
                patch("vibeagent.cli.format_write_process_report_text", return_value="Write process:\n  ok: no") as format_write_process_report,
                redirect_stdout(write_stdout),
            ):
                write_exit = main(["--json", "--cwd", base, "--write-process", "missing", "--write-stdin", "hello\\n"])

        check_payload = json.loads(check_stdout.getvalue())
        write_payload = json.loads(write_stdout.getvalue())
        self.assertEqual(check_exit, 0)
        self.assertTrue(check_payload["success"])
        self.assertEqual(check_payload["checkWriteProcess"], check_report)
        get_check_write_process_report.assert_called_once_with(Path(base).resolve(), process_id="bg-1", content="hello\\n")
        format_check_write_process_report.assert_called_once_with(check_report)
        create_chat_client.assert_not_called()
        self.assertEqual(write_exit, 1)
        self.assertFalse(write_payload["success"])
        self.assertEqual(write_payload["status"], "failed")
        self.assertEqual(write_payload["writeProcess"], write_report)
        get_write_process_report.assert_called_once_with(Path(base).resolve(), process_id="missing", content="hello\\n")
        format_write_process_report.assert_called_once_with(write_report)
        create_chat_client_write.assert_not_called()

    def test_main_runs_stop_process_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stop_process_text", return_value="Check stop process:\n  ok: yes") as get_check_stop_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-stop-process", "bg-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check stop process:", stdout.getvalue())
        get_check_stop_process_text.assert_called_once_with(Path(base).resolve(), "bg-1")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stop_process_text", return_value="Stop process:\n  ok: no") as get_stop_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--stop-process", "bg-1"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Stop process:", stdout.getvalue())
        get_stop_process_text.assert_called_once_with(Path(base).resolve(), "bg-1")
        create_chat_client.assert_not_called()

    def test_main_stop_process_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            check_stdout = io.StringIO()
            check_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 123,
                "command": "npm run dev",
                "cwd": "web",
                "running": True,
                "exitCode": None,
                "signal": None,
                "status": "running",
                "message": "Process bg-1 is running and can be stopped.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stop_process_report", return_value=check_report) as get_check_stop_process_report,
                patch("vibeagent.cli.format_check_stop_process_report_text", return_value="Check stop process:\n  ok: yes") as format_check_stop_process_report,
                redirect_stdout(check_stdout),
            ):
                check_exit = main(["--json", "--cwd", base, "--check-stop-process", "bg-1"])

            stop_stdout = io.StringIO()
            stop_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "processId": "missing",
                "pid": None,
                "exitCode": None,
                "signal": None,
                "result": "unknown",
                "message": "Unknown background process id.",
            }
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client_stop,
                patch("vibeagent.cli.get_stop_process_report", return_value=stop_report) as get_stop_process_report,
                patch("vibeagent.cli.format_stop_process_report_text", return_value="Stop process:\n  ok: no") as format_stop_process_report,
                redirect_stdout(stop_stdout),
            ):
                stop_exit = main(["--json", "--cwd", base, "--stop-process", "missing"])

        check_payload = json.loads(check_stdout.getvalue())
        stop_payload = json.loads(stop_stdout.getvalue())
        self.assertEqual(check_exit, 0)
        self.assertTrue(check_payload["success"])
        self.assertEqual(check_payload["checkStopProcess"], check_report)
        get_check_stop_process_report.assert_called_once_with(Path(base).resolve(), "bg-1")
        format_check_stop_process_report.assert_called_once_with(check_report)
        create_chat_client.assert_not_called()
        self.assertEqual(stop_exit, 1)
        self.assertFalse(stop_payload["success"])
        self.assertEqual(stop_payload["status"], "failed")
        self.assertEqual(stop_payload["stopProcess"], stop_report)
        get_stop_process_report.assert_called_once_with(Path(base).resolve(), "missing")
        format_stop_process_report.assert_called_once_with(stop_report)
        create_chat_client_stop.assert_not_called()

    def test_main_runs_stop_all_processes_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stop_all_processes_text", return_value="Check stop processes:\n  processes: 1") as get_check_stop_all_processes_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-stop-all-processes"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check stop processes:", stdout.getvalue())
        get_check_stop_all_processes_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stop_all_processes_text", return_value="Stop processes:\n  stopped: 1") as get_stop_all_processes_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--stop-all-processes"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Stop processes:", stdout.getvalue())
        get_stop_all_processes_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_stop_all_processes_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            check_stdout = io.StringIO()
            check_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processes": {
                    "total": 1,
                    "running": 1,
                    "items": [
                        {
                            "processId": "bg-1",
                            "pid": 123,
                            "command": "npm run dev",
                            "cwd": "web",
                            "running": True,
                            "exitCode": None,
                            "signal": None,
                            "status": "running",
                        }
                    ],
                },
                "message": "stop_all_processes would stop 1 background process(es), 1 still running.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stop_all_processes_report", return_value=check_report) as get_check_stop_all_processes_report,
                patch("vibeagent.cli.format_check_stop_all_processes_report_text", return_value="Check stop processes:\n  processes: 1") as format_check_stop_all_processes_report,
                redirect_stdout(check_stdout),
            ):
                check_exit = main(["--json", "--cwd", base, "--check-stop-all-processes"])

            stop_stdout = io.StringIO()
            stop_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "stopped": {
                    "total": 1,
                    "items": [
                        {
                            "processId": "bg-1",
                            "pid": 123,
                            "command": "npm run dev",
                            "cwd": "web",
                            "ok": True,
                            "exitCode": -15,
                            "signal": "SIGTERM",
                            "result": "signaled(SIGTERM)",
                            "message": "Stopped process bg-1.",
                        }
                    ],
                },
                "message": "Stopped 1 background process(es).",
            }
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client_stop,
                patch("vibeagent.cli.get_stop_all_processes_report", return_value=stop_report) as get_stop_all_processes_report,
                patch("vibeagent.cli.format_stop_all_processes_report_text", return_value="Stop processes:\n  stopped: 1") as format_stop_all_processes_report,
                redirect_stdout(stop_stdout),
            ):
                stop_exit = main(["--json", "--cwd", base, "--stop-all-processes"])

        check_payload = json.loads(check_stdout.getvalue())
        stop_payload = json.loads(stop_stdout.getvalue())
        self.assertEqual(check_exit, 0)
        self.assertTrue(check_payload["success"])
        self.assertEqual(check_payload["checkStopAllProcesses"], check_report)
        get_check_stop_all_processes_report.assert_called_once_with(Path(base).resolve())
        format_check_stop_all_processes_report.assert_called_once_with(check_report)
        create_chat_client.assert_not_called()
        self.assertEqual(stop_exit, 0)
        self.assertTrue(stop_payload["success"])
        self.assertEqual(stop_payload["stopAllProcesses"], stop_report)
        get_stop_all_processes_report.assert_called_once_with(Path(base).resolve())
        format_stop_all_processes_report.assert_called_once_with(stop_report)
        create_chat_client_stop.assert_not_called()

    def test_main_runs_git_stage_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stage_text", return_value="Check stage:\n  ok: yes") as get_check_stage_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-stage", "app.py", "tests/test_app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check stage:", stdout.getvalue())
        get_check_stage_text.assert_called_once_with(Path(base).resolve(), ["app.py", "tests/test_app.py"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stage_text", return_value="Stage:\n  ok: yes") as get_stage_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-stage", "app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Stage:", stdout.getvalue())
        get_stage_text.assert_called_once_with(Path(base).resolve(), ["app.py"])
        create_chat_client.assert_not_called()

    def test_main_runs_git_unstage_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_unstage_text", return_value="Check unstage:\n  ok: yes") as get_check_unstage_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-unstage", "app.py", "tests/test_app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check unstage:", stdout.getvalue())
        get_check_unstage_text.assert_called_once_with(Path(base).resolve(), ["app.py", "tests/test_app.py"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_unstage_text", return_value="Unstage:\n  ok: yes") as get_unstage_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-unstage", "app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Unstage:", stdout.getvalue())
        get_unstage_text.assert_called_once_with(Path(base).resolve(), ["app.py"])
        create_chat_client.assert_not_called()

    def test_main_check_git_stage_local_flag_exits_nonzero_when_not_ok(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stage_text", return_value="Check stage:\n  ok: no\n  message: git status failed"),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-stage", "app.py"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Check stage:", stdout.getvalue())
        self.assertIn("ok: no", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_runs_git_commit_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_commit_text", return_value="Check commit:\n  ok: yes") as get_check_commit_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-commit", "update app"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check commit:", stdout.getvalue())
        get_check_commit_text.assert_called_once_with(Path(base).resolve(), "update app")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_commit_text", return_value="Commit:\n  ok: yes") as get_commit_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-commit", "update app"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Commit:", stdout.getvalue())
        get_commit_text.assert_called_once_with(Path(base).resolve(), "update app")
        create_chat_client.assert_not_called()

    def test_main_runs_git_restore_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_restore_text", return_value="Check restore:\n  ok: yes") as get_check_restore_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-restore", "app.py", "tests/test_app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check restore:", stdout.getvalue())
        get_check_restore_text.assert_called_once_with(Path(base).resolve(), ["app.py", "tests/test_app.py"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_restore_text", return_value="Restore:\n  ok: yes") as get_restore_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-restore", "app.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Restore:", stdout.getvalue())
        get_restore_text.assert_called_once_with(Path(base).resolve(), ["app.py"])
        create_chat_client.assert_not_called()

    def test_main_runs_git_index_commit_restore_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--check-git-stage", "app.py", "tests/test_app.py"],
                "vibeagent.cli.get_check_stage_report",
                "vibeagent.cli.format_git_index_report_text",
                "Check stage",
                "checkGitStage",
                (["app.py", "tests/test_app.py"],),
            ),
            (
                ["--git-stage", "app.py"],
                "vibeagent.cli.get_stage_report",
                "vibeagent.cli.format_git_index_report_text",
                "Stage",
                "gitStage",
                (["app.py"],),
            ),
            (
                ["--check-git-unstage", "app.py", "tests/test_app.py"],
                "vibeagent.cli.get_check_unstage_report",
                "vibeagent.cli.format_git_index_report_text",
                "Check unstage",
                "checkGitUnstage",
                (["app.py", "tests/test_app.py"],),
            ),
            (
                ["--git-unstage", "app.py"],
                "vibeagent.cli.get_unstage_report",
                "vibeagent.cli.format_git_index_report_text",
                "Unstage",
                "gitUnstage",
                (["app.py"],),
            ),
            (
                ["--check-git-commit", "update app"],
                "vibeagent.cli.get_check_commit_report",
                "vibeagent.cli.format_git_commit_report_text",
                "Check commit",
                "checkGitCommit",
                ("update app",),
            ),
            (
                ["--git-commit", "update app"],
                "vibeagent.cli.get_commit_report",
                "vibeagent.cli.format_git_commit_report_text",
                "Commit",
                "gitCommit",
                ("update app",),
            ),
            (
                ["--check-git-restore", "app.py", "tests/test_app.py"],
                "vibeagent.cli.get_check_restore_report",
                "vibeagent.cli.format_git_restore_report_text",
                "Check restore",
                "checkGitRestore",
                (["app.py", "tests/test_app.py"],),
            ),
            (
                ["--git-restore", "app.py"],
                "vibeagent.cli.get_restore_report",
                "vibeagent.cli.format_git_restore_report_text",
                "Restore",
                "gitRestore",
                (["app.py"],),
            ),
        ]

        for argv_tail, getter_target, formatter_target, title, payload_key, expected_args in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{title}:\n  ok: yes"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch(formatter_target, return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(Path(base).resolve(), *expected_args)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_git_remote_sync_switch_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--check-git-fetch", "origin"],
                "vibeagent.cli.get_check_fetch_report",
                "vibeagent.cli.format_git_fetch_report_text",
                "Check fetch",
                "checkGitFetch",
                ("origin",),
            ),
            (
                ["--git-fetch", "origin"],
                "vibeagent.cli.get_fetch_report",
                "vibeagent.cli.format_git_fetch_report_text",
                "Fetch",
                "gitFetch",
                ("origin",),
            ),
            (
                ["--check-git-pull"],
                "vibeagent.cli.get_check_pull_report",
                "vibeagent.cli.format_git_sync_preview_report_text",
                "Check pull",
                "checkGitPull",
                (),
            ),
            (
                ["--git-pull"],
                "vibeagent.cli.get_pull_report",
                "vibeagent.cli.format_git_pull_report_text",
                "Pull",
                "gitPull",
                (),
            ),
            (
                ["--check-git-push"],
                "vibeagent.cli.get_check_push_report",
                "vibeagent.cli.format_git_sync_preview_report_text",
                "Check push",
                "checkGitPush",
                (),
            ),
            (
                ["--git-push"],
                "vibeagent.cli.get_push_report",
                "vibeagent.cli.format_git_push_report_text",
                "Push",
                "gitPush",
                (),
            ),
            (
                ["--check-git-switch", "feature/demo", "--git-switch-create"],
                "vibeagent.cli.get_check_switch_report",
                "vibeagent.cli.format_git_switch_report_text",
                "Check switch",
                "checkGitSwitch",
                ("--create feature/demo",),
            ),
            (
                ["--git-switch", "main"],
                "vibeagent.cli.get_switch_report",
                "vibeagent.cli.format_git_switch_report_text",
                "Switch",
                "gitSwitch",
                ("main",),
            ),
        ]

        for argv_tail, getter_target, formatter_target, title, payload_key, expected_args in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{title}:\n  ok: yes"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch(formatter_target, return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(Path(base).resolve(), *expected_args)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_git_stash_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stash_text", return_value="Check stash:\n  ok: yes") as get_check_stash_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-stash", "save work", "--stash-include-untracked"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check stash:", stdout.getvalue())
        get_check_stash_text.assert_called_once_with(Path(base).resolve(), "--include-untracked save work")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stash_text", return_value="Stash:\n  ok: yes") as get_stash_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-stash"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Stash:", stdout.getvalue())
        get_stash_text.assert_called_once_with(Path(base).resolve(), "")
        create_chat_client.assert_not_called()

    def test_main_runs_git_stash_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--check-git-stash", "save work", "--stash-include-untracked"],
                "vibeagent.cli.get_check_stash_report",
                "vibeagent.cli.format_git_stash_report_text",
                "Check stash",
                "checkGitStash",
                ("--include-untracked save work",),
            ),
            (
                ["--git-stash"],
                "vibeagent.cli.get_stash_report",
                "vibeagent.cli.format_git_stash_report_text",
                "Stash",
                "gitStash",
                ("",),
            ),
            (
                ["--check-git-stash-apply", "stash@{0}"],
                "vibeagent.cli.get_check_stash_apply_report",
                "vibeagent.cli.format_git_stash_apply_report_text",
                "Check stash apply",
                "checkGitStashApply",
                ("stash@{0}",),
            ),
            (
                ["--git-stash-apply", "stash@{0}"],
                "vibeagent.cli.get_stash_apply_report",
                "vibeagent.cli.format_git_stash_apply_report_text",
                "Stash apply",
                "gitStashApply",
                ("stash@{0}",),
            ),
            (
                ["--check-git-stash-drop", "stash@{0}"],
                "vibeagent.cli.get_check_stash_drop_report",
                "vibeagent.cli.format_git_stash_drop_report_text",
                "Check stash drop",
                "checkGitStashDrop",
                ("stash@{0}",),
            ),
            (
                ["--git-stash-drop", "stash@{0}"],
                "vibeagent.cli.get_stash_drop_report",
                "vibeagent.cli.format_git_stash_drop_report_text",
                "Stash drop",
                "gitStashDrop",
                ("stash@{0}",),
            ),
        ]

        for argv_tail, getter_target, formatter_target, title, payload_key, expected_args in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{title}:\n  ok: yes"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch(formatter_target, return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(Path(base).resolve(), *expected_args)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_git_stash_apply_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stash_apply_text", return_value="Check stash apply:\n  ok: yes") as get_check_stash_apply_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-stash-apply", "stash@{0}"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check stash apply:", stdout.getvalue())
        get_check_stash_apply_text.assert_called_once_with(Path(base).resolve(), "stash@{0}")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stash_apply_text", return_value="Stash apply:\n  ok: yes") as get_stash_apply_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-stash-apply", "stash@{0}"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Stash apply:", stdout.getvalue())
        get_stash_apply_text.assert_called_once_with(Path(base).resolve(), "stash@{0}")
        create_chat_client.assert_not_called()

    def test_main_runs_git_stash_drop_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stash_drop_text", return_value="Check stash drop:\n  ok: yes") as get_check_stash_drop_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-stash-drop", "stash@{0}"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check stash drop:", stdout.getvalue())
        get_check_stash_drop_text.assert_called_once_with(Path(base).resolve(), "stash@{0}")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stash_drop_text", return_value="Stash drop:\n  ok: yes") as get_stash_drop_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-stash-drop", "stash@{0}"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Stash drop:", stdout.getvalue())
        get_stash_drop_text.assert_called_once_with(Path(base).resolve(), "stash@{0}")
        create_chat_client.assert_not_called()

    def test_main_runs_git_remote_sync_local_flags_without_creating_client(self) -> None:
        cases = [
            ("--check-git-fetch", "origin", "vibeagent.cli.get_check_fetch_text", "Check fetch:", [Path, "origin"]),
            ("--git-fetch", "origin", "vibeagent.cli.get_fetch_text", "Fetch:", [Path, "origin"]),
            ("--check-git-pull", None, "vibeagent.cli.get_check_pull_text", "Check pull:", [Path]),
            ("--git-pull", None, "vibeagent.cli.get_pull_text", "Pull:", [Path]),
            ("--check-git-push", None, "vibeagent.cli.get_check_push_text", "Check push:", [Path]),
            ("--git-push", None, "vibeagent.cli.get_push_text", "Push:", [Path]),
        ]
        for flag, value, patch_target, output_text, expected_args in cases:
            with self.subTest(flag=flag), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                argv = ["--cwd", base, flag]
                if value is not None:
                    argv.append(value)

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=f"{output_text}\n  ok: yes") as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

            self.assertEqual(exit_code, 0)
            self.assertIn(output_text, stdout.getvalue())
            resolved_args = [Path(base).resolve() if item is Path else item for item in expected_args]
            getter.assert_called_once_with(*resolved_args)
            create_chat_client.assert_not_called()

    def test_main_reports_stash_include_untracked_without_stash_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--stash-include-untracked", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--stash-include-untracked can only be used with --check-git-stash or --git-stash.\n")
        create_chat_client.assert_not_called()

    def test_main_runs_git_switch_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_switch_text", return_value="Check switch:\n  ok: yes") as get_check_switch_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-git-switch", "feature/demo", "--git-switch-create"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check switch:", stdout.getvalue())
        get_check_switch_text.assert_called_once_with(Path(base).resolve(), "--create feature/demo")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_switch_text", return_value="Switch:\n  ok: yes") as get_switch_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--git-switch", "main"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Switch:", stdout.getvalue())
        get_switch_text.assert_called_once_with(Path(base).resolve(), "main")
        create_chat_client.assert_not_called()

    def test_main_reports_git_switch_create_without_switch_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--git-switch-create", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--git-switch-create can only be used with --check-git-switch or --git-switch.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_diff_max_chars_without_diff_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--diff-max-chars", "2000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--diff-max-chars can only be used with --diff.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_changes_max_files_without_changes_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--changes-max-files", "1", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--changes-max-files can only be used with --changes.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_review_limits_without_review_as_local_flag_errors(self) -> None:
        cases = [
            (["--review-max-files", "1", "fix", "tests"], "--review-max-files can only be used with --review.\n"),
            (["--review-max-checks", "1", "fix", "tests"], "--review-max-checks can only be used with --review.\n"),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_handoff_limits_without_handoff_as_local_flag_errors(self) -> None:
        cases = [
            (["--handoff-max-files", "1", "fix", "tests"], "--handoff-max-files can only be used with --handoff.\n"),
            (["--handoff-max-checks", "1", "fix", "tests"], "--handoff-max-checks can only be used with --handoff.\n"),
            (["--handoff-max-status-chars", "1000", "fix", "tests"], "--handoff-max-status-chars can only be used with --handoff.\n"),
            (["--handoff-max-plan-chars", "1000", "fix", "tests"], "--handoff-max-plan-chars can only be used with --handoff.\n"),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_structured_diff_limits_without_matching_diff_flag_as_local_flag_errors(self) -> None:
        cases = [
            (["--diff-hunks-max-hunks", "2", "fix"], "--diff-hunks-max-hunks can only be used with --diff-hunks.\n"),
            (["--diff-hunks-max-lines", "2", "fix"], "--diff-hunks-max-lines can only be used with --diff-hunks.\n"),
            (["--diff-context-lines", "2", "fix"], "--diff-context-lines can only be used with --diff-contexts.\n"),
            (["--diff-contexts-max-hunks", "2", "fix"], "--diff-contexts-max-hunks can only be used with --diff-contexts.\n"),
            (["--diff-contexts-max-bytes", "1000", "fix"], "--diff-contexts-max-bytes can only be used with --diff-contexts.\n"),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_process_max_chars_without_process_output_flag_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--process-max-chars", "2000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--process-max-chars can only be used with --process-output, --process-output-contexts, or --process-output-diagnostics.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_process_output_context_options_without_context_flag_as_local_flag_error(self) -> None:
        cases = [
            (["--process-output-context-lines", "2", "fix"], "--process-output-context-lines can only be used with --process-output-contexts or --process-output-diagnostics.\n"),
            (["--process-output-context-max", "5", "fix"], "--process-output-context-max can only be used with --process-output-contexts or --process-output-diagnostics.\n"),
            (["--process-output-context-max-bytes", "1000", "fix"], "--process-output-context-max-bytes can only be used with --process-output-contexts or --process-output-diagnostics.\n"),
            (["--process-output-diagnostic-max", "5", "fix"], "--process-output-diagnostic-max can only be used with --process-output-diagnostics.\n"),
            (["--process-output-contexts", "bg-1", "--process-output-diagnostic-max", "5"], "--process-output-diagnostic-max can only be used with --process-output-diagnostics.\n"),
        ]

        for argv, message in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), message)
                create_chat_client.assert_not_called()

    def test_main_reports_wait_options_without_wait_process_as_local_flag_error(self) -> None:
        cases = [
            (["--wait-timeout-ms", "2000", "fix"], "--wait-timeout-ms can only be used with --wait-process.\n"),
            (["--wait-max-chars", "2000", "fix"], "--wait-max-chars can only be used with --wait-process.\n"),
            (["--wait-stdout", "ready", "fix"], "--wait-stdout can only be used with --wait-process.\n"),
            (["--wait-stderr", "ready", "fix"], "--wait-stderr can only be used with --wait-process.\n"),
            (["--wait-regex", "fix"], "--wait-regex can only be used with --wait-process.\n"),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_write_process_stdin_pairing_errors(self) -> None:
        cases = [
            (["--write-stdin", "hello", "fix"], "--write-stdin can only be used with --check-write-process or --write-process.\n"),
            (["--check-write-process", "bg-1"], "--check-write-process requires --write-stdin.\n"),
            (["--write-process", "bg-1"], "--write-process requires --write-stdin.\n"),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_stash_count_without_stashes_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--stash-count", "3", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--stash-count can only be used with --stashes.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_blame_lines_without_blame_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--blame-lines", "2:4", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--blame-lines can only be used with --blame.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_show_options_without_show_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--show-path", "app.py", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--show-path can only be used with --show.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_log_count_without_log_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--log-count", "2", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--log-count can only be used with --log.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_read_lines_without_read_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--read-lines", "2:4", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--read-lines can only be used with --read.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_read_max_bytes_without_read_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--read-max-bytes", "1000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--read-max-bytes can only be used with --read.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_read_line_numbers_without_read_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--read-line-numbers", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--read-line-numbers can only be used with --read.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_read_files_max_bytes_without_read_files_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--read-files-max-bytes", "1000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--read-files-max-bytes can only be used with --read-files.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_read_files_line_numbers_without_read_files_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--read-files-line-numbers", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--read-files-line-numbers can only be used with --read-files.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_read_ranges_max_bytes_without_read_ranges_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--read-ranges-max-bytes", "1000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--read-ranges-max-bytes can only be used with --read-ranges.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_around_lines_without_around_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--around-lines", "5", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--around-lines can only be used with --around.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_around_max_bytes_without_around_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--around-max-bytes", "1000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--around-max-bytes can only be used with --around.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_around_many_max_bytes_without_around_many_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--around-many-max-bytes", "1000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--around-many-max-bytes can only be used with --around-many.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_output_context_options_without_output_contexts_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--output-context-lines", "2", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--output-context-lines can only be used with --output-contexts.\n")
        create_chat_client.assert_not_called()

        stdout = io.StringIO()
        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--output-context-max", "5", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--output-context-max can only be used with --output-contexts.\n")
        create_chat_client.assert_not_called()

        stdout = io.StringIO()
        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--output-context-max-bytes", "1000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--output-context-max-bytes can only be used with --output-contexts.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_output_diagnostic_options_without_output_diagnostics_as_local_flag_error(self) -> None:
        cases = [
            (["--output-diagnostic-lines", "3", "fix"], "--output-diagnostic-lines can only be used with --output-diagnostics or --python-traceback.\n"),
            (["--output-diagnostic-max", "5", "fix"], "--output-diagnostic-max can only be used with --output-diagnostics or --python-traceback.\n"),
            (["--output-diagnostic-context-max", "5", "fix"], "--output-diagnostic-context-max can only be used with --output-diagnostics or --python-traceback.\n"),
            (["--output-diagnostic-context-max-bytes", "1000", "fix"], "--output-diagnostic-context-max-bytes can only be used with --output-diagnostics or --python-traceback.\n"),
        ]

        for argv, message in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), message)
                create_chat_client.assert_not_called()

    def test_main_reports_session_output_context_options_without_session_output_contexts_as_local_flag_error(self) -> None:
        cases = [
            (
                ["--session-output-command-max", "3", "fix", "tests"],
                "--session-output-command-max can only be used with --session-output-contexts or --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-max-chars", "4000", "fix", "tests"],
                "--session-output-max-chars can only be used with --session-output-contexts or --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-context-lines", "2", "fix", "tests"],
                "--session-output-context-lines can only be used with --session-output-contexts or --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-context-max", "5", "fix", "tests"],
                "--session-output-context-max can only be used with --session-output-contexts or --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-context-max-bytes", "1000", "fix", "tests"],
                "--session-output-context-max-bytes can only be used with --session-output-contexts or --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-diagnostic-max", "4", "fix", "tests"],
                "--session-output-diagnostic-max can only be used with --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-diagnostic-max", "4", "--session-output-contexts", "run-1"],
                "--session-output-diagnostic-max can only be used with --session-output-diagnostics.\n",
            ),
        ]

        for argv, message in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), message)
                create_chat_client.assert_not_called()

    def test_main_reports_session_limit_options_without_matching_session_view_as_local_flag_error(self) -> None:
        cases = [
            (
                ["--session-transcript-event-max", "3", "fix", "tests"],
                "--session-transcript-event-max can only be used with --transcript.\n",
            ),
            (
                ["--session-search-match-max", "3", "fix", "tests"],
                "--session-search-match-max can only be used with --session-search.\n",
            ),
            (
                ["--session-search-case-sensitive", "fix", "tests"],
                "--session-search-case-sensitive can only be used with --session-search.\n",
            ),
            (
                ["--session-max-checks", "3", "fix", "tests"],
                "--session-max-checks can only be used with --session-verification, --run-session-verification, --session-audit, or --session-handoff.\n",
            ),
            (
                ["--session-max-commands", "3", "fix", "tests"],
                "--session-max-commands can only be used with --session-commands, --session-audit, or --session-handoff.\n",
            ),
            (
                ["--session-max-output-chars", "4000", "fix", "tests"],
                "--session-max-output-chars can only be used with --session-commands or --session-handoff.\n",
            ),
            (
                ["--session-max-output-chars", "4000", "--session-audit", "run-1"],
                "--session-max-output-chars can only be used with --session-commands or --session-handoff.\n",
            ),
            (
                ["--session-max-files", "7", "--session-commands", "run-1"],
                "--session-max-files can only be used with --session-files, --session-audit, or --session-handoff.\n",
            ),
            (
                ["--session-max-failures", "4", "--session-files", "run-1"],
                "--session-max-failures can only be used with --session-failures, --session-audit, or --session-handoff.\n",
            ),
            (
                ["--session-max-text", "120", "--session-commands", "run-1"],
                "--session-max-text can only be used with --transcript, --session-search, --session-failures, --session-audit, or --session-handoff.\n",
            ),
        ]

        for argv, message in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), message)
                create_chat_client.assert_not_called()

    def test_main_reports_tail_lines_without_tail_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--tail-lines", "5", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--tail-lines can only be used with --tail.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_tail_max_bytes_without_tail_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--tail-max-bytes", "1000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--tail-max-bytes can only be used with --tail.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_search_path_without_search_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--search-path", "src", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--search-path can only be used with --search or --search-contexts.\n")
        create_chat_client.assert_not_called()

    def test_main_local_model_flag_uses_provider_overrides(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_model_text", return_value="Model provider: deepseek") as get_model_text,
            redirect_stdout(stdout),
        ):
            exit_code = main(
                [
                    "--model",
                    "--provider",
                    "deepseek",
                    "--model-name",
                    "deepseek-reasoner",
                    "--base-url",
                    "https://deepseek.example",
                    "--api-key",
                    "secret-key",
                ]
            )

        provider_env = get_model_text.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertIn("Model provider: deepseek", stdout.getvalue())
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["OPENAI_COMPAT_MODEL"], "deepseek-reasoner")
        self.assertEqual(provider_env["OPENAI_COMPAT_BASE_URL"], "https://deepseek.example")
        self.assertEqual(provider_env["OPENAI_COMPAT_API_KEY"], "secret-key")
        create_chat_client.assert_not_called()

    def test_main_local_model_flag_uses_project_provider_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps({"provider": "deepseek", "model": "deepseek-reasoner"}),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_model_text", return_value="Model provider: deepseek") as get_model_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--model"])

        provider_env = get_model_text.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertIn("Model provider: deepseek", stdout.getvalue())
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["VIBEAGENT_MODEL"], "deepseek-reasoner")
        create_chat_client.assert_not_called()

    def test_main_local_model_flag_exits_nonzero_for_invalid_provider(self) -> None:
        stdout = io.StringIO()

        with (
            patch.dict("vibeagent.cli.os.environ", {"VIBEAGENT_PROVIDER": "unknown"}, clear=True),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--model"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Unsupported VIBEAGENT_PROVIDER: unknown", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_local_config_flag_reports_resolved_config_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_config_text", return_value="Config:\n  provider: deepseek") as get_config_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--config",
                        "--provider",
                        "deepseek",
                        "--model-name",
                        "deepseek-reasoner",
                        "--max-iterations",
                        "9",
                        "--command-timeout-ms",
                        "120000",
                        "--max-output-tokens",
                        "8192",
                        "--model-retries",
                        "2",
                        "--model-retry-delay-ms",
                        "25",
                        "--model-timeout-ms",
                        "45000",
                    ]
                )

        provider_env = get_config_text.call_args.args[1]
        self.assertEqual(exit_code, 0)
        self.assertIn("Config:", stdout.getvalue())
        self.assertEqual(get_config_text.call_args.args[0], Path(base).resolve())
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["OPENAI_COMPAT_MODEL"], "deepseek-reasoner")
        self.assertEqual(get_config_text.call_args.kwargs["max_iterations"], 9)
        self.assertEqual(get_config_text.call_args.kwargs["command_timeout_ms"], 120000)
        self.assertEqual(get_config_text.call_args.kwargs["max_output_tokens"], 8192)
        self.assertEqual(get_config_text.call_args.kwargs["model_retries"], 2)
        self.assertEqual(get_config_text.call_args.kwargs["model_retry_delay_ms"], 25)
        self.assertEqual(get_config_text.call_args.kwargs["model_timeout_ms"], 45000)
        create_chat_client.assert_not_called()

    def test_main_save_config_writes_non_secret_project_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--save-config",
                        "--provider",
                        "deepseek",
                        "--model-name",
                        "deepseek-reasoner",
                        "--base-url",
                        "https://deepseek.example",
                        "--max-iterations",
                        "15",
                        "--command-timeout-ms",
                        "60000",
                        "--max-output-tokens",
                        "8192",
                        "--model-retries",
                        "2",
                        "--model-retry-delay-ms",
                        "25",
                        "--model-timeout-ms",
                        "60000",
                    ]
                )
            data = json.loads((Path(base) / ".vibeagent" / "config.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "Saved .vibeagent/config.json.\n")
        self.assertEqual(data["provider"], "deepseek")
        self.assertEqual(data["model"], "deepseek-reasoner")
        self.assertEqual(data["base_url"], "https://deepseek.example")
        self.assertEqual(data["max_iterations"], 15)
        self.assertEqual(data["command_timeout_ms"], 60000)
        self.assertEqual(data["max_output_tokens"], 8192)
        self.assertEqual(data["model_retries"], 2)
        self.assertEqual(data["model_retry_delay_ms"], 25)
        self.assertEqual(data["model_timeout_ms"], 60000)
        self.assertNotIn("api_key", data)
        create_chat_client.assert_not_called()

    def test_main_save_config_accepts_model_alias(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--save-config", "--provider", "minimax", "--model", "MiniMax-custom"])
            data = json.loads((Path(base) / ".vibeagent" / "config.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(data["provider"], "minimax")
        self.assertEqual(data["model"], "MiniMax-custom")
        create_chat_client.assert_not_called()

    def test_main_save_config_rejects_api_key_without_writing_secret(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--save-config", "--provider", "deepseek", "--api-key", "secret-key"])
            config_path = Path(base) / ".vibeagent" / "config.json"

        self.assertEqual(exit_code, 1)
        self.assertIn("--save-config does not write API keys", stdout.getvalue())
        self.assertFalse(config_path.exists())
        create_chat_client.assert_not_called()

    def test_main_save_config_with_json_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--save-config",
                        "--provider",
                        "minimax",
                        "--model-name",
                        "MiniMax-M2.7",
                        "--max-iterations",
                        "9",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["text"], "Saved .vibeagent/config.json.")
        report = payload["saveConfig"]
        self.assertTrue(report["ok"])
        self.assertTrue(report["created"])
        self.assertFalse(report["existedBefore"])
        self.assertTrue(report["exists"])
        self.assertEqual(report["projectRoot"], str(Path(base).resolve()))
        self.assertEqual(report["path"], str(Path(base).resolve() / ".vibeagent" / "config.json"))
        self.assertEqual(report["writtenKeys"], ["provider", "model", "max_iterations"])
        self.assertEqual(report["config"]["provider"], "minimax")
        self.assertEqual(report["config"]["model"], "MiniMax-M2.7")
        self.assertEqual(report["config"]["max_iterations"], 9)
        self.assertNotIn("api_key", json.dumps(report, ensure_ascii=False))
        create_chat_client.assert_not_called()

    def test_main_local_session_flag_uses_requested_run_id_and_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_text", return_value="Session: run-1") as get_session_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session", " run-1 "])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session: run-1", stdout.getvalue())
        get_session_text.assert_called_once_with("run-1", Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_local_status_flag_uses_approval_setting(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--approval", "deny", "--status"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Status:", stdout.getvalue())
        self.assertIn("approval: deny", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_local_status_flag_reports_json_payload(self) -> None:
        stdout = io.StringIO()
        report = {
            "mode": "code",
            "approval": "deny",
            "resume": "",
            "chatTurns": 0,
            "message": "Runtime status resolved.",
        }

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_status_report", return_value=report) as get_status_report,
            patch("vibeagent.cli.format_status_report_text", return_value="Status:\n  approval: deny"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--approval", "deny", "--status"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["runtimeStatus"], report)
        self.assertIn("Status:", payload["text"])
        get_status_report.assert_called_once_with("code", "deny", None, chat_turns=0)
        create_chat_client.assert_not_called()

    def test_main_local_context_flag_reports_json_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "resume": "",
                "resumeChars": 0,
                "instructions": {"found": False, "text": "No AGENTS.md or CLAUDE.md instructions found."},
                "commandHints": {"found": False, "text": "No project command hints found."},
                "workspaceSnapshot": {"text": "."},
                "message": "Prompt context resolved.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_context_report", return_value=report) as get_context_report,
                patch("vibeagent.cli.format_context_report_text", return_value="Context:\n  resume: none"),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--context"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["context"], report)
        self.assertIn("Context:", payload["text"])
        get_context_report.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_local_context_flag_defaults_to_current_directory(self) -> None:
        stdout = io.StringIO()
        report = {
            "projectRoot": str(Path.cwd().resolve()),
            "resume": "",
            "resumeChars": 0,
            "instructions": {"found": False, "text": "No AGENTS.md or CLAUDE.md instructions found."},
            "commandHints": {"found": False, "text": "No project command hints found."},
            "workspaceSnapshot": {"text": "."},
            "message": "Prompt context resolved.",
        }

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_context_report", return_value=report) as get_context_report,
            patch("vibeagent.cli.format_context_report_text", return_value="Context:\n  resume: none"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--context"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["context"], report)
        get_context_report.assert_called_once_with(".")
        create_chat_client.assert_not_called()

    def test_main_local_flag_rejects_task_text(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--doctor", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "Local command flags cannot be combined with a task.\n")
        create_chat_client.assert_not_called()

    def test_main_local_flag_rejects_task_text_with_json_status(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--doctor", "fix", "tests"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["kind"], "error")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["error"], "Local command flags cannot be combined with a task.")
        create_chat_client.assert_not_called()

    def test_main_runs_one_shot_code_task_from_stdin(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("sys.stdin", io.StringIO("fix from stdin\n")),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["-"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.args[0], "fix from stdin")

    def test_main_runs_one_shot_code_task_from_stream_json_stdin(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            input_records = "\n".join(
                [
                    json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": "fix from"}]}}),
                    json.dumps({"type": "user", "text": "stream json"}),
                ]
            )

            with (
                patch("sys.stdin", io.StringIO(input_records)),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--input-format", "stream-json", "-"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.args[0], "fix from\nstream json")

    def test_main_stream_json_session_id_loads_resume_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            input_records = json.dumps(
                {
                    "session_id": "run-1",
                    "messages": [{"role": "user", "content": "continue task"}],
                }
            )

            with (
                patch("sys.stdin", io.StringIO(input_records)),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                patch(
                    "vibeagent.cli.get_resume_context",
                    return_value=("run-1", "previous context", "Resume context loaded from session run-1."),
                ) as get_resume_context,
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--input-format", "stream-json", "--cwd", base, "-"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.args[0], "continue task")
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "previous context")
        get_resume_context.assert_called_once_with("run-1", Path(base).resolve())

    def test_main_runs_one_shot_code_task_from_json_stdin(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            input_record = json.dumps(
                {
                    "session_id": "run-1",
                    "messages": [
                        {"role": "system", "content": "Prefer focused checks."},
                        {"role": "assistant", "content": "I saw tests/test_app.py."},
                        {"role": "user", "input": "continue task"},
                    ],
                }
            )

            with (
                patch("sys.stdin", io.StringIO(input_record)),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                patch(
                    "vibeagent.cli.get_resume_context",
                    return_value=("run-1", "previous context", "Resume context loaded from session run-1."),
                ) as get_resume_context,
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--input-format", "json", "--cwd", base, "-"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.args[0], "continue task")
        self.assertEqual(run_agent.call_args.kwargs["system_prompt"], "Prefer focused checks.")
        self.assertIn("previous context", run_agent.call_args.kwargs["prior_context"])
        self.assertIn("Structured input assistant messages:", run_agent.call_args.kwargs["prior_context"])
        self.assertIn("tests/test_app.py", run_agent.call_args.kwargs["prior_context"])
        get_resume_context.assert_called_once_with("run-1", Path(base).resolve())

    def test_main_stream_json_session_id_does_not_override_explicit_resume(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            input_records = json.dumps({"session_id": "run-1", "type": "user", "text": "continue task"})

            with (
                patch("sys.stdin", io.StringIO(input_records)),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                patch(
                    "vibeagent.cli.get_resume_context",
                    return_value=("explicit-run", "explicit context", "Resume context loaded from session explicit-run."),
                ) as get_resume_context,
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--input-format", "stream-json", "--cwd", base, "--resume", "explicit-run", "-"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "explicit context")
        get_resume_context.assert_called_once_with("explicit-run", Path(base).resolve())

    def test_main_stream_json_stdin_parse_error_does_not_call_agent(self) -> None:
        stdout = io.StringIO()

        with (
            patch("sys.stdin", io.StringIO("{not json}\n")),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--input-format", "stream-json", "-"])

        self.assertEqual(exit_code, 2)
        self.assertIn("Invalid stream-json input on line 1", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_json_stdin_parse_error_does_not_call_agent(self) -> None:
        stdout = io.StringIO()

        with (
            patch("sys.stdin", io.StringIO("{not json}\n")),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--input-format", "json", "-"])

        self.assertEqual(exit_code, 2)
        self.assertIn("Invalid json input", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_rejects_input_format_stream_json_without_stdin_task(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["--input-format", "stream-json", "inspect"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            stdout.getvalue(),
            "--input-format stream-json requires task '-' so input can be read from stdin.\n",
        )

    def test_main_rejects_input_format_json_without_stdin_task(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["--input-format", "json", "inspect"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            stdout.getvalue(),
            "--input-format json requires task '-' so input can be read from stdin.\n",
        )

    def test_main_one_shot_empty_stdin_returns_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("sys.stdin", io.StringIO("\n")),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["-"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "No task provided.\n")
        create_chat_client.assert_not_called()

    def test_main_one_shot_empty_stdin_returns_json_error_status(self) -> None:
        stdout = io.StringIO()

        with (
            patch("sys.stdin", io.StringIO("\n")),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "-"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["kind"], "error")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["error"], "No task provided.")
        create_chat_client.assert_not_called()

    def test_main_runs_one_shot_chat_task_from_args(self) -> None:
        stdout = io.StringIO()
        run_chat = Mock(return_value="你好")

        with (
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_chat", run_chat),
            patch("vibeagent.cli.run_agent") as run_agent,
            redirect_stdout(stdout),
        ):
            exit_code = main(
                [
                    "--chat",
                    "--max-output-tokens",
                    "8192",
                    "--model-retries",
                    "2",
                    "--model-retry-delay-ms",
                    "25",
                    "--model-timeout-ms",
                    "45000",
                    "随便聊聊",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "你好\n")
        run_chat.assert_called_once()
        self.assertEqual(run_chat.call_args.args[0], "随便聊聊")
        self.assertEqual(run_chat.call_args.kwargs["history"], [])
        self.assertEqual(run_chat.call_args.kwargs["max_output_tokens"], 8192)
        self.assertEqual(run_chat.call_args.kwargs["model_retries"], 2)
        self.assertEqual(run_chat.call_args.kwargs["model_retry_delay_ms"], 25)
        self.assertEqual(run_chat.call_args.kwargs["model_timeout_ms"], 45000)
        run_agent.assert_not_called()

    def test_main_runs_one_shot_chat_task_with_json_output(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_chat", return_value="你好"),
            patch("vibeagent.cli_runner.monotonic", side_effect=[20.0, 20.045]),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--chat", "随便聊聊"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload,
            {
                "durationMs": 45,
                "duration_ms": 45,
                "kind": "chat",
                "message": "你好",
                "numTurns": 1,
                "num_turns": 1,
                "result": "你好",
                "success": True,
                "status": "completed",
            },
        )

    def test_main_passes_system_prompt_to_one_shot_chat(self) -> None:
        run_chat = Mock(return_value="好")

        with (
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_chat", run_chat),
            redirect_stdout(io.StringIO()),
        ):
            exit_code = main(["--chat", "--system-prompt", "You are terse.", "随便聊聊"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_chat.call_args.kwargs["system_prompt"], "You are terse.")
        self.assertIsNone(run_chat.call_args.kwargs["append_system_prompt"])

    def test_main_passes_appended_system_prompt_to_one_shot_code_task(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--append-system-prompt", "Prefer focused tests.", "inspect"])

        self.assertEqual(exit_code, 0)
        self.assertIsNone(run_agent.call_args.kwargs["system_prompt"])
        self.assertEqual(run_agent.call_args.kwargs["append_system_prompt"], "Prefer focused tests.")

    def test_main_passes_mcp_config_paths_to_one_shot_code_task(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "extra.mcp.json").write_text('{"mcpServers": {}}', encoding="utf-8")
            result = AgentResult(
                success=True,
                message="done",
                run_dir=root,
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--mcp-config", "extra.mcp.json", "inspect"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["mcp_config_paths"], (root / "extra.mcp.json",))
        self.assertFalse(run_agent.call_args.kwargs["strict_mcp_config"])

    def test_main_passes_strict_mcp_config_to_one_shot_code_task(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "extra.mcp.json").write_text('{"mcpServers": {}}', encoding="utf-8")
            result = AgentResult(
                success=True,
                message="done",
                run_dir=root,
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--mcp-config", "extra.mcp.json", "--strict-mcp-config", "inspect"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["mcp_config_paths"], (root / "extra.mcp.json",))
        self.assertTrue(run_agent.call_args.kwargs["strict_mcp_config"])

    def test_main_missing_mcp_config_path_does_not_create_client(self) -> None:
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--mcp-config", "missing.json", "inspect"])

        self.assertEqual(exit_code, 2)
        self.assertIn("--mcp-config file not found: missing.json.", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_one_shot_code_task_can_load_resume_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_resume_context", return_value=("run-1", "previous context", "Resume context loaded from session run-1.")) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--resume",
                        "run-1",
                        "--resume-max-failures",
                        "3",
                        "--resume-max-files",
                        "4",
                        "--resume-max-commands",
                        "5",
                        "--resume-max-checks",
                        "2",
                        "--resume-max-output-chars",
                        "0",
                        "--resume-max-text",
                        "90",
                        "continue",
                        "task",
                    ]
                )

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_called_once_with(
            "run-1",
            Path(base).resolve(),
            max_failures=3,
            max_files=4,
            max_commands=5,
            max_checks=2,
            max_output_chars=0,
            max_text=90,
        )
        self.assertEqual(run_agent.call_args.kwargs["base_dir"], Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "previous context")

    def test_main_one_shot_session_id_alias_loads_resume_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_resume_context", return_value=("run-1", "previous context", "Resume context loaded from session run-1.")) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--session-id", "run-1", "--resume-max-files", "4", "continue", "task"])

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_called_once_with("run-1", Path(base).resolve(), max_files=4)
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "previous context")

    def test_main_one_shot_session_id_latest_loads_newest_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    return_value=("latest-run", "latest context", "Resume context loaded from session latest-run."),
                ) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--session-id", "latest", "continue", "task"])

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_called_once_with(None, Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "latest context")

    def test_main_resume_overrides_session_id_alias(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_resume_context", return_value=("explicit-run", "explicit context", "Resume context loaded from session explicit-run.")) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--session-id", "run-1", "--resume", "explicit-run", "continue", "task"])

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_called_once_with("explicit-run", Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "explicit context")

    def test_main_one_shot_resume_without_run_id_loads_newest_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    return_value=("latest-run", "latest context", "Resume context loaded from session latest-run."),
                ) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--resume", "--", "continue", "task"])

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_called_once_with(None, Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "latest context")

    def test_main_one_shot_code_task_auto_loads_latest_compact_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_compact_context",
                    return_value=("latest-run", "latest compact context", "Compacted context loaded from session latest-run."),
                ) as get_compact_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "continue", "task"])

        self.assertEqual(exit_code, 0)
        get_compact_context.assert_called_once_with(None, Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "latest compact context")

    def test_main_one_shot_no_auto_compact_runs_without_prior_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_compact_context") as get_compact_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--no-auto-compact", "continue", "task"])

        self.assertEqual(exit_code, 0)
        get_compact_context.assert_not_called()
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])

    def test_main_one_shot_json_reports_auto_loaded_compact_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_compact_context",
                    return_value=("latest-run", "latest compact context", "Compacted context loaded from session latest-run."),
                ),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "continue", "task"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "latest compact context")
        self.assertEqual(payload["priorContext"], {"loaded": True, "source": "auto_compact", "runId": "latest-run"})

    def test_main_one_shot_json_reports_no_auto_compact_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_compact_context") as get_compact_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--no-auto-compact", "continue", "task"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        get_compact_context.assert_not_called()
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])
        self.assertEqual(payload["priorContext"], {"loaded": False, "source": "none", "runId": None})

    def test_main_one_shot_code_task_without_sessions_runs_without_prior_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_compact_context", return_value=(None, None, "No sessions found.")) as get_compact_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "continue", "task"])

        self.assertEqual(exit_code, 0)
        get_compact_context.assert_called_once_with(None, Path(base).resolve())
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])
        self.assertNotIn("No sessions found.", stdout.getvalue())

    def test_main_one_shot_resume_without_cwd_uses_current_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            previous_cwd = Path.cwd()

            try:
                os.chdir(base)
                with (
                    patch("vibeagent.cli.create_chat_client", return_value=object()),
                    patch(
                        "vibeagent.cli.get_resume_context",
                        return_value=("run-1", "previous context", "Resume context loaded from session run-1."),
                    ) as get_resume_context,
                    patch("vibeagent.cli.run_agent", run_agent),
                    redirect_stdout(io.StringIO()),
                ):
                    exit_code = main(["--resume", "run-1", "continue", "task"])
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_called_once_with("run-1", Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["base_dir"], Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "previous context")

    def test_main_one_shot_resume_off_runs_without_prior_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_resume_context", return_value=(None, None, "Resume context cleared.")) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--resume", "off", "fresh", "task"])

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_called_once_with("off", Path(base).resolve())
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])

    def test_main_one_shot_invalid_cwd_returns_error_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--cwd", "missing-dir", "continue"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Project directory not found: missing-dir", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_one_shot_error_with_json_output(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--cwd", "missing-dir", "continue"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["kind"], "error")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["error"], "Project directory not found: missing-dir")
        create_chat_client.assert_not_called()

    def test_main_interactive_uses_requested_cwd_and_restores_original_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            original_cwd = Path.cwd()
            seen_cwds: list[Path] = []

            def fake_git_status_text() -> str:
                seen_cwds.append(Path.cwd())
                return "Git status:\n  ok: yes"

            with (
                patch("builtins.input", side_effect=["/git-status", "/exit"]),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_git_status_text", side_effect=fake_git_status_text),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base])

        self.assertEqual(exit_code, 0)
        self.assertIn("Git status:", stdout.getvalue())
        self.assertEqual(seen_cwds, [Path(base).resolve()])
        self.assertEqual(Path.cwd(), original_cwd)
        create_chat_client.assert_not_called()

    def test_main_interactive_tool_search_reports_invalid_option_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("builtins.input", side_effect=["/tool-search --category missing verification", "/exit"]),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tool_search_text") as get_tool_search_text,
            redirect_stdout(stdout),
        ):
            exit_code = main([])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /tool-search", output)
        self.assertIn("--category must be one of:", output)
        get_tool_search_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_one_shot_code_task_reports_missing_resume_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_resume_context", return_value=(None, None, "Session not found: missing")),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--resume", "missing", "continue"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "Session not found: missing\n")
        create_chat_client.assert_not_called()

    def test_main_handles_session_commands_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "builtins.input",
                    side_effect=[
                        "/sessions",
                        "/usage",
                        "/cost",
                        "/doctor",
                        "/config",
                        "/review",
                        "/handoff",
                        "/changes",
                        "/diff --staged app.py",
                        "/diff-hunks --staged app.py",
                        "/diff-contexts --staged app.py",
                        "/tools",
                        "/tool read_file",
                        "/tool-search --max 3 --category session --approval no verification",
                        "/permissions",
                        "/checks",
                        "/commands",
                        "/related-tests pkg/actions.py",
                        "/focused-tests pkg/actions.py",
                        "/check-focused-tests pkg/actions.py",
                        "/run-focused-tests pkg/actions.py",
                        "/manifests",
                        "/command python3 --version",
                        "/run python3 --version",
                        "/check-run-seq python3 --version ;; npm test",
                        "/run-seq python3 --version ;; npm test",
                        "/check-start npm run dev",
                        "/start npm run dev",
                        "/port 5173 127.0.0.1 1500",
                        "/http http://127.0.0.1:5173 ready",
                        "/http-fetch http://127.0.0.1:5173/app",
                        "/overview",
                        "/repo-map src",
                        "/search needle",
                        "/search-contexts needle",
                        "/glob **/*.py",
                        "/tree src",
                        "/symbols src/app.py web/app.ts",
                        "/file-info src/app.py asset.bin",
                        "/image-info assets/logo.png",
                        "/read src/app.py 2:4",
                        "/around src/app.py 42 8",
                        "/around-many src/app.py:42:8 tests/test_app.py:17",
                        "/output-contexts src/app.py:42:8",
                        "/output-diagnostics ERROR src/app.py:42:8 failed",
                        "/python-traceback ValueError: bad",
                        "/tail logs/app.log 3",
                        "/read-files src/app.py tests/test_app.py",
                        "/read-ranges src/app.py:2:4 tests/test_app.py:1",
                        "/python-check src",
                        "/python-deps src",
                        "/python-defs Runner.run src",
                        "/python-refs run_agent src",
                        "/python-ref-contexts run_agent src",
                        "/python-calls helper src",
                        "/python-call-graph src",
                        "/python-rename-preview run_agent execute_agent src",
                        "/python-rename run_agent execute_agent src",
                        "/check-replace-python-def Runner.run '    def run(self):\\n        return 2\\n' src",
                        "/replace-python-def Runner.run '    def run(self):\\n        return 2\\n' src",
                        "/config-check pyproject.toml",
                        "/check-json-set package.json /private true",
                        "/json-set package.json /scripts/test '\"npm test\"'",
                        "/check-json-remove package.json /scripts/dev",
                        "/json-remove package.json /keywords/0",
                        "/check-json-patch package.json '[{\"op\":\"replace\",\"path\":\"/private\",\"value\":true}]'",
                        "/json-patch package.json '[{\"op\":\"remove\",\"path\":\"/keywords/0\"}]'",
                        "/check-replace-lines app.py 2 3 'new\\n'",
                        "/replace-lines app.py 2 2 'new\\n'",
                        "/check-insert-lines app.py 2 'new\\n'",
                        "/insert-lines app.py 2 'new\\n'",
                        "/check-append app.py 'new\\n'",
                        "/append app.py 'new\\n'",
                        "/check-write app.py 'new\\n'",
                        "/write app.py 'new\\n'",
                        "/check-write-files app.py 'a\\n' test.py 'b\\n'",
                        "/write-files app.py 'a\\n' test.py 'b\\n'",
                        "/check-edit app.py old new",
                        "/edit app.py old new",
                        "/check-multi-edit app.py old new print log",
                        "/multi-edit app.py old new print log",
                        "/check-delete old.py",
                        "/delete old.py",
                        "/check-delete-files old.py other.py",
                        "/delete-files old.py other.py",
                        "/check-move old.py new.py",
                        "/move old.py new.py",
                        "/check-move-files old.py new.py other.py other-new.py",
                        "/move-files old.py new.py other.py other-new.py",
                        "/check-copy template.py new.py",
                        "/copy template.py new.py",
                        "/check-copy-files template.py new.py config.py config-copy.py",
                        "/copy-files template.py new.py config.py config-copy.py",
                        "/check-move-dir old_pkg new_pkg",
                        "/move-dir old_pkg new_pkg",
                        "/check-move-dirs old_a new_a old_b new_b",
                        "/move-dirs old_a new_a old_b new_b",
                        "/check-copy-dir template_pkg copy_pkg",
                        "/copy-dir template_pkg copy_pkg",
                        "/check-copy-dirs template_a copy_a template_b copy_b",
                        "/copy-dirs template_a copy_a template_b copy_b",
                        "/check-mkdir pkg/generated",
                        "/mkdir pkg/generated",
                        "/check-mkdirs pkg/generated assets/icons",
                        "/mkdirs pkg/generated assets/icons",
                        "/check-rmdir pkg/generated",
                        "/rmdir pkg/generated",
                        "/check-rmdirs pkg/generated assets/icons",
                        "/rmdirs pkg/generated assets/icons",
                        "/check-executable tool.sh false",
                        "/set-executable tool.sh true",
                        "/check-patch app.py '@@ -1 +1 @@\\n-old\\n+new\\n'",
                        "/patch app.py '@@ -1 +1 @@\\n-old\\n+new\\n'",
                        "/check-patches '--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'",
                        "/patches '--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'",
                        "/check-regex-replace --ignore-case app.py old new",
                        "/regex-replace --count 1 app.py old new",
                        "/code-deps web",
                        "/code-refs runAgent web",
                        "/code-ref-contexts runAgent web",
                        "/code-defs runAgent web",
                        "/code-rename-preview runAgent executeAgent web",
                        "/code-rename runAgent executeAgent web",
                        "/git-status",
                        "/conflicts src",
                        "/git-info",
                        "/branches",
                        "/log app.py 2",
                        "/show HEAD app.py",
                        "/blame app.py 2:2",
                        "/stashes 3",
                        "/check-fetch origin",
                        "/fetch origin",
                        "/check-pull",
                        "/pull",
                        "/check-push",
                        "/push",
                        "/check-stash --include-untracked save work",
                        "/stash save work",
                        "/check-stash-apply stash@{0}",
                        "/stash-apply stash@{0}",
                        "/check-stash-drop stash@{0}",
                        "/stash-drop stash@{0}",
                        "/check-stage app.py",
                        "/stage app.py",
                        "/check-unstage app.py",
                        "/unstage app.py",
                        "/check-commit update app",
                        "/commit update app",
                        "/check-restore app.py",
                        "/restore app.py",
                        "/check-switch --create feature/demo",
                        "/switch feature/demo",
                        "/env",
                        "/processes",
                        "/process bg-1 2000",
                        "/process-output-contexts bg-1 2000",
                        "/process-output-diagnostics bg-1 2000",
                        "/wait-process bg-1 5000 2000",
                        "/check-write-process bg-1 hello\\n",
                        "/write-process bg-1 hello\\n",
                        "/check-stop-process bg-1",
                        "/stop-process bg-1",
                        "/check-stop-processes",
                        "/stop-processes",
                        "/session run-1",
                        "/last",
                        "/plan run-1",
                        "/transcript run-1",
                        "/checkpoint before tests",
                        "/checkpoints",
                        "/checkpoint-show ckpt-1",
                        "/checkpoint-diff ckpt-1",
                        "/checkpoint-status ckpt-1",
                        "/check-checkpoint-restore ckpt-1",
                        "/checkpoint-restore ckpt-1",
                        "/check-checkpoint-delete ckpt-1",
                        "/checkpoint-delete ckpt-1",
                        "/check-checkpoint-prune 2",
                        "/checkpoint-prune 2",
                        "/resume run-1",
                        "/compact run-1",
                        "/context",
                        "/init",
                        "/clear",
                        "/exit",
                    ],
                )
            )
            create_chat_client = stack.enter_context(patch("vibeagent.cli.create_chat_client"))
            stack.enter_context(patch("vibeagent.cli.get_sessions_text", return_value="Recent sessions:\n  run-1"))
            stack.enter_context(patch("vibeagent.cli.get_usage_text", return_value="Usage:\n  sessions: 1"))
            stack.enter_context(patch("vibeagent.cli.get_cost_text", return_value="Cost:\n  estimatedCostUsd: $0.000001"))
            stack.enter_context(patch("vibeagent.cli.get_doctor_text", return_value="Doctor:\n  provider: minimax"))
            get_config_text = stack.enter_context(patch("vibeagent.cli.get_config_text", return_value="Config:\n  provider: minimax"))
            stack.enter_context(patch("vibeagent.cli.get_review_text", return_value="Review:\n  ready: yes"))
            get_handoff_text = stack.enter_context(patch("vibeagent.cli.get_handoff_text", return_value="Handoff:\n  ready: yes"))
            get_changes_text = stack.enter_context(patch("vibeagent.cli.get_changes_text", return_value="Changes:\n  changedFiles: 1"))
            get_diff_text = stack.enter_context(patch("vibeagent.cli.get_diff_text", return_value="Diff:\n  scope: staged"))
            get_diff_hunks_text = stack.enter_context(patch("vibeagent.cli.get_diff_hunks_text", return_value="Diff hunks:\n  hunks: 1/1"))
            get_diff_contexts_text = stack.enter_context(patch("vibeagent.cli.get_diff_contexts_text", return_value="Diff contexts:\n  contexts: 1/1"))
            stack.enter_context(patch("vibeagent.cli.get_tools_text", return_value="Tools:\n  total: 1"))
            stack.enter_context(patch("vibeagent.cli.get_tool_text", return_value="Tool: read_file"))
            get_tool_search_text = stack.enter_context(patch("vibeagent.cli.get_tool_search_text", return_value="Tool search:\n  matches: 1/1"))
            get_permissions_text = stack.enter_context(patch("vibeagent.cli.get_permissions_text", return_value="Permissions:\n  approvalPolicy: ask"))
            get_checks_text = stack.enter_context(patch("vibeagent.cli.get_checks_text", return_value="Checks:\n  suggestedChecks: 1/1"))
            get_commands_text = stack.enter_context(patch("vibeagent.cli.get_commands_text", return_value="Project commands:\n  commands: 1/1"))
            get_related_tests_text = stack.enter_context(patch("vibeagent.cli.get_related_tests_text", return_value="Related tests:\n  candidates: 1/1"))
            get_focused_test_commands_text = stack.enter_context(patch("vibeagent.cli.get_focused_test_commands_text", return_value="Focused test commands:\n  commands: 1/1"))
            get_check_focused_test_commands_text = stack.enter_context(patch("vibeagent.cli.get_check_focused_test_commands_text", return_value="Check focused test commands:\n  ok: yes"))
            get_run_focused_test_commands_text = stack.enter_context(patch("vibeagent.cli.get_run_focused_test_commands_text", return_value="Run focused test commands:\n  ok: yes"))
            get_manifests_text = stack.enter_context(patch("vibeagent.cli.get_manifests_text", return_value="Manifests:\n  files: 1/1"))
            get_command_check_text = stack.enter_context(patch("vibeagent.cli.get_command_check_text", return_value="Command check:\n  ok: yes"))
            get_run_text = stack.enter_context(patch("vibeagent.cli.get_run_text", return_value="Run:\n  ok: yes"))
            get_check_run_sequence_text = stack.enter_context(patch("vibeagent.cli.get_check_run_sequence_text", return_value="Check run sequence:\n  ok: yes"))
            get_run_sequence_text = stack.enter_context(patch("vibeagent.cli.get_run_sequence_text", return_value="Run sequence:\n  ok: yes"))
            get_check_start_text = stack.enter_context(patch("vibeagent.cli.get_check_start_text", return_value="Check start:\n  ok: yes"))
            get_start_text = stack.enter_context(patch("vibeagent.cli.get_start_text", return_value="Start:\n  ok: yes"))
            get_port_text = stack.enter_context(patch("vibeagent.cli.get_port_text", return_value="Port:\n  ok: yes"))
            get_http_text = stack.enter_context(patch("vibeagent.cli.get_http_text", return_value="HTTP:\n  ok: yes"))
            get_http_fetch_text = stack.enter_context(patch("vibeagent.cli.get_http_fetch_text", return_value="HTTP fetch:\n  ok: yes"))
            get_overview_text = stack.enter_context(patch("vibeagent.cli.get_overview_text", return_value="Overview:\n  files: 1/1"))
            get_repo_map_text = stack.enter_context(patch("vibeagent.cli.get_repo_map_text", return_value="Repo map:\n  files: 1/1"))
            get_search_text = stack.enter_context(patch("vibeagent.cli.get_search_text", return_value="Search:\n  matches: 1/1"))
            get_search_contexts_text = stack.enter_context(patch("vibeagent.cli.get_search_contexts_text", return_value="Search contexts:\n  contexts: 1/1"))
            get_glob_text = stack.enter_context(patch("vibeagent.cli.get_glob_text", return_value="Glob:\n  matches: 1/1"))
            get_tree_text = stack.enter_context(patch("vibeagent.cli.get_tree_text", return_value="Tree:\n  entries: 1/1"))
            get_symbols_text = stack.enter_context(patch("vibeagent.cli.get_symbols_text", return_value="Symbols:\n  files: 1/1"))
            get_file_info_text = stack.enter_context(patch("vibeagent.cli.get_file_info_text", return_value="File info:\n  paths: 1/1"))
            get_image_info_text = stack.enter_context(patch("vibeagent.cli.get_image_info_text", return_value="Image info:\n  images: 1/1"))
            get_read_text = stack.enter_context(patch("vibeagent.cli.get_read_text", return_value="Read:\n  ok: yes"))
            get_around_text = stack.enter_context(patch("vibeagent.cli.get_around_text", return_value="Around:\n  ok: yes"))
            get_around_many_text = stack.enter_context(patch("vibeagent.cli.get_around_many_text", return_value="Around many:\n  contexts: 2/2"))
            get_output_contexts_text = stack.enter_context(patch("vibeagent.cli.get_output_contexts_text", return_value="Output contexts:\n  contexts: 1/1"))
            get_output_diagnostics_text = stack.enter_context(patch("vibeagent.cli.get_output_diagnostics_text", return_value="Output diagnostics:\n  diagnostics: 1/1"))
            get_python_traceback_text = stack.enter_context(patch("vibeagent.cli.get_python_traceback_text", return_value="Python traceback:\n  diagnostics: 1/1"))
            get_tail_text = stack.enter_context(patch("vibeagent.cli.get_tail_text", return_value="Tail:\n  ok: yes"))
            get_read_files_text = stack.enter_context(patch("vibeagent.cli.get_read_files_text", return_value="Read files:\n  files: 2/2"))
            get_read_ranges_text = stack.enter_context(patch("vibeagent.cli.get_read_ranges_text", return_value="Read ranges:\n  ranges: 2/2"))
            get_python_check_text = stack.enter_context(patch("vibeagent.cli.get_python_check_text", return_value="Python check:\n  ok: yes"))
            get_python_deps_text = stack.enter_context(patch("vibeagent.cli.get_python_deps_text", return_value="Python dependencies:\n  files: 1/1"))
            get_python_defs_text = stack.enter_context(patch("vibeagent.cli.get_python_defs_text", return_value="Python definitions:\n  definitions: 1/1"))
            get_python_refs_text = stack.enter_context(patch("vibeagent.cli.get_python_refs_text", return_value="Python references:\n  references: 1/1"))
            get_python_ref_contexts_text = stack.enter_context(patch("vibeagent.cli.get_python_ref_contexts_text", return_value="Python reference contexts:\n  contexts: 1/1"))
            get_python_calls_text = stack.enter_context(patch("vibeagent.cli.get_python_calls_text", return_value="Python calls:\n  calls: 1/1"))
            get_python_call_graph_text = stack.enter_context(patch("vibeagent.cli.get_python_call_graph_text", return_value="Python call graph:\n  edges: 3/3"))
            get_python_rename_preview_text = stack.enter_context(patch("vibeagent.cli.get_python_rename_preview_text", return_value="Python rename preview:\n  replacements: 2"))
            get_python_rename_text = stack.enter_context(patch("vibeagent.cli.get_python_rename_text", return_value="Python rename:\n  replacements: 2"))
            get_check_replace_python_definition_text = stack.enter_context(patch("vibeagent.cli.get_check_replace_python_definition_text", return_value="Check replace Python definition:\n  ok: yes"))
            get_replace_python_definition_text = stack.enter_context(patch("vibeagent.cli.get_replace_python_definition_text", return_value="Replace Python definition:\n  ok: yes"))
            get_config_check_text = stack.enter_context(patch("vibeagent.cli.get_config_check_text", return_value="Config check:\n  ok: yes"))
            get_check_json_set_text = stack.enter_context(patch("vibeagent.cli.get_check_json_set_text", return_value="Check JSON set:\n  ok: yes"))
            get_json_set_text = stack.enter_context(patch("vibeagent.cli.get_json_set_text", return_value="JSON set:\n  ok: yes"))
            get_check_json_remove_text = stack.enter_context(patch("vibeagent.cli.get_check_json_remove_text", return_value="Check JSON remove:\n  ok: yes"))
            get_json_remove_text = stack.enter_context(patch("vibeagent.cli.get_json_remove_text", return_value="JSON remove:\n  ok: yes"))
            get_check_json_patch_text = stack.enter_context(patch("vibeagent.cli.get_check_json_patch_text", return_value="Check JSON patch:\n  ok: yes"))
            get_json_patch_text = stack.enter_context(patch("vibeagent.cli.get_json_patch_text", return_value="JSON patch:\n  ok: yes"))
            get_check_replace_lines_text = stack.enter_context(patch("vibeagent.cli.get_check_replace_lines_text", return_value="Check replace lines:\n  ok: yes"))
            get_replace_lines_text = stack.enter_context(patch("vibeagent.cli.get_replace_lines_text", return_value="Replace lines:\n  ok: yes"))
            get_check_insert_lines_text = stack.enter_context(patch("vibeagent.cli.get_check_insert_lines_text", return_value="Check insert lines:\n  ok: yes"))
            get_insert_lines_text = stack.enter_context(patch("vibeagent.cli.get_insert_lines_text", return_value="Insert lines:\n  ok: yes"))
            get_check_append_file_text = stack.enter_context(patch("vibeagent.cli.get_check_append_file_text", return_value="Check append:\n  ok: yes"))
            get_append_file_text = stack.enter_context(patch("vibeagent.cli.get_append_file_text", return_value="Append:\n  ok: yes"))
            get_check_write_file_text = stack.enter_context(patch("vibeagent.cli.get_check_write_file_text", return_value="Check write:\n  ok: yes"))
            get_write_file_text = stack.enter_context(patch("vibeagent.cli.get_write_file_text", return_value="Write:\n  ok: yes"))
            get_check_write_files_text = stack.enter_context(patch("vibeagent.cli.get_check_write_files_text", return_value="Check write files:\n  ok: yes"))
            get_write_files_text = stack.enter_context(patch("vibeagent.cli.get_write_files_text", return_value="Write files:\n  ok: yes"))
            get_check_edit_file_text = stack.enter_context(patch("vibeagent.cli.get_check_edit_file_text", return_value="Check edit:\n  ok: yes"))
            get_edit_file_text = stack.enter_context(patch("vibeagent.cli.get_edit_file_text", return_value="Edit:\n  ok: yes"))
            get_check_multi_edit_file_text = stack.enter_context(patch("vibeagent.cli.get_check_multi_edit_file_text", return_value="Check multi edit:\n  ok: yes"))
            get_multi_edit_file_text = stack.enter_context(patch("vibeagent.cli.get_multi_edit_file_text", return_value="Multi edit:\n  ok: yes"))
            get_check_delete_file_text = stack.enter_context(patch("vibeagent.cli.get_check_delete_file_text", return_value="Check delete:\n  ok: yes"))
            get_delete_file_text = stack.enter_context(patch("vibeagent.cli.get_delete_file_text", return_value="Delete:\n  ok: yes"))
            get_check_delete_files_text = stack.enter_context(patch("vibeagent.cli.get_check_delete_files_text", return_value="Check delete files:\n  ok: yes"))
            get_delete_files_text = stack.enter_context(patch("vibeagent.cli.get_delete_files_text", return_value="Delete files:\n  ok: yes"))
            get_check_move_file_text = stack.enter_context(patch("vibeagent.cli.get_check_move_file_text", return_value="Check move:\n  ok: yes"))
            get_move_file_text = stack.enter_context(patch("vibeagent.cli.get_move_file_text", return_value="Move:\n  ok: yes"))
            get_check_move_files_text = stack.enter_context(patch("vibeagent.cli.get_check_move_files_text", return_value="Check move files:\n  ok: yes"))
            get_move_files_text = stack.enter_context(patch("vibeagent.cli.get_move_files_text", return_value="Move files:\n  ok: yes"))
            get_check_copy_file_text = stack.enter_context(patch("vibeagent.cli.get_check_copy_file_text", return_value="Check copy:\n  ok: yes"))
            get_copy_file_text = stack.enter_context(patch("vibeagent.cli.get_copy_file_text", return_value="Copy:\n  ok: yes"))
            get_check_copy_files_text = stack.enter_context(patch("vibeagent.cli.get_check_copy_files_text", return_value="Check copy files:\n  ok: yes"))
            get_copy_files_text = stack.enter_context(patch("vibeagent.cli.get_copy_files_text", return_value="Copy files:\n  ok: yes"))
            get_check_move_dir_text = stack.enter_context(patch("vibeagent.cli.get_check_move_dir_text", return_value="Check move dir:\n  ok: yes"))
            get_move_dir_text = stack.enter_context(patch("vibeagent.cli.get_move_dir_text", return_value="Move dir:\n  ok: yes"))
            get_check_move_dirs_text = stack.enter_context(patch("vibeagent.cli.get_check_move_dirs_text", return_value="Check move dirs:\n  ok: yes"))
            get_move_dirs_text = stack.enter_context(patch("vibeagent.cli.get_move_dirs_text", return_value="Move dirs:\n  ok: yes"))
            get_check_copy_dir_text = stack.enter_context(patch("vibeagent.cli.get_check_copy_dir_text", return_value="Check copy dir:\n  ok: yes"))
            get_copy_dir_text = stack.enter_context(patch("vibeagent.cli.get_copy_dir_text", return_value="Copy dir:\n  ok: yes"))
            get_check_copy_dirs_text = stack.enter_context(patch("vibeagent.cli.get_check_copy_dirs_text", return_value="Check copy dirs:\n  ok: yes"))
            get_copy_dirs_text = stack.enter_context(patch("vibeagent.cli.get_copy_dirs_text", return_value="Copy dirs:\n  ok: yes"))
            get_check_create_dir_text = stack.enter_context(patch("vibeagent.cli.get_check_create_dir_text", return_value="Check mkdir:\n  ok: yes"))
            get_create_dir_text = stack.enter_context(patch("vibeagent.cli.get_create_dir_text", return_value="Mkdir:\n  ok: yes"))
            get_check_create_dirs_text = stack.enter_context(patch("vibeagent.cli.get_check_create_dirs_text", return_value="Check mkdirs:\n  ok: yes"))
            get_create_dirs_text = stack.enter_context(patch("vibeagent.cli.get_create_dirs_text", return_value="Mkdirs:\n  ok: yes"))
            get_check_delete_empty_dir_text = stack.enter_context(patch("vibeagent.cli.get_check_delete_empty_dir_text", return_value="Check rmdir:\n  ok: yes"))
            get_delete_empty_dir_text = stack.enter_context(patch("vibeagent.cli.get_delete_empty_dir_text", return_value="Rmdir:\n  ok: yes"))
            get_check_delete_empty_dirs_text = stack.enter_context(patch("vibeagent.cli.get_check_delete_empty_dirs_text", return_value="Check rmdirs:\n  ok: yes"))
            get_delete_empty_dirs_text = stack.enter_context(patch("vibeagent.cli.get_delete_empty_dirs_text", return_value="Rmdirs:\n  ok: yes"))
            get_check_set_executable_text = stack.enter_context(patch("vibeagent.cli.get_check_set_executable_text", return_value="Check executable:\n  ok: yes"))
            get_set_executable_text = stack.enter_context(patch("vibeagent.cli.get_set_executable_text", return_value="Set executable:\n  ok: yes"))
            get_check_patch_text = stack.enter_context(patch("vibeagent.cli.get_check_patch_text", return_value="Check patch:\n  ok: yes"))
            get_patch_text = stack.enter_context(patch("vibeagent.cli.get_patch_text", return_value="Patch:\n  ok: yes"))
            get_check_patches_text = stack.enter_context(patch("vibeagent.cli.get_check_patches_text", return_value="Check patches:\n  ok: yes"))
            get_patches_text = stack.enter_context(patch("vibeagent.cli.get_patches_text", return_value="Patches:\n  ok: yes"))
            get_check_regex_replace_text = stack.enter_context(patch("vibeagent.cli.get_check_regex_replace_text", return_value="Check regex replace:\n  ok: yes"))
            get_regex_replace_text = stack.enter_context(patch("vibeagent.cli.get_regex_replace_text", return_value="Regex replace:\n  ok: yes"))
            get_code_deps_text = stack.enter_context(patch("vibeagent.cli.get_code_deps_text", return_value="Code dependencies:\n  files: 1/1"))
            get_code_refs_text = stack.enter_context(patch("vibeagent.cli.get_code_refs_text", return_value="Code references:\n  references: 1/1"))
            get_code_ref_contexts_text = stack.enter_context(patch("vibeagent.cli.get_code_ref_contexts_text", return_value="Code reference contexts:\n  contexts: 1/1"))
            get_code_defs_text = stack.enter_context(patch("vibeagent.cli.get_code_defs_text", return_value="Code definitions:\n  definitions: 1/1"))
            get_code_rename_preview_text = stack.enter_context(patch("vibeagent.cli.get_code_rename_preview_text", return_value="Code rename preview:\n  replacements: 2"))
            get_code_rename_text = stack.enter_context(patch("vibeagent.cli.get_code_rename_text", return_value="Code rename:\n  replacements: 2"))
            get_git_status_text = stack.enter_context(patch("vibeagent.cli.get_git_status_text", return_value="Git status:\n  ok: yes"))
            get_git_conflicts_text = stack.enter_context(patch("vibeagent.cli.get_git_conflicts_text", return_value="Git conflicts:\n  ok: yes"))
            get_git_info_text = stack.enter_context(patch("vibeagent.cli.get_git_info_text", return_value="Git info:\n  branch: main"))
            get_branches_text = stack.enter_context(patch("vibeagent.cli.get_branches_text", return_value="Branches:\n  current: main"))
            get_log_text = stack.enter_context(patch("vibeagent.cli.get_log_text", return_value="Log:\n  ok: yes"))
            get_show_text = stack.enter_context(patch("vibeagent.cli.get_show_text", return_value="Show:\n  ok: yes"))
            get_blame_text = stack.enter_context(patch("vibeagent.cli.get_blame_text", return_value="Blame:\n  ok: yes"))
            get_stashes_text = stack.enter_context(patch("vibeagent.cli.get_stashes_text", return_value="Stashes:\n  entries: 1/1"))
            get_check_fetch_text = stack.enter_context(patch("vibeagent.cli.get_check_fetch_text", return_value="Check fetch:\n  ok: yes"))
            get_fetch_text = stack.enter_context(patch("vibeagent.cli.get_fetch_text", return_value="Fetch:\n  ok: yes"))
            get_check_pull_text = stack.enter_context(patch("vibeagent.cli.get_check_pull_text", return_value="Check pull:\n  ok: yes"))
            get_pull_text = stack.enter_context(patch("vibeagent.cli.get_pull_text", return_value="Pull:\n  ok: yes"))
            get_check_push_text = stack.enter_context(patch("vibeagent.cli.get_check_push_text", return_value="Check push:\n  ok: yes"))
            get_push_text = stack.enter_context(patch("vibeagent.cli.get_push_text", return_value="Push:\n  ok: yes"))
            get_check_stash_text = stack.enter_context(patch("vibeagent.cli.get_check_stash_text", return_value="Check stash:\n  ok: yes"))
            get_stash_text = stack.enter_context(patch("vibeagent.cli.get_stash_text", return_value="Stash:\n  ok: yes"))
            get_check_stash_apply_text = stack.enter_context(patch("vibeagent.cli.get_check_stash_apply_text", return_value="Check stash apply:\n  ok: yes"))
            get_stash_apply_text = stack.enter_context(patch("vibeagent.cli.get_stash_apply_text", return_value="Stash apply:\n  ok: yes"))
            get_check_stash_drop_text = stack.enter_context(patch("vibeagent.cli.get_check_stash_drop_text", return_value="Check stash drop:\n  ok: yes"))
            get_stash_drop_text = stack.enter_context(patch("vibeagent.cli.get_stash_drop_text", return_value="Stash drop:\n  ok: yes"))
            get_check_stage_text = stack.enter_context(patch("vibeagent.cli.get_check_stage_text", return_value="Check stage:\n  ok: yes"))
            get_stage_text = stack.enter_context(patch("vibeagent.cli.get_stage_text", return_value="Stage:\n  ok: yes"))
            get_check_unstage_text = stack.enter_context(patch("vibeagent.cli.get_check_unstage_text", return_value="Check unstage:\n  ok: yes"))
            get_unstage_text = stack.enter_context(patch("vibeagent.cli.get_unstage_text", return_value="Unstage:\n  ok: yes"))
            get_check_commit_text = stack.enter_context(patch("vibeagent.cli.get_check_commit_text", return_value="Check commit:\n  ok: yes"))
            get_commit_text = stack.enter_context(patch("vibeagent.cli.get_commit_text", return_value="Commit:\n  ok: yes"))
            get_check_restore_text = stack.enter_context(patch("vibeagent.cli.get_check_restore_text", return_value="Check restore:\n  ok: yes"))
            get_restore_text = stack.enter_context(patch("vibeagent.cli.get_restore_text", return_value="Restore:\n  ok: yes"))
            get_check_switch_text = stack.enter_context(patch("vibeagent.cli.get_check_switch_text", return_value="Check switch:\n  ok: yes"))
            get_switch_text = stack.enter_context(patch("vibeagent.cli.get_switch_text", return_value="Switch:\n  ok: yes"))
            get_env_text = stack.enter_context(patch("vibeagent.cli.get_env_text", return_value="Environment:\n  tools: 3/9"))
            get_processes_text = stack.enter_context(patch("vibeagent.cli.get_processes_text", return_value="Processes:\n  processes: 0"))
            get_process_text = stack.enter_context(patch("vibeagent.cli.get_process_text", return_value="Process:\n  ok: no"))
            get_process_output_contexts_text = stack.enter_context(patch("vibeagent.cli.get_process_output_contexts_text", return_value="Process output contexts:\n  contexts: 1/1"))
            get_process_output_diagnostics_text = stack.enter_context(patch("vibeagent.cli.get_process_output_diagnostics_text", return_value="Process output diagnostics:\n  diagnostics: 1/1"))
            get_wait_process_text = stack.enter_context(patch("vibeagent.cli.get_wait_process_text", return_value="Wait process:\n  ok: no"))
            get_check_write_process_text = stack.enter_context(patch("vibeagent.cli.get_check_write_process_text", return_value="Check write process:\n  ok: yes"))
            get_write_process_text = stack.enter_context(patch("vibeagent.cli.get_write_process_text", return_value="Write process:\n  ok: no"))
            get_check_stop_process_text = stack.enter_context(patch("vibeagent.cli.get_check_stop_process_text", return_value="Check stop process:\n  ok: yes"))
            get_stop_process_text = stack.enter_context(patch("vibeagent.cli.get_stop_process_text", return_value="Stop process:\n  ok: no"))
            get_check_stop_all_processes_text = stack.enter_context(patch("vibeagent.cli.get_check_stop_all_processes_text", return_value="Check stop processes:\n  processes: 1"))
            get_stop_all_processes_text = stack.enter_context(patch("vibeagent.cli.get_stop_all_processes_text", return_value="Stop processes:\n  stopped: 1"))
            get_session_text = stack.enter_context(patch("vibeagent.cli.get_session_text", return_value="Session: run-1"))
            stack.enter_context(patch("vibeagent.cli.get_last_session_text", return_value="Session: run-1"))
            get_plan_text = stack.enter_context(patch("vibeagent.cli.get_plan_text", return_value="Plan:\n  session: run-1"))
            get_transcript_text = stack.enter_context(patch("vibeagent.cli.get_transcript_text", return_value="Transcript:\n  session: run-1"))
            get_checkpoint_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_text", return_value="Checkpoint:\n  created: yes"))
            get_checkpoints_text = stack.enter_context(patch("vibeagent.cli.get_checkpoints_text", return_value="Checkpoints:\n  total: 1"))
            get_checkpoint_show_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_show_text", return_value="Checkpoint:\n  id: ckpt-1"))
            get_checkpoint_diff_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_diff_text", return_value="Checkpoint diff:\n  id: ckpt-1"))
            get_checkpoint_status_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_status_text", return_value="Checkpoint status:\n  matches: yes"))
            get_check_checkpoint_restore_text = stack.enter_context(patch("vibeagent.cli.get_check_checkpoint_restore_text", return_value="Check checkpoint restore:\n  ok: yes"))
            get_checkpoint_restore_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_restore_text", return_value="Checkpoint restore:\n  restored: yes"))
            get_check_checkpoint_delete_text = stack.enter_context(patch("vibeagent.cli.get_check_checkpoint_delete_text", return_value="Check checkpoint delete:\n  canDelete: yes"))
            get_checkpoint_delete_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_delete_text", return_value="Checkpoint delete:\n  deleted: yes"))
            get_check_checkpoint_prune_text = stack.enter_context(patch("vibeagent.cli.get_check_checkpoint_prune_text", return_value="Check checkpoint prune:\n  deleteCount: 2"))
            get_checkpoint_prune_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_prune_text", return_value="Checkpoint prune:\n  deleted: 2"))
            stack.enter_context(patch("vibeagent.cli.get_resume_context", return_value=("run-1", "context", "Resume context loaded from session run-1.")))
            stack.enter_context(patch("vibeagent.cli.get_compact_context", return_value=("run-1", "context", "Compacted context loaded from session run-1.")))
            stack.enter_context(patch("vibeagent.cli.get_context_text", return_value="Context:\n  resume: run-1"))
            stack.enter_context(patch("vibeagent.cli.init_project_instructions", return_value="Created AGENTS.md."))
            stack.enter_context(redirect_stdout(stdout))
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Recent sessions:", output)
        self.assertIn("Usage:", output)
        self.assertIn("Cost:", output)
        self.assertIn("Doctor:", output)
        self.assertIn("Config:", output)
        self.assertIn("Review:", output)
        self.assertIn("Handoff:", output)
        self.assertIn("Changes:", output)
        self.assertIn("Diff:", output)
        self.assertIn("Diff hunks:", output)
        self.assertIn("Diff contexts:", output)
        self.assertIn("Tools:", output)
        self.assertIn("Tool: read_file", output)
        self.assertIn("Tool search:", output)
        self.assertIn("Permissions:", output)
        self.assertIn("Checks:", output)
        self.assertIn("Project commands:", output)
        self.assertIn("Related tests:", output)
        self.assertIn("Focused test commands:", output)
        self.assertIn("Check focused test commands:", output)
        self.assertIn("Run focused test commands:", output)
        self.assertIn("Manifests:", output)
        self.assertIn("Command check:", output)
        self.assertIn("Run:", output)
        self.assertIn("Check run sequence:", output)
        self.assertIn("Run sequence:", output)
        self.assertIn("Check start:", output)
        self.assertIn("Start:", output)
        self.assertIn("Port:", output)
        self.assertIn("HTTP:", output)
        self.assertIn("Overview:", output)
        self.assertIn("Repo map:", output)
        self.assertIn("Search:", output)
        self.assertIn("Search contexts:", output)
        self.assertIn("Glob:", output)
        self.assertIn("Tree:", output)
        self.assertIn("Symbols:", output)
        self.assertIn("File info:", output)
        self.assertIn("Read:", output)
        self.assertIn("Output contexts:", output)
        self.assertIn("Output diagnostics:", output)
        self.assertIn("Python traceback:", output)
        self.assertIn("Read files:", output)
        self.assertIn("Read ranges:", output)
        self.assertIn("Python check:", output)
        self.assertIn("Python dependencies:", output)
        self.assertIn("Python definitions:", output)
        self.assertIn("Python references:", output)
        self.assertIn("Python reference contexts:", output)
        self.assertIn("Python calls:", output)
        self.assertIn("Python call graph:", output)
        self.assertIn("Python rename preview:", output)
        self.assertIn("Python rename:", output)
        self.assertIn("Config check:", output)
        self.assertIn("Check JSON set:", output)
        self.assertIn("JSON set:", output)
        self.assertIn("Check JSON remove:", output)
        self.assertIn("JSON remove:", output)
        self.assertIn("Check write:", output)
        self.assertIn("Write:", output)
        self.assertIn("Check write files:", output)
        self.assertIn("Write files:", output)
        self.assertIn("Check edit:", output)
        self.assertIn("Edit:", output)
        self.assertIn("Check multi edit:", output)
        self.assertIn("Multi edit:", output)
        self.assertIn("Check delete:", output)
        self.assertIn("Delete:", output)
        self.assertIn("Check delete files:", output)
        self.assertIn("Delete files:", output)
        self.assertIn("Check move:", output)
        self.assertIn("Move:", output)
        self.assertIn("Check move files:", output)
        self.assertIn("Move files:", output)
        self.assertIn("Check copy:", output)
        self.assertIn("Copy:", output)
        self.assertIn("Check copy files:", output)
        self.assertIn("Copy files:", output)
        self.assertIn("Check move dir:", output)
        self.assertIn("Move dir:", output)
        self.assertIn("Check move dirs:", output)
        self.assertIn("Move dirs:", output)
        self.assertIn("Check copy dir:", output)
        self.assertIn("Copy dir:", output)
        self.assertIn("Check copy dirs:", output)
        self.assertIn("Copy dirs:", output)
        self.assertIn("Check mkdir:", output)
        self.assertIn("Mkdir:", output)
        self.assertIn("Check mkdirs:", output)
        self.assertIn("Mkdirs:", output)
        self.assertIn("Check rmdir:", output)
        self.assertIn("Rmdir:", output)
        self.assertIn("Check rmdirs:", output)
        self.assertIn("Rmdirs:", output)
        self.assertIn("Check executable:", output)
        self.assertIn("Set executable:", output)
        self.assertIn("Check patch:", output)
        self.assertIn("Patch:", output)
        self.assertIn("Check patches:", output)
        self.assertIn("Patches:", output)
        self.assertIn("Code dependencies:", output)
        self.assertIn("Code references:", output)
        self.assertIn("Code reference contexts:", output)
        self.assertIn("Code definitions:", output)
        self.assertIn("Code rename preview:", output)
        self.assertIn("Code rename:", output)
        self.assertIn("Git status:", output)
        self.assertIn("Git conflicts:", output)
        self.assertIn("Git info:", output)
        self.assertIn("Branches:", output)
        self.assertIn("Log:", output)
        self.assertIn("Show:", output)
        self.assertIn("Blame:", output)
        self.assertIn("Stashes:", output)
        self.assertIn("Check fetch:", output)
        self.assertIn("Fetch:", output)
        self.assertIn("Check pull:", output)
        self.assertIn("Pull:", output)
        self.assertIn("Check push:", output)
        self.assertIn("Push:", output)
        self.assertIn("Check stash:", output)
        self.assertIn("Stash:", output)
        self.assertIn("Check stash apply:", output)
        self.assertIn("Stash apply:", output)
        self.assertIn("Check stash drop:", output)
        self.assertIn("Stash drop:", output)
        self.assertIn("Check stage:", output)
        self.assertIn("Stage:", output)
        self.assertIn("Check unstage:", output)
        self.assertIn("Unstage:", output)
        self.assertIn("Check commit:", output)
        self.assertIn("Commit:", output)
        self.assertIn("Check restore:", output)
        self.assertIn("Restore:", output)
        self.assertIn("Check switch:", output)
        self.assertIn("Switch:", output)
        self.assertIn("Environment:", output)
        self.assertIn("Processes:", output)
        self.assertIn("Process:", output)
        self.assertIn("Process output contexts:", output)
        self.assertIn("Process output diagnostics:", output)
        self.assertIn("Wait process:", output)
        self.assertIn("Write process:", output)
        self.assertIn("Check stop process:", output)
        self.assertIn("Stop process:", output)
        self.assertIn("Check stop processes:", output)
        self.assertIn("Stop processes:", output)
        self.assertIn("Session: run-1", output)
        self.assertIn("Plan:", output)
        self.assertIn("Transcript:", output)
        self.assertIn("Checkpoint:", output)
        self.assertIn("Checkpoints:", output)
        self.assertIn("Checkpoint diff:", output)
        self.assertIn("Checkpoint status:", output)
        self.assertIn("Check checkpoint restore:", output)
        self.assertIn("Checkpoint restore:", output)
        self.assertIn("Check checkpoint delete:", output)
        self.assertIn("Checkpoint delete:", output)
        self.assertIn("Check checkpoint prune:", output)
        self.assertIn("Checkpoint prune:", output)
        self.assertIn("Resume context loaded", output)
        self.assertIn("Compacted context loaded", output)
        self.assertIn("Context:", output)
        self.assertIn("Created AGENTS.md.", output)
        self.assertIn("Cleared chat history and resume context.", output)
        get_session_text.assert_called_once_with("run-1")
        get_plan_text.assert_called_once_with(run_id="run-1")
        get_transcript_text.assert_called_once_with(run_id="run-1")
        get_checkpoint_text.assert_called_once_with(label="before tests")
        get_checkpoints_text.assert_called_once_with()
        get_checkpoint_show_text.assert_called_once_with("ckpt-1")
        get_checkpoint_diff_text.assert_called_once_with("ckpt-1")
        get_checkpoint_status_text.assert_called_once_with("ckpt-1")
        get_check_checkpoint_restore_text.assert_called_once_with("ckpt-1")
        get_checkpoint_restore_text.assert_called_once_with("ckpt-1")
        get_check_checkpoint_delete_text.assert_called_once_with("ckpt-1")
        get_checkpoint_delete_text.assert_called_once_with("ckpt-1")
        get_check_checkpoint_prune_text.assert_called_once_with("2")
        get_checkpoint_prune_text.assert_called_once_with("2")
        get_diff_text.assert_called_once_with(argument="--staged app.py", max_chars=12000)
        get_diff_hunks_text.assert_called_once_with(argument="--staged app.py")
        get_diff_contexts_text.assert_called_once_with(argument="--staged app.py")
        get_config_text.assert_called_once_with()
        get_handoff_text.assert_called_once_with()
        get_changes_text.assert_called_once_with()
        get_tool_search_text.assert_called_once_with("verification", max_matches=3, category="session", approval_required=False)
        get_permissions_text.assert_called_once_with("ask", Path.cwd())
        get_checks_text.assert_called_once_with()
        get_commands_text.assert_called_once_with()
        get_related_tests_text.assert_called_once_with(argument="pkg/actions.py")
        get_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py")
        get_check_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py")
        get_run_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py", timeout_ms=30000, max_output_chars=12000)
        get_manifests_text.assert_called_once_with()
        get_command_check_text.assert_called_once_with(command="python3 --version")
        get_run_text.assert_called_once_with(command="python3 --version")
        get_check_run_sequence_text.assert_called_once_with(argument="python3 --version ;; npm test")
        get_run_sequence_text.assert_called_once_with(argument="python3 --version ;; npm test")
        get_check_start_text.assert_called_once_with(command="npm run dev")
        get_start_text.assert_called_once_with(command="npm run dev")
        get_port_text.assert_called_once_with(argument="5173 127.0.0.1 1500")
        get_http_text.assert_called_once_with(argument="http://127.0.0.1:5173 ready")
        get_http_fetch_text.assert_called_once_with(argument="http://127.0.0.1:5173/app")
        get_overview_text.assert_called_once_with()
        get_repo_map_text.assert_called_once_with(path="src")
        get_search_text.assert_called_once_with(query="needle")
        get_search_contexts_text.assert_called_once_with(query="needle")
        get_glob_text.assert_called_once_with(pattern="**/*.py")
        get_tree_text.assert_called_once_with(path="src")
        get_symbols_text.assert_called_once_with(argument="src/app.py web/app.ts")
        get_file_info_text.assert_called_once_with(argument="src/app.py asset.bin")
        get_image_info_text.assert_called_once_with(argument="assets/logo.png")
        get_read_text.assert_called_once_with(argument="src/app.py 2:4")
        get_around_text.assert_called_once_with(argument="src/app.py 42 8")
        get_around_many_text.assert_called_once_with(argument="src/app.py:42:8 tests/test_app.py:17")
        get_output_contexts_text.assert_called_once_with(text="src/app.py:42:8")
        get_output_diagnostics_text.assert_called_once_with(text="ERROR src/app.py:42:8 failed")
        get_python_traceback_text.assert_called_once_with(text="ValueError: bad")
        get_tail_text.assert_called_once_with(argument="logs/app.log 3")
        get_read_files_text.assert_called_once_with(argument="src/app.py tests/test_app.py")
        get_read_ranges_text.assert_called_once_with(argument="src/app.py:2:4 tests/test_app.py:1")
        get_python_check_text.assert_called_once_with(argument="src")
        get_python_deps_text.assert_called_once_with(argument="src")
        get_python_defs_text.assert_called_once_with(argument="Runner.run src")
        get_python_refs_text.assert_called_once_with(argument="run_agent src")
        get_python_ref_contexts_text.assert_called_once_with(argument="run_agent src")
        get_python_calls_text.assert_called_once_with(argument="helper src")
        get_python_call_graph_text.assert_called_once_with(argument="src")
        get_python_rename_preview_text.assert_called_once_with(argument="run_agent execute_agent src")
        get_python_rename_text.assert_called_once_with(argument="run_agent execute_agent src")
        get_check_replace_python_definition_text.assert_called_once_with(argument="Runner.run '    def run(self):\\n        return 2\\n' src")
        get_replace_python_definition_text.assert_called_once_with(argument="Runner.run '    def run(self):\\n        return 2\\n' src")
        get_config_check_text.assert_called_once_with(argument="pyproject.toml")
        get_check_json_set_text.assert_called_once_with(argument="package.json /private true")
        get_json_set_text.assert_called_once_with(argument="package.json /scripts/test '\"npm test\"'")
        get_check_json_remove_text.assert_called_once_with(argument="package.json /scripts/dev")
        get_json_remove_text.assert_called_once_with(argument="package.json /keywords/0")
        get_check_json_patch_text.assert_called_once_with(argument="package.json '[{\"op\":\"replace\",\"path\":\"/private\",\"value\":true}]'")
        get_json_patch_text.assert_called_once_with(argument="package.json '[{\"op\":\"remove\",\"path\":\"/keywords/0\"}]'")
        get_check_replace_lines_text.assert_called_once_with(argument="app.py 2 3 'new\\n'")
        get_replace_lines_text.assert_called_once_with(argument="app.py 2 2 'new\\n'")
        get_check_insert_lines_text.assert_called_once_with(argument="app.py 2 'new\\n'")
        get_insert_lines_text.assert_called_once_with(argument="app.py 2 'new\\n'")
        get_check_append_file_text.assert_called_once_with(argument="app.py 'new\\n'")
        get_append_file_text.assert_called_once_with(argument="app.py 'new\\n'")
        get_check_write_file_text.assert_called_once_with(argument="app.py 'new\\n'")
        get_write_file_text.assert_called_once_with(argument="app.py 'new\\n'")
        get_check_write_files_text.assert_called_once_with(argument="app.py 'a\\n' test.py 'b\\n'")
        get_write_files_text.assert_called_once_with(argument="app.py 'a\\n' test.py 'b\\n'")
        get_check_edit_file_text.assert_called_once_with(argument="app.py old new")
        get_edit_file_text.assert_called_once_with(argument="app.py old new")
        get_check_multi_edit_file_text.assert_called_once_with(argument="app.py old new print log")
        get_multi_edit_file_text.assert_called_once_with(argument="app.py old new print log")
        get_check_delete_file_text.assert_called_once_with(argument="old.py")
        get_delete_file_text.assert_called_once_with(argument="old.py")
        get_check_delete_files_text.assert_called_once_with(argument="old.py other.py")
        get_delete_files_text.assert_called_once_with(argument="old.py other.py")
        get_check_move_file_text.assert_called_once_with(argument="old.py new.py")
        get_move_file_text.assert_called_once_with(argument="old.py new.py")
        get_check_move_files_text.assert_called_once_with(argument="old.py new.py other.py other-new.py")
        get_move_files_text.assert_called_once_with(argument="old.py new.py other.py other-new.py")
        get_check_copy_file_text.assert_called_once_with(argument="template.py new.py")
        get_copy_file_text.assert_called_once_with(argument="template.py new.py")
        get_check_copy_files_text.assert_called_once_with(argument="template.py new.py config.py config-copy.py")
        get_copy_files_text.assert_called_once_with(argument="template.py new.py config.py config-copy.py")
        get_check_move_dir_text.assert_called_once_with(argument="old_pkg new_pkg")
        get_move_dir_text.assert_called_once_with(argument="old_pkg new_pkg")
        get_check_move_dirs_text.assert_called_once_with(argument="old_a new_a old_b new_b")
        get_move_dirs_text.assert_called_once_with(argument="old_a new_a old_b new_b")
        get_check_copy_dir_text.assert_called_once_with(argument="template_pkg copy_pkg")
        get_copy_dir_text.assert_called_once_with(argument="template_pkg copy_pkg")
        get_check_copy_dirs_text.assert_called_once_with(argument="template_a copy_a template_b copy_b")
        get_copy_dirs_text.assert_called_once_with(argument="template_a copy_a template_b copy_b")
        get_check_create_dir_text.assert_called_once_with(argument="pkg/generated")
        get_create_dir_text.assert_called_once_with(argument="pkg/generated")
        get_check_create_dirs_text.assert_called_once_with(argument="pkg/generated assets/icons")
        get_create_dirs_text.assert_called_once_with(argument="pkg/generated assets/icons")
        get_check_delete_empty_dir_text.assert_called_once_with(argument="pkg/generated")
        get_delete_empty_dir_text.assert_called_once_with(argument="pkg/generated")
        get_check_delete_empty_dirs_text.assert_called_once_with(argument="pkg/generated assets/icons")
        get_delete_empty_dirs_text.assert_called_once_with(argument="pkg/generated assets/icons")
        get_check_set_executable_text.assert_called_once_with(argument="tool.sh false")
        get_set_executable_text.assert_called_once_with(argument="tool.sh true")
        get_check_patch_text.assert_called_once_with(argument="app.py '@@ -1 +1 @@\\n-old\\n+new\\n'")
        get_patch_text.assert_called_once_with(argument="app.py '@@ -1 +1 @@\\n-old\\n+new\\n'")
        get_check_patches_text.assert_called_once_with(argument="'--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'")
        get_patches_text.assert_called_once_with(argument="'--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'")
        get_check_regex_replace_text.assert_called_once_with(argument="--ignore-case app.py old new")
        get_regex_replace_text.assert_called_once_with(argument="--count 1 app.py old new")
        get_code_deps_text.assert_called_once_with(argument="web")
        get_code_refs_text.assert_called_once_with(argument="runAgent web")
        get_code_ref_contexts_text.assert_called_once_with(argument="runAgent web")
        get_code_defs_text.assert_called_once_with(argument="runAgent web")
        get_code_rename_preview_text.assert_called_once_with(argument="runAgent executeAgent web")
        get_code_rename_text.assert_called_once_with(argument="runAgent executeAgent web")
        get_git_status_text.assert_called_once_with()
        get_git_conflicts_text.assert_called_once_with(argument="src")
        get_git_info_text.assert_called_once_with()
        get_branches_text.assert_called_once_with()
        get_log_text.assert_called_once_with(argument="app.py 2")
        get_show_text.assert_called_once_with(argument="HEAD app.py")
        get_blame_text.assert_called_once_with(argument="app.py 2:2")
        get_stashes_text.assert_called_once_with(argument="3")
        get_check_fetch_text.assert_called_once_with(argument="origin")
        get_fetch_text.assert_called_once_with(argument="origin")
        get_check_pull_text.assert_called_once_with()
        get_pull_text.assert_called_once_with()
        get_check_push_text.assert_called_once_with()
        get_push_text.assert_called_once_with()
        get_check_stash_text.assert_called_once_with(argument="--include-untracked save work")
        get_stash_text.assert_called_once_with(argument="save work")
        get_check_stash_apply_text.assert_called_once_with(argument="stash@{0}")
        get_stash_apply_text.assert_called_once_with(argument="stash@{0}")
        get_check_stash_drop_text.assert_called_once_with(argument="stash@{0}")
        get_stash_drop_text.assert_called_once_with(argument="stash@{0}")
        get_check_stage_text.assert_called_once_with(argument="app.py")
        get_stage_text.assert_called_once_with(argument="app.py")
        get_check_unstage_text.assert_called_once_with(argument="app.py")
        get_unstage_text.assert_called_once_with(argument="app.py")
        get_check_commit_text.assert_called_once_with(argument="update app")
        get_commit_text.assert_called_once_with(argument="update app")
        get_check_restore_text.assert_called_once_with(argument="app.py")
        get_restore_text.assert_called_once_with(argument="app.py")
        get_check_switch_text.assert_called_once_with(argument="--create feature/demo")
        get_switch_text.assert_called_once_with(argument="feature/demo")
        get_env_text.assert_called_once_with()
        get_processes_text.assert_called_once_with()
        get_process_text.assert_called_once_with(argument="bg-1 2000")
        get_process_output_contexts_text.assert_called_once_with(argument="bg-1 2000")
        get_process_output_diagnostics_text.assert_called_once_with(argument="bg-1 2000")
        get_wait_process_text.assert_called_once_with(argument="bg-1 5000 2000")
        get_check_write_process_text.assert_called_once_with(argument="bg-1 hello\\n")
        get_write_process_text.assert_called_once_with(argument="bg-1 hello\\n")
        get_check_stop_process_text.assert_called_once_with(process_id="bg-1")
        get_stop_process_text.assert_called_once_with(process_id="bg-1")
        get_check_stop_all_processes_text.assert_called_once_with()
        get_stop_all_processes_text.assert_called_once_with()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_checks_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/checks --max-checks 2",
                    "/checks --max-checks=3",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_checks_text", return_value="Checks:\n  suggestedChecks: 1/2") as get_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Checks:", output)
        get_checks_text.assert_has_calls(
            [
                call(max_checks=2),
                call(max_checks=3),
            ]
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_checks_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/checks --max-checks 0",
                    "/checks --unknown 1",
                    "/checks package.json",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_checks_text") as get_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /checks [--max-checks N]", output)
        self.assertIn("--max-checks must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_checks_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_commands_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/commands --max-commands 2 --max-files 3",
                    "/commands --max-commands=4 --max-files=5",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_commands_text", return_value="Project commands:\n  commands: 1/2") as get_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Project commands:", output)
        get_commands_text.assert_has_calls(
            [
                call(max_commands=2, max_files=3),
                call(max_commands=4, max_files=5),
            ]
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_commands_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/commands --max-commands 0",
                    "/commands --max-files 0",
                    "/commands --unknown 1",
                    "/commands package.json",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_commands_text") as get_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /commands [--max-commands N] [--max-files N]", output)
        self.assertIn("--max-commands must be a positive integer.", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_commands_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_manifests_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/manifests --max-files 2 --max-items 10",
                    "/manifests --max-files=3 --max-items=20",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_manifests_text", return_value="Manifests:\n  files: 1/2") as get_manifests_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Manifests:", output)
        get_manifests_text.assert_has_calls(
            [
                call(max_files=2, max_items=10),
                call(max_files=3, max_items=20),
            ]
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_manifests_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/manifests --max-files 0",
                    "/manifests --max-items 0",
                    "/manifests --unknown 1",
                    "/manifests package.json",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_manifests_text") as get_manifests_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /manifests [--max-files N] [--max-items N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("--max-items must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_manifests_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_todos_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/todos src --max-items 3 --max-files 20",
                    "/todos --max-items=4 --max-files=30 -- src",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_todos_text", return_value="Project TODOs:\n  todos: 1/3") as get_todos_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Project TODOs:", output)
        get_todos_text.assert_has_calls(
            [
                call(path="src", max_items=3, max_files=20),
                call(path="src", max_items=4, max_files=30),
            ]
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_instructions_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/instructions --max-files 2 --max-bytes 1000",
                    "/instructions --max-files=3 --max-bytes=1200",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_instructions_text", return_value="Project instructions:\n  files: 1/2") as get_instructions_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Project instructions:", output)
        get_instructions_text.assert_has_calls(
            [
                call(max_files=2, max_bytes=1000),
                call(max_files=3, max_bytes=1200),
            ]
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_instructions_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/instructions --max-files 0",
                    "/instructions --max-bytes 0",
                    "/instructions --unknown 1",
                    "/instructions AGENTS.md",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_instructions_text") as get_instructions_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /instructions [--max-files N] [--max-bytes N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_instructions_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_todos_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/todos --max-items 0 -- src",
                    "/todos --max-files 0 -- src",
                    "/todos --unknown 1 -- src",
                    "/todos src docs --max-items 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_todos_text") as get_todos_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /todos [--max-items N] [--max-files N] -- [path]", output)
        self.assertIn("error: --max-items must be a positive integer.", output)
        self.assertIn("error: --max-files must be a positive integer.", output)
        self.assertIn("error: Unknown option: --unknown", output)
        get_todos_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_python_symbol_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-defs --path src --max-matches 3 --max-lines 40 -- Runner.run",
                    "/python-refs run_agent --path src --max-matches 4",
                    "/python-ref-contexts --path src --max-matches 5 --context-lines 1 --max-bytes 1000 -- run_agent",
                    "/python-calls helper src --max-matches 6",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_python_defs_text", return_value="Python definitions:\n  definitions: 1/1") as get_python_defs_text,
            patch("vibeagent.cli.get_python_refs_text", return_value="Python references:\n  references: 1/1") as get_python_refs_text,
            patch("vibeagent.cli.get_python_ref_contexts_text", return_value="Python reference contexts:\n  contexts: 1/1") as get_python_ref_contexts_text,
            patch("vibeagent.cli.get_python_calls_text", return_value="Python calls:\n  calls: 1/1") as get_python_calls_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Python definitions:", output)
        self.assertIn("Python references:", output)
        self.assertIn("Python reference contexts:", output)
        self.assertIn("Python calls:", output)
        get_python_defs_text.assert_called_once_with(symbol="Runner.run", path="src", max_matches=3, max_lines=40)
        get_python_refs_text.assert_called_once_with(symbol="run_agent", path="src", max_matches=4)
        get_python_ref_contexts_text.assert_called_once_with(
            symbol="run_agent",
            path="src",
            max_matches=5,
            context_lines=1,
            max_bytes_per_context=1000,
        )
        get_python_calls_text.assert_called_once_with(symbol="helper", path="src", max_matches=6)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_python_deps_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-deps --max-files 2 --max-imports=7 -- src",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch(
                "vibeagent.cli.get_python_deps_text",
                return_value="Python dependencies:\n  files: 1/1",
            ) as get_python_deps_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Python dependencies:", output)
        get_python_deps_text.assert_called_once_with(argument="src", max_files=2, max_imports=7)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_python_call_graph_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-call-graph --max-files 2 --max-edges=7 -- src",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_python_call_graph_text", return_value="Python call graph:\n  edges: 3/3") as get_python_call_graph_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Python call graph:", output)
        get_python_call_graph_text.assert_called_once_with(argument="src", max_files=2, max_edges=7)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_python_symbol_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-defs --max-matches 0 -- Runner.run",
                    "/python-defs --max-lines 0 -- Runner.run",
                    "/python-defs --path src Runner.run src",
                    "/python-refs --max-matches 0 -- run_agent",
                    "/python-ref-contexts --context-lines -1 -- run_agent",
                    "/python-ref-contexts --max-bytes 0 -- run_agent",
                    "/python-ref-contexts --unknown 1 -- run_agent",
                    "/python-calls --max-matches 0 -- helper",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_python_defs_text") as get_python_defs_text,
            patch("vibeagent.cli.get_python_refs_text") as get_python_refs_text,
            patch("vibeagent.cli.get_python_ref_contexts_text") as get_python_ref_contexts_text,
            patch("vibeagent.cli.get_python_calls_text") as get_python_calls_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /python-defs [--path PATH] [--max-matches N] [--max-lines N] -- <symbol> [path]", output)
        self.assertIn("Usage: /python-refs [--path PATH] [--max-matches N] -- <symbol> [path]", output)
        self.assertIn(
            "Usage: /python-ref-contexts [--path PATH] [--max-matches N] [--context-lines N] [--max-bytes N] -- <symbol> [path]",
            output,
        )
        self.assertIn("Usage: /python-calls [--path PATH] [--max-matches N] -- <symbol> [path]", output)
        self.assertIn("error: --max-matches must be a positive integer.", output)
        self.assertIn("error: --max-lines must be a positive integer.", output)
        self.assertIn("error: path can only be provided once.", output)
        self.assertIn("error: --context-lines must be a non-negative integer.", output)
        self.assertIn("error: --max-bytes must be a positive integer.", output)
        self.assertIn("error: Unknown option: --unknown", output)
        get_python_defs_text.assert_not_called()
        get_python_refs_text.assert_not_called()
        get_python_ref_contexts_text.assert_not_called()
        get_python_calls_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_python_deps_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-deps --max-files 0 -- src",
                    "/python-deps --max-imports 0 -- src",
                    "/python-deps --unknown 1 -- src",
                    "/python-deps src tests --max-files 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_python_deps_text") as get_python_deps_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /python-deps [--max-files N] [--max-imports N] -- [path]", output)
        self.assertIn("error: --max-files must be a positive integer.", output)
        self.assertIn("error: --max-imports must be a positive integer.", output)
        self.assertIn("error: Unknown option: --unknown", output)
        get_python_deps_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_python_call_graph_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-call-graph --max-files 0 -- src",
                    "/python-call-graph --max-edges 0 -- src",
                    "/python-call-graph --unknown 1 -- src",
                    "/python-call-graph src tests --max-files 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_python_call_graph_text") as get_python_call_graph_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /python-call-graph [--max-files N] [--max-edges N] -- [path]", output)
        self.assertIn("error: --max-files must be a positive integer.", output)
        self.assertIn("error: --max-edges must be a positive integer.", output)
        self.assertIn("error: Unknown option: --unknown", output)
        get_python_call_graph_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_code_symbol_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/code-refs runAgent --path web --max-matches 4",
                    "/code-ref-contexts --path web --max-matches 5 --context-lines 1 --max-bytes 1000 -- runAgent",
                    "/code-defs --path web --max-matches 6 --max-lines 40 -- runAgent",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_code_refs_text", return_value="Code references:\n  references: 1/1") as get_code_refs_text,
            patch("vibeagent.cli.get_code_ref_contexts_text", return_value="Code reference contexts:\n  contexts: 1/1") as get_code_ref_contexts_text,
            patch("vibeagent.cli.get_code_defs_text", return_value="Code definitions:\n  definitions: 1/1") as get_code_defs_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Code references:", output)
        self.assertIn("Code reference contexts:", output)
        self.assertIn("Code definitions:", output)
        get_code_refs_text.assert_called_once_with(symbol="runAgent", path="web", max_matches=4)
        get_code_ref_contexts_text.assert_called_once_with(
            symbol="runAgent",
            path="web",
            max_matches=5,
            context_lines=1,
            max_bytes_per_context=1000,
        )
        get_code_defs_text.assert_called_once_with(symbol="runAgent", path="web", max_matches=6, max_lines=40)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_code_symbol_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/code-refs --max-matches 0 -- runAgent",
                    "/code-ref-contexts --context-lines -1 -- runAgent",
                    "/code-ref-contexts --max-bytes 0 -- runAgent",
                    "/code-ref-contexts --unknown 1 -- runAgent",
                    "/code-defs --max-lines 0 -- runAgent",
                    "/code-defs --path web runAgent web",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_code_refs_text") as get_code_refs_text,
            patch("vibeagent.cli.get_code_ref_contexts_text") as get_code_ref_contexts_text,
            patch("vibeagent.cli.get_code_defs_text") as get_code_defs_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /code-refs [--path PATH] [--max-matches N] -- <symbol> [path]", output)
        self.assertIn(
            "Usage: /code-ref-contexts [--path PATH] [--max-matches N] [--context-lines N] [--max-bytes N] -- <symbol> [path]",
            output,
        )
        self.assertIn("Usage: /code-defs [--path PATH] [--max-matches N] [--max-lines N] -- <symbol> [path]", output)
        self.assertIn("error: --max-matches must be a positive integer.", output)
        self.assertIn("error: --context-lines must be a non-negative integer.", output)
        self.assertIn("error: --max-bytes must be a positive integer.", output)
        self.assertIn("error: Unknown option: --unknown", output)
        self.assertIn("error: --max-lines must be a positive integer.", output)
        self.assertIn("error: path can only be provided once.", output)
        get_code_refs_text.assert_not_called()
        get_code_ref_contexts_text.assert_not_called()
        get_code_defs_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_session_timeline_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/transcript run-1 --max-events 3 --max-text 120",
                    '/session-search --run run-1 --max-matches 4 --case-sensitive --max-text 140 "Missing config"',
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_transcript_text", return_value="Transcript:\n  session: run-1") as get_transcript_text,
            patch("vibeagent.cli.get_session_search_text", return_value="Session search:\n  session: run-1") as get_session_search_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Transcript:", output)
        self.assertIn("Session search:", output)
        get_transcript_text.assert_called_once_with(run_id="run-1", max_events=3, max_text=120)
        get_session_search_text.assert_called_once_with(
            argument="Missing config",
            run_id="run-1",
            max_matches=4,
            case_sensitive=True,
            max_text=140,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_session_timeline_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/transcript --max-events nope",
                    "/session-search --max-matches 0 needle",
                    "/session-search --unknown needle",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_transcript_text") as get_transcript_text,
            patch("vibeagent.cli.get_session_search_text") as get_session_search_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /transcript [run-id] [--max-events N] [--max-text N]", output)
        self.assertIn("--max-events must be a positive integer.", output)
        self.assertIn("Usage: /session-search [--run run-id] [--max-matches N] [--case-sensitive] [--max-text N] <query>", output)
        self.assertIn("--max-matches must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_transcript_text.assert_not_called()
        get_session_search_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_session_output_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/session-output-contexts run-1 --max-commands 2 --max-output-chars 120 --context-lines 0 --max-contexts 3 --max-bytes 1000",
                    "/session-output-diagnostics run-1 --max-commands 4 --max-output-chars 140 --context-lines 1 --max-diagnostics 5 --max-contexts 6 --max-bytes 1200",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_session_output_contexts_text", return_value="Session output contexts:\n  session: run-1") as get_session_output_contexts_text,
            patch("vibeagent.cli.get_session_output_diagnostics_text", return_value="Session output diagnostics:\n  session: run-1") as get_session_output_diagnostics_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Session output contexts:", output)
        self.assertIn("Session output diagnostics:", output)
        get_session_output_contexts_text.assert_called_once_with(
            run_id="run-1",
            max_commands=2,
            max_output_chars=120,
            context_lines=0,
            max_contexts=3,
            max_bytes_per_context=1000,
        )
        get_session_output_diagnostics_text.assert_called_once_with(
            run_id="run-1",
            max_commands=4,
            max_output_chars=140,
            context_lines=1,
            max_diagnostics=5,
            max_contexts=6,
            max_bytes_per_context=1200,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_session_output_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/session-output-contexts --context-lines -1",
                    "/session-output-diagnostics --max-diagnostics 0",
                    "/session-output-contexts --max-diagnostics 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_session_output_contexts_text") as get_session_output_contexts_text,
            patch("vibeagent.cli.get_session_output_diagnostics_text") as get_session_output_diagnostics_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /session-output-contexts [run-id]", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("Usage: /session-output-diagnostics [run-id]", output)
        self.assertIn("--max-diagnostics must be a positive integer.", output)
        self.assertIn("Unknown option: --max-diagnostics", output)
        get_session_output_contexts_text.assert_not_called()
        get_session_output_diagnostics_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_process_output_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/process-output-contexts bg-1 --max-chars 120 --context-lines 0 --max-contexts 3 --max-bytes 1000",
                    "/process-output-diagnostics bg-1 140 --context-lines 1 --max-diagnostics 4 --max-contexts 5 --max-bytes 1200",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_process_output_contexts_text", return_value="Process output contexts:\n  contexts: 1/1") as get_process_output_contexts_text,
            patch("vibeagent.cli.get_process_output_diagnostics_text", return_value="Process output diagnostics:\n  diagnostics: 1/1") as get_process_output_diagnostics_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Process output contexts:", output)
        self.assertIn("Process output diagnostics:", output)
        get_process_output_contexts_text.assert_called_once_with(
            process_id="bg-1",
            max_output_chars=120,
            context_lines=0,
            max_contexts=3,
            max_bytes_per_context=1000,
        )
        get_process_output_diagnostics_text.assert_called_once_with(
            process_id="bg-1",
            max_output_chars=140,
            context_lines=1,
            max_diagnostics=4,
            max_contexts=5,
            max_bytes_per_context=1200,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_process_output_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/process-output-contexts --context-lines -1 bg-1",
                    "/process-output-diagnostics bg-1 --max-diagnostics 0",
                    "/process-output-contexts bg-1 --max-diagnostics 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_process_output_contexts_text") as get_process_output_contexts_text,
            patch("vibeagent.cli.get_process_output_diagnostics_text") as get_process_output_diagnostics_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /process-output-contexts <id> [chars]", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("Usage: /process-output-diagnostics <id> [chars]", output)
        self.assertIn("--max-diagnostics must be a positive integer.", output)
        self.assertIn("Unknown option: --max-diagnostics", output)
        get_process_output_contexts_text.assert_not_called()
        get_process_output_diagnostics_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_port_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/port 5173 --host 0.0.0.0 --timeout-ms 1500",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_port_text", return_value="Port:\n  reachable: yes") as get_port_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Port:", output)
        get_port_text.assert_called_once_with(port=5173, host="0.0.0.0", timeout_ms=1500)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_port_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/port --host 127.0.0.1",
                    "/port 5173 --timeout-ms 99",
                    "/port 5173 --host",
                    "/port 5173 --unknown 1",
                    "/port 5173 extra --host 127.0.0.1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_port_text") as get_port_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /port <port> [host] [timeout-ms]", output)
        self.assertIn("port is required.", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--host requires a value.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_port_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_http_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/http http://127.0.0.1:5173 ready --timeout-ms 1500 --max-body-chars 1000 --regex",
                    "/http-fetch --timeout-ms 2500 --max-body-chars 4000 -- http://127.0.0.1:5173/app",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_http_text", return_value="HTTP:\n  matched: yes") as get_http_text,
            patch("vibeagent.cli.get_http_fetch_text", return_value="HTTP fetch:\n  ok: yes") as get_http_fetch_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("HTTP:", output)
        self.assertIn("HTTP fetch:", output)
        get_http_text.assert_called_once_with(
            url="http://127.0.0.1:5173",
            contains="ready",
            timeout_ms=1500,
            max_body_chars=1000,
            regex=True,
        )
        get_http_fetch_text.assert_called_once_with(
            url="http://127.0.0.1:5173/app",
            timeout_ms=2500,
            max_body_chars=4000,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_http_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/http --timeout-ms 99 -- http://127.0.0.1:5173",
                    "/http http://127.0.0.1:5173 --contains",
                    "/http --contains ready",
                    "/http http://127.0.0.1:5173 --unknown 1",
                    "/http-fetch --max-body-chars 0 -- http://127.0.0.1:5173/app",
                    "/http-fetch http://127.0.0.1:5173/app extra --timeout-ms 1000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_http_text") as get_http_text,
            patch("vibeagent.cli.get_http_fetch_text") as get_http_fetch_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /http <url> [contains]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--contains requires a value.", output)
        self.assertIn("url is required.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("Usage: /http-fetch <url>", output)
        self.assertIn("--max-body-chars must be a positive integer.", output)
        get_http_text.assert_not_called()
        get_http_fetch_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_search_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/search --path src --max-matches 5 --regex --ignore-case --context-lines 1 -- needle.+",
                    "/search-contexts needle --path tests --max-matches 3 --context-lines 2 --max-bytes 1000 --case-sensitive",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_search_text", return_value="Search:\n  matches: 1/1") as get_search_text,
            patch("vibeagent.cli.get_search_contexts_text", return_value="Search contexts:\n  contexts: 1/1") as get_search_contexts_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Search:", output)
        self.assertIn("Search contexts:", output)
        get_search_text.assert_called_once_with(
            query="needle.+",
            path="src",
            max_matches=5,
            regex=True,
            case_sensitive=False,
            context_lines=1,
        )
        get_search_contexts_text.assert_called_once_with(
            query="needle",
            path="tests",
            max_matches=3,
            context_lines=2,
            max_bytes_per_context=1000,
            case_sensitive=True,
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_find_files_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/find-files --path src --max-matches 5 --regex --case-sensitive --include-dirs -- app.+",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_find_files_text", return_value="Find Files:\n  matches: 1/1") as get_find_files_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Find Files:", output)
        get_find_files_text.assert_called_once_with(
            query="app.+",
            path="src",
            max_matches=5,
            regex=True,
            case_sensitive=True,
            include_dirs=True,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_search_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/search --path src",
                    "/search needle --max-matches 0",
                    "/search needle --regex=true",
                    "/search needle --max-bytes 1000",
                    "/search-contexts needle --context-lines -1",
                    "/search-contexts needle --max-bytes 0",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_search_text") as get_search_text,
            patch("vibeagent.cli.get_search_contexts_text") as get_search_contexts_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /search [--path PATH]", output)
        self.assertIn("query is required.", output)
        self.assertIn("--max-matches must be a positive integer.", output)
        self.assertIn("--regex does not take a value.", output)
        self.assertIn("Unknown option: --max-bytes", output)
        self.assertIn("Usage: /search-contexts [--path PATH]", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        get_search_text.assert_not_called()
        get_search_contexts_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_find_files_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/find-files --path src",
                    "/find-files app --max-matches 0",
                    "/find-files app --regex=true",
                    "/find-files app --unknown",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_find_files_text") as get_find_files_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /find-files [--path PATH]", output)
        self.assertIn("query is required.", output)
        self.assertIn("--max-matches must be a positive integer.", output)
        self.assertIn("--regex does not take a value.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_find_files_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_overview_repo_map_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/overview --max-files 7 --max-commands 3 --max-checks 2",
                    "/repo-map src --max-depth 2 --max-files 8 --max-symbols 9",
                    "/repo-map --max-depth=0 --max-files=4 --max-symbols=5",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_overview_text", return_value="Overview:\n  files: 1/1") as get_overview_text,
            patch("vibeagent.cli.get_repo_map_text", return_value="Repo map:\n  files: 1/1") as get_repo_map_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Overview:", output)
        self.assertIn("Repo map:", output)
        get_overview_text.assert_called_once_with(max_files=7, max_commands=3, max_checks=2)
        self.assertEqual(
            get_repo_map_text.call_args_list,
            [
                call(path="src", max_depth=2, max_files=8, max_symbols=9),
                call(path=None, max_depth=0, max_files=4, max_symbols=5),
            ],
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_overview_repo_map_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/overview --max-files 0",
                    "/overview --unknown 1",
                    "/overview unexpected --max-files 1",
                    "/repo-map src --max-depth -1",
                    "/repo-map src --max-files 0",
                    "/repo-map src --max-symbols 0",
                    "/repo-map src other --max-depth 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_overview_text") as get_overview_text,
            patch("vibeagent.cli.get_repo_map_text") as get_repo_map_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /overview [--max-files N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("Usage: /repo-map [path] [--max-depth N]", output)
        self.assertIn("--max-depth must be a non-negative integer.", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("--max-symbols must be a positive integer.", output)
        get_overview_text.assert_not_called()
        get_repo_map_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_glob_tree_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/glob --max-matches 7 --include-dirs -- **/*.py",
                    "/tree src --max-depth 2 --max-entries 30",
                    "/tree --max-depth=0 --max-entries=5",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_glob_text", return_value="Glob:\n  matches: 1/1") as get_glob_text,
            patch("vibeagent.cli.get_tree_text", return_value="Tree:\n  entries: 1/1") as get_tree_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Glob:", output)
        self.assertIn("Tree:", output)
        get_glob_text.assert_called_once_with(pattern="**/*.py", max_matches=7, include_dirs=True)
        self.assertEqual(
            get_tree_text.call_args_list,
            [
                call(path="src", max_depth=2, max_entries=30),
                call(path=None, max_depth=0, max_entries=5),
            ],
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_glob_tree_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/glob --max-matches 0 -- **/*.py",
                    "/glob --max-matches 5",
                    "/glob --include-dirs=maybe -- **/*.py",
                    "/glob --unknown 1 -- **/*.py",
                    "/tree --max-depth -1",
                    "/tree src --max-entries 0",
                    "/tree src other --max-depth 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_glob_text") as get_glob_text,
            patch("vibeagent.cli.get_tree_text") as get_tree_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /glob [--max-matches N] [--include-dirs] -- <pattern>", output)
        self.assertIn("--max-matches must be a positive integer.", output)
        self.assertIn("pattern is required.", output)
        self.assertIn("--include-dirs must be a boolean.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("Usage: /tree [path] [--max-depth N] [--max-entries N]", output)
        self.assertIn("--max-depth must be a non-negative integer.", output)
        self.assertIn("--max-entries must be a positive integer.", output)
        get_glob_text.assert_not_called()
        get_tree_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_symbols_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/symbols --max-symbols 12 -- src/app.py web/app.ts",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_symbols_text", return_value="Symbols:\n  files: 1/1") as get_symbols_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Symbols:", output)
        get_symbols_text.assert_called_once_with(argument=["src/app.py", "web/app.ts"], max_symbols=12)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_symbols_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/symbols --max-symbols 0 -- src/app.py",
                    "/symbols --max-symbols 12",
                    "/symbols --unknown 1 -- src/app.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_symbols_text") as get_symbols_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /symbols [--max-symbols N] -- <path...>", output)
        self.assertIn("--max-symbols must be a positive integer.", output)
        self.assertIn("at least one path is required.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_symbols_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_read_files_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/read-files --max-bytes 1000 --line-numbers -- src/app.py tests/test_app.py",
                    "/read-files --max-bytes=1200 --line-numbers=false -- README.md",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_read_files_text", return_value="Read files:\n  files: 1/1") as get_read_files_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Read files:", output)
        self.assertEqual(
            get_read_files_text.call_args_list,
            [
                call(argument=["src/app.py", "tests/test_app.py"], max_bytes_per_file=1000, show_line_numbers=True),
                call(argument=["README.md"], max_bytes_per_file=1200, show_line_numbers=False),
            ],
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_read_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/read --max-bytes 1000 --line-numbers -- src/app.py 2:4",
                    "/read --max-bytes=1200 --line-numbers=false -- README.md",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_read_text", return_value="Read:\n  ok: yes") as get_read_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Read:", output)
        self.assertEqual(
            get_read_text.call_args_list,
            [
                call(argument="src/app.py 2:4", max_bytes=1000, show_line_numbers=True),
                call(argument="README.md", max_bytes=1200, show_line_numbers=False),
            ],
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_read_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/read --max-bytes 0 -- src/app.py",
                    "/read --line-numbers=maybe -- src/app.py",
                    "/read --unknown 1 -- src/app.py",
                    "/read --max-bytes 1000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_read_text") as get_read_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /read [--max-bytes N] [--line-numbers] -- <path> [start[:end]]", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("--line-numbers must be a boolean.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("path is required.", output)
        get_read_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_context_read_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/tail --max-bytes 1000 -- logs/app.log 3",
                    "/around --max-bytes=1200 -- src/app.py 42 8",
                    "/around-many --max-bytes 1400 -- src/app.py:42:8 tests/test_app.py:17",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tail_text", return_value="Tail:\n  ok: yes") as get_tail_text,
            patch("vibeagent.cli.get_around_text", return_value="Around:\n  ok: yes") as get_around_text,
            patch("vibeagent.cli.get_around_many_text", return_value="Around many:\n  contexts: 2/2") as get_around_many_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Tail:", output)
        self.assertIn("Around:", output)
        self.assertIn("Around many:", output)
        get_tail_text.assert_called_once_with(argument="logs/app.log 3", max_bytes=1000)
        get_around_text.assert_called_once_with(argument="src/app.py 42 8", max_bytes=1200)
        get_around_many_text.assert_called_once_with(argument="src/app.py:42:8 tests/test_app.py:17", max_bytes_per_context=1400)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_diff_max_chars(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/diff --max-chars 1000 --staged app.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_diff_text", return_value="Diff:\n  truncated: yes") as get_diff_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Diff:", stdout.getvalue())
        get_diff_text.assert_called_once_with(argument="--staged app.py", max_chars=1000)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_changes_max_files(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/changes --max-files 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_changes_text", return_value="Changes:\n  shownFiles: 1/3") as get_changes_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Changes:", stdout.getvalue())
        get_changes_text.assert_called_once_with(max_files=1)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_review_limits(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/review --max-files 1 --max-checks 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_review_text", return_value="Review:\n  ready: yes") as get_review_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Review:", stdout.getvalue())
        get_review_text.assert_called_once_with(max_files=1, max_checks=2)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_handoff_limits(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/handoff --max-files 1 --max-checks 2 --max-status-chars 3000 --max-plan-chars 4000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_handoff_text", return_value="Handoff:\n  ready: yes") as get_handoff_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Handoff:", stdout.getvalue())
        get_handoff_text.assert_called_once_with(max_files=1, max_checks=2, max_status_chars=3000, max_plan_chars=4000)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_changes_max_files_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/changes --max-files 0",
                    "/changes --unknown 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_changes_text") as get_changes_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /changes [--max-files N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_changes_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_review_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/review --max-files 0",
                    "/review --unknown 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_review_text") as get_review_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /review [--max-files N] [--max-checks N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_review_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_handoff_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/handoff --max-files 0",
                    "/handoff --unknown 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_handoff_text") as get_handoff_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /handoff [--max-files N] [--max-checks N] [--max-status-chars N] [--max-plan-chars N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_handoff_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_diff_max_chars_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/diff --max-chars 0 app.py",
                    "/diff --max-chars 99 app.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_diff_text", side_effect=ValueError("max_chars must be at least 100.")) as get_diff_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /diff [--staged|--cached] [--max-chars N] [path]", output)
        self.assertIn("--max-chars must be a positive integer.", output)
        self.assertIn("max_chars must be at least 100.", output)
        get_diff_text.assert_called_once_with(argument="app.py", max_chars=99)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_structured_diff_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/diff-hunks --max-hunks 3 --max-lines 4 --staged app.py",
                    "/diff-contexts --context-lines 2 --max-hunks 5 --max-bytes 1000 app.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_diff_hunks_text", return_value="Diff hunks:\n  hunks: 1/1") as get_diff_hunks_text,
            patch("vibeagent.cli.get_diff_contexts_text", return_value="Diff contexts:\n  contexts: 1/1") as get_diff_contexts_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Diff hunks:", output)
        self.assertIn("Diff contexts:", output)
        get_diff_hunks_text.assert_called_once_with(argument="--staged app.py", max_hunks=3, max_lines_per_hunk=4)
        get_diff_contexts_text.assert_called_once_with(
            argument="app.py",
            context_lines=2,
            max_hunks=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_structured_diff_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/diff-hunks --max-hunks 0 app.py",
                    "/diff-contexts --context-lines -1 app.py",
                    "/diff-contexts --unknown app.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_diff_hunks_text") as get_diff_hunks_text,
            patch("vibeagent.cli.get_diff_contexts_text") as get_diff_contexts_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /diff-hunks [--staged|--cached] [--max-hunks N] [--max-lines N] [path]", output)
        self.assertIn("--max-hunks must be a positive integer.", output)
        self.assertIn("Usage: /diff-contexts [--staged|--cached] [--context-lines N] [--max-hunks N] [--max-bytes N] [path]", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_diff_hunks_text.assert_not_called()
        get_diff_contexts_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_context_read_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/tail --max-bytes 0 -- logs/app.log",
                    "/around --unknown 1 -- src/app.py 42",
                    "/around-many --max-bytes 1000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tail_text") as get_tail_text,
            patch("vibeagent.cli.get_around_text") as get_around_text,
            patch("vibeagent.cli.get_around_many_text") as get_around_many_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /tail [--max-bytes N] -- <path> [lines]", output)
        self.assertIn("Usage: /around [--max-bytes N] -- <path> <line> [context-lines]", output)
        self.assertIn("Usage: /around-many [--max-bytes N] -- <path:line[:context-lines]...>", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("at least one context is required.", output)
        get_tail_text.assert_not_called()
        get_around_text.assert_not_called()
        get_around_many_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_read_ranges_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/read-ranges --max-bytes 1000 -- src/app.py:2:4 tests/test_app.py:1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_read_ranges_text", return_value="Read ranges:\n  ranges: 2/2") as get_read_ranges_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Read ranges:", output)
        get_read_ranges_text.assert_called_once_with(argument="src/app.py:2:4 tests/test_app.py:1", max_bytes_per_range=1000)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_read_ranges_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/read-ranges --max-bytes 0 -- src/app.py:2:4",
                    "/read-ranges --max-bytes 1000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_read_ranges_text") as get_read_ranges_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /read-ranges [--max-bytes N] -- <path:start[:end]...>", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("at least one range is required.", output)
        get_read_ranges_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_read_files_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/read-files --max-bytes 0 -- src/app.py",
                    "/read-files --line-numbers=maybe -- src/app.py",
                    "/read-files --unknown 1 -- src/app.py",
                    "/read-files --max-bytes 1000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_read_files_text") as get_read_files_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /read-files [--max-bytes N] [--line-numbers] -- <path...>", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("--line-numbers must be a boolean.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("at least one path is required.", output)
        get_read_files_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_output_analysis_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/output-contexts --context-lines 3 --max-contexts 4 --max-bytes 1000 -- src/app.py:42:8",
                    "/output-diagnostics --context-lines 2 --max-diagnostics 5 --max-contexts 6 --max-bytes 1200 -- ERROR src/app.py:42 failed",
                    "/python-traceback --context-lines=1 --max-diagnostics=7 --max-contexts=8 --max-bytes=1400 -- ValueError: bad",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_output_contexts_text", return_value="Output contexts:\n  contexts: 1/1") as get_output_contexts_text,
            patch("vibeagent.cli.get_output_diagnostics_text", return_value="Output diagnostics:\n  diagnostics: 1/1") as get_output_diagnostics_text,
            patch("vibeagent.cli.get_python_traceback_text", return_value="Python traceback:\n  diagnostics: 1/1") as get_python_traceback_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Output contexts:", output)
        self.assertIn("Output diagnostics:", output)
        self.assertIn("Python traceback:", output)
        get_output_contexts_text.assert_called_once_with(
            text="src/app.py:42:8",
            context_lines=3,
            max_contexts=4,
            max_bytes_per_context=1000,
        )
        get_output_diagnostics_text.assert_called_once_with(
            text="ERROR src/app.py:42 failed",
            context_lines=2,
            max_diagnostics=5,
            max_contexts=6,
            max_bytes_per_context=1200,
        )
        get_python_traceback_text.assert_called_once_with(
            text="ValueError: bad",
            context_lines=1,
            max_diagnostics=7,
            max_contexts=8,
            max_bytes_per_context=1400,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_output_analysis_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/output-contexts --context-lines -1 -- src/app.py:42",
                    "/output-contexts --max-contexts 0 -- src/app.py:42",
                    "/output-diagnostics --max-diagnostics 0 -- ERROR src/app.py:42 failed",
                    "/python-traceback --max-bytes 0 -- ValueError: bad",
                    "/python-traceback --unknown 1 -- ValueError: bad",
                    "/output-diagnostics --context-lines 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_output_contexts_text") as get_output_contexts_text,
            patch("vibeagent.cli.get_output_diagnostics_text") as get_output_diagnostics_text,
            patch("vibeagent.cli.get_python_traceback_text") as get_python_traceback_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /output-contexts [--context-lines N]", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("--max-contexts must be a positive integer.", output)
        self.assertIn("Usage: /output-diagnostics [--context-lines N]", output)
        self.assertIn("--max-diagnostics must be a positive integer.", output)
        self.assertIn("Usage: /python-traceback [--context-lines N]", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("text is required.", output)
        get_output_contexts_text.assert_not_called()
        get_output_diagnostics_text.assert_not_called()
        get_python_traceback_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_wait_process_match_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/wait-process bg-1 --timeout-ms 6000 --max-chars 5000 --stdout ready --stderr error --regex",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_wait_process_text", return_value="Wait process:\n  matched: yes") as get_wait_process_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Wait process:", output)
        get_wait_process_text.assert_called_once_with(
            process_id="bg-1",
            timeout_ms=6000,
            max_output_chars=5000,
            stdout_contains="ready",
            stderr_contains="error",
            regex=True,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_wait_process_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/wait-process --timeout-ms 99 -- bg-1",
                    "/wait-process bg-1 --stdout",
                    "/wait-process --stdout ready",
                    "/wait-process bg-1 --unknown 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_wait_process_text") as get_wait_process_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /wait-process <id> [timeout-ms] [chars]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--stdout requires a value.", output)
        self.assertIn("process id is required.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_wait_process_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run --cwd src --timeout-ms 2000 --max-chars 3000 --output-contexts --output-diagnostics --context-lines 2 --max-diagnostics 7 --max-contexts 5 --max-bytes 1000 -- python3 --version",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_text", return_value="Run:\n  ok: yes") as get_run_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run:", output)
        get_run_text.assert_called_once_with(
            command="python3 --version",
            cwd="src",
            timeout_ms=2000,
            max_output_chars=3000,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_run_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run --timeout-ms 99 -- python3 --version",
                    "/run --max-diagnostics 0 -- python3 --version",
                    "/run --output-diagnostics",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_text") as get_run_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /run [--timeout-ms N]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--max-diagnostics must be a positive integer.", output)
        self.assertIn("command is required.", output)
        get_run_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_sequence_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-seq --cwd src --timeout-ms 2000 --max-chars 3000 --continue-on-failure --output-contexts --output-diagnostics --context-lines 2 --max-diagnostics 7 --max-contexts 5 --max-bytes 1000 -- python3 --version ;; npm test",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_sequence_text", return_value="Run sequence:\n  ok: yes") as get_run_sequence_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run sequence:", output)
        get_run_sequence_text.assert_called_once_with(
            commands=["python3 --version", "npm test"],
            cwd="src",
            timeout_ms=2000,
            max_output_chars=3000,
            stop_on_failure=False,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_run_sequence_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-seq --timeout-ms 99 -- python3 --version",
                    "/run-seq --max-contexts 0 -- python3 --version",
                    "/run-seq --output-diagnostics",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_sequence_text") as get_run_sequence_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /run-seq [--timeout-ms N]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--max-contexts must be a positive integer.", output)
        self.assertIn("at least one command is required.", output)
        get_run_sequence_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_focused_test_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-focused-tests --max-paths 3 --max-candidates 4 --max-commands 5 --timeout-ms 2000 --max-chars 3000 --continue-on-failure --output-contexts --output-diagnostics --context-lines 2 --max-diagnostics 7 --max-contexts 5 --max-bytes 1000 -- pkg/actions.py tests/test_actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_focused_test_commands_text", return_value="Run focused test commands:\n  ok: yes") as get_run_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run focused test commands:", output)
        get_run_focused_test_commands_text.assert_called_once_with(
            argument="pkg/actions.py tests/test_actions.py",
            max_paths=3,
            max_candidates=4,
            max_commands=5,
            timeout_ms=2000,
            max_output_chars=3000,
            stop_on_failure=False,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_related_and_focused_test_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/related-tests --max-paths 3 --max-candidates 4 -- pkg/actions.py",
                    "/focused-tests --max-paths 5 --max-candidates 6 --max-commands 7 -- pkg/actions.py",
                    "/check-focused-tests --max-paths 8 --max-candidates 9 --max-commands 10 -- pkg/actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_related_tests_text", return_value="Related tests:\n  candidates: 1/1") as get_related_tests_text,
            patch("vibeagent.cli.get_focused_test_commands_text", return_value="Focused test commands:\n  commands: 1/1") as get_focused_test_commands_text,
            patch("vibeagent.cli.get_check_focused_test_commands_text", return_value="Check focused test commands:\n  ok: yes") as get_check_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Related tests:", output)
        self.assertIn("Focused test commands:", output)
        self.assertIn("Check focused test commands:", output)
        get_related_tests_text.assert_called_once_with(argument="pkg/actions.py", max_paths=3, max_candidates=4)
        get_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py", max_paths=5, max_candidates=6, max_commands=7)
        get_check_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py", max_paths=8, max_candidates=9, max_commands=10)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_test_limit_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/related-tests --max-paths 0 -- pkg/actions.py",
                    "/focused-tests --max-commands 0 -- pkg/actions.py",
                    "/check-focused-tests --unknown 1 -- pkg/actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_related_tests_text") as get_related_tests_text,
            patch("vibeagent.cli.get_focused_test_commands_text") as get_focused_test_commands_text,
            patch("vibeagent.cli.get_check_focused_test_commands_text") as get_check_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /related-tests [--max-paths N]", output)
        self.assertIn("--max-paths must be a positive integer.", output)
        self.assertIn("Usage: /focused-tests [--max-paths N]", output)
        self.assertIn("--max-commands must be a positive integer.", output)
        self.assertIn("Usage: /check-focused-tests [--max-paths N]", output)
        self.assertIn("Unknown option: --unknown", output)
        get_related_tests_text.assert_not_called()
        get_focused_test_commands_text.assert_not_called()
        get_check_focused_test_commands_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_run_focused_test_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-focused-tests --timeout-ms 99 -- pkg/actions.py",
                    "/run-focused-tests --max-bytes 0 -- pkg/actions.py",
                    "/run-focused-tests --output-contexts=true -- pkg/actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_focused_test_commands_text") as get_run_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /run-focused-tests [--max-paths N]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("--output-contexts does not take a value.", output)
        get_run_focused_test_commands_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_suggested_check_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-suggested-checks --timeout-ms 2000 --max-chars 3000 --continue-on-failure --output-contexts --output-diagnostics --context-lines 2 --max-diagnostics 7 --max-contexts 5 --max-bytes 1000 -- 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_suggested_checks_text", return_value="Run suggested checks:\n  ok: yes") as get_run_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run suggested checks:", output)
        get_run_suggested_checks_text.assert_called_once_with(
            argument="2",
            timeout_ms=2000,
            max_output_chars=3000,
            stop_on_failure=False,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_suggested_check_named_max_option(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-suggested-checks --max-checks 2 --timeout-ms 2000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_suggested_checks_text", return_value="Run suggested checks:\n  ok: yes") as get_run_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run suggested checks:", output)
        get_run_suggested_checks_text.assert_called_once_with(
            argument=None,
            max_checks=2,
            timeout_ms=2000,
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_check_suggested_check_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/check-suggested-checks --max-checks 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_check_suggested_checks_text", return_value="Check suggested checks:\n  ok: yes") as get_check_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Check suggested checks:", output)
        get_check_suggested_checks_text.assert_called_once_with(max_checks=2)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_check_suggested_check_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/check-suggested-checks --max-checks 0",
                    "/check-suggested-checks --bad",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_check_suggested_checks_text") as get_check_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /check-suggested-checks [--max-checks N]", output)
        self.assertIn("--max-checks must be a positive integer.", output)
        self.assertIn("Unknown option: --bad", output)
        get_check_suggested_checks_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_run_suggested_check_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-suggested-checks --timeout-ms 99 -- 2",
                    "/run-suggested-checks --context-lines -1 -- 2",
                    "/run-suggested-checks --output-diagnostics=true -- 2",
                    "/run-suggested-checks --output-contexts -- 1 2",
                    "/run-suggested-checks --max-checks 1 -- 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_suggested_checks_text") as get_run_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /run-suggested-checks [--max-checks N]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("--output-diagnostics does not take a value.", output)
        self.assertIn("expected at most one max value.", output)
        self.assertIn("provide either --max-checks or trailing max, not both.", output)
        get_run_suggested_checks_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_session_verification_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-session-verification run-1 --max-checks 2 --timeout-ms 2000 --max-output-chars 3000 --no-failed --continue-on-failure --output-contexts --output-diagnostics --context-lines 2 --max-diagnostics 7 --max-contexts 5 --max-bytes 1000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_session_verification_text", return_value="Run session verification:\n  ok: yes") as get_run_session_verification_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run session verification:", output)
        get_run_session_verification_text.assert_called_once_with(
            run_id="run-1",
            max_checks=2,
            timeout_ms=2000,
            max_output_chars=3000,
            include_failed=False,
            stop_on_failure=False,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_run_session_verification_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-session-verification --timeout-ms 99",
                    "/run-session-verification --context-lines -1",
                    "/run-session-verification --output-contexts=true",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_session_verification_text") as get_run_session_verification_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /run-session-verification [run-id]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("--output-contexts does not take a value.", output)
        get_run_session_verification_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_preflight_cwd_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/command --cwd src -- python3 --version",
                    "/check-run-seq --cwd src -- python3 --version ;; npm test",
                    "/check-start --cwd web -- npm run dev",
                    "/start --cwd web -- npm run dev",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_command_check_text", return_value="Command check:\n  ok: yes") as get_command_check_text,
            patch("vibeagent.cli.get_check_run_sequence_text", return_value="Check run sequence:\n  ok: yes") as get_check_run_sequence_text,
            patch("vibeagent.cli.get_check_start_text", return_value="Check start:\n  ok: yes") as get_check_start_text,
            patch("vibeagent.cli.get_start_text", return_value="Start:\n  ok: yes") as get_start_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Command check:", output)
        self.assertIn("Check run sequence:", output)
        self.assertIn("Check start:", output)
        self.assertIn("Start:", output)
        get_command_check_text.assert_called_once_with(command="python3 --version", cwd="src")
        get_check_run_sequence_text.assert_called_once_with(commands=["python3 --version", "npm test"], cwd="src")
        get_check_start_text.assert_called_once_with(command="npm run dev", cwd="web")
        get_start_text.assert_called_once_with(command="npm run dev", cwd="web")
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_preflight_cwd_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/command --cwd",
                    "/command --cwd src",
                    "/check-run-seq --cwd src",
                    "/check-start --cwd app --cwd web -- npm run dev",
                    "/start --cwd app --cwd web -- npm run dev",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_command_check_text") as get_command_check_text,
            patch("vibeagent.cli.get_check_run_sequence_text") as get_check_run_sequence_text,
            patch("vibeagent.cli.get_check_start_text") as get_check_start_text,
            patch("vibeagent.cli.get_start_text") as get_start_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /command [--cwd PATH] -- <cmd>", output)
        self.assertIn("--cwd requires a value.", output)
        self.assertIn("command is required.", output)
        self.assertIn("Usage: /check-run-seq [--cwd PATH] -- <cmd> ;; <cmd>", output)
        self.assertIn("at least one command is required.", output)
        self.assertIn("Usage: /check-start [--cwd PATH] -- <cmd>", output)
        self.assertIn("Usage: /start [--cwd PATH] -- <cmd>", output)
        self.assertIn("--cwd can only be provided once.", output)
        get_command_check_text.assert_not_called()
        get_check_run_sequence_text.assert_not_called()
        get_check_start_text.assert_not_called()
        get_start_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_session_detail_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/session-verification run-1 --max-checks 2",
                    "/session-commands run-1 --max-commands 2 --max-output-chars 0",
                    "/session-files run-1 --max-files 3",
                    "/session-failures run-1 --max-failures 4 --max-text 80",
                    "/session-audit run-1 --max-failures 5 --max-files 6 --max-commands 7 --max-checks 8 --max-text 90",
                    "/session-handoff run-1 --max-failures 8 --max-files 9 --max-commands 10 --max-checks 11 --max-output-chars 0 --max-text 100",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_session_verification_text", return_value="Session verification:\n  session: run-1") as get_session_verification_text,
            patch("vibeagent.cli.get_session_commands_text", return_value="Command results:\n  session: run-1") as get_session_commands_text,
            patch("vibeagent.cli.get_session_files_text", return_value="Session files:\n  session: run-1") as get_session_files_text,
            patch("vibeagent.cli.get_session_failures_text", return_value="Session failures:\n  session: run-1") as get_session_failures_text,
            patch("vibeagent.cli.get_session_audit_text", return_value="Session audit:\n  session: run-1") as get_session_audit_text,
            patch("vibeagent.cli.get_session_handoff_text", return_value="Session handoff:\n  session: run-1") as get_session_handoff_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Session verification:", output)
        self.assertIn("Command results:", output)
        self.assertIn("Session files:", output)
        self.assertIn("Session failures:", output)
        self.assertIn("Session audit:", output)
        self.assertIn("Session handoff:", output)
        get_session_verification_text.assert_called_once_with(run_id="run-1", max_checks=2)
        get_session_commands_text.assert_called_once_with(run_id="run-1", max_commands=2, max_output_chars=0)
        get_session_files_text.assert_called_once_with(run_id="run-1", max_files=3)
        get_session_failures_text.assert_called_once_with(run_id="run-1", max_failures=4, max_text=80)
        get_session_audit_text.assert_called_once_with(
            run_id="run-1",
            max_failures=5,
            max_files=6,
            max_commands=7,
            max_checks=8,
            max_text=90,
        )
        get_session_handoff_text.assert_called_once_with(
            run_id="run-1",
            max_failures=8,
            max_files=9,
            max_commands=10,
            max_checks=11,
            max_output_chars=0,
            max_text=100,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_session_detail_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/session-verification --max-checks 0",
                    "/session-commands --max-output-chars -1",
                    "/session-files --max-files 0",
                    "/session-audit --max-checks 0",
                    "/session-handoff --max-checks 0",
                    "/session-handoff --unknown run-1",
                    "/resume --max-checks 0",
                    "/resume --max-output-chars -1",
                    "/compact --max-checks 0",
                    "/compact --max-output-chars -1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_session_verification_text") as get_session_verification_text,
            patch("vibeagent.cli.get_session_commands_text") as get_session_commands_text,
            patch("vibeagent.cli.get_session_files_text") as get_session_files_text,
            patch("vibeagent.cli.get_session_handoff_text") as get_session_handoff_text,
            patch("vibeagent.cli.get_resume_context") as get_resume_context,
            patch("vibeagent.cli.get_compact_context") as get_compact_context,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /session-verification [run-id] [--max-checks N]", output)
        self.assertIn("--max-checks must be a positive integer.", output)
        self.assertIn("Usage: /session-commands [run-id] [--max-commands N] [--max-output-chars N]", output)
        self.assertIn("--max-output-chars must be a non-negative integer.", output)
        self.assertIn("Usage: /session-files [run-id] [--max-files N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("Usage: /session-audit [run-id]", output)
        self.assertIn("Usage: /session-handoff [run-id]", output)
        self.assertIn("Usage: /resume [run-id|off] [--max-failures N]", output)
        self.assertIn("Usage: /compact [run-id] [--max-failures N]", output)
        self.assertIn("Unknown option: --unknown", output)
        get_session_verification_text.assert_not_called()
        get_session_commands_text.assert_not_called()
        get_session_files_text.assert_not_called()
        get_session_handoff_text.assert_not_called()
        get_resume_context.assert_not_called()
        get_compact_context.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_status_command_reports_local_state_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/status",
                    "/chat",
                    "/approval allow",
                    "/resume run-1",
                    "/status",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_resume_context", return_value=("run-1", "context", "Resume context loaded from session run-1.")),
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("mode: code", output)
        self.assertIn("approval: ask", output)
        self.assertIn("resume: none", output)
        self.assertIn("mode: chat", output)
        self.assertIn("approval: allow", output)
        self.assertIn("resume: run-1", output)
        create_chat_client.assert_not_called()

    def test_main_passes_resume_context_to_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch(
                    "builtins.input",
                    side_effect=[
                        "/resume run-1 --max-failures 3 --max-files 4 --max-commands 5 --max-checks 2 --max-output-chars 0 --max-text 90",
                        "continue task",
                        "/exit",
                    ],
                ),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_resume_context", side_effect=[
                    ("run-1", "previous context", "Resume context loaded from session run-1."),
                    ("new-run", "new context", "Resume context loaded from session new-run."),
                ]) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            get_resume_context.call_args_list[0].kwargs,
            {
                "max_failures": 3,
                "max_files": 4,
                "max_commands": 5,
                "max_checks": 2,
                "max_output_chars": 0,
                "max_text": 90,
            },
        )
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "previous context")

    def test_main_starts_interactive_with_resume_context_from_cli_args(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_resume_context", side_effect=[
                    ("run-1", "startup context", "Resume context loaded from session run-1."),
                    ("new-run", "new context", "Resume context loaded from session new-run."),
                ]) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--resume", "run-1", "--resume-max-files", "4"])

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_any_call("run-1", Path(base).resolve(), max_files=4)
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "startup context")
        self.assertIn("Resume context loaded from session run-1.", stdout.getvalue())

    def test_main_continue_without_task_starts_interactive_with_latest_resume_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_resume_context", side_effect=[
                    ("latest-run", "latest context", "Resume context loaded from session latest-run."),
                    ("new-run", "new context", "Resume context loaded from session new-run."),
                ]) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "-c"])

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_any_call(None, Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "latest context")

    def test_main_startup_resume_missing_context_does_not_create_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_resume_context", return_value=(None, None, "Session not found: missing")),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--resume", "missing"])

        self.assertEqual(exit_code, 2)
        self.assertIn("Session not found: missing", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_starts_interactive_with_compact_context_from_cli_args(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_compact_context",
                    return_value=("run-1", "startup compact context", "Compacted context loaded from session run-1."),
                ) as get_compact_context,
                patch("vibeagent.cli.get_resume_context", return_value=("new-run", "new context", "Resume context loaded from session new-run.")),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--compact", "run-1", "--compact-max-checks", "2"])

        self.assertEqual(exit_code, 0)
        get_compact_context.assert_called_once_with("run-1", Path(base).resolve(), max_checks=2)
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "startup compact context")

    def test_main_starts_interactive_with_session_id_resume_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("run-1", "startup resume context", "Resume context loaded from session run-1."),
                        ("new-run", "new context", "Resume context loaded from session new-run."),
                    ],
                ) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--session-id", "run-1", "--resume-max-checks", "2"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(get_resume_context.call_args_list[0].args, ("run-1", Path(base).resolve()))
        self.assertEqual(get_resume_context.call_args_list[0].kwargs, {"max_checks": 2})
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "startup resume context")

    def test_main_starts_interactive_with_session_id_latest_resume_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("latest-run", "startup latest context", "Resume context loaded from session latest-run."),
                        ("new-run", "new context", "Resume context loaded from session new-run."),
                    ],
                ) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--session-id", "latest"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(get_resume_context.call_args_list[0].args, (None, Path(base).resolve()))
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "startup latest context")

    def test_main_one_shot_compact_passes_compacted_context_to_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_compact_context", return_value=("run-1", "compacted context", "Compacted context loaded from session run-1.")) as get_compact_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--compact",
                        "run-1",
                        "--compact-max-failures",
                        "3",
                        "--compact-max-files",
                        "4",
                        "--compact-max-commands",
                        "5",
                        "--compact-max-checks",
                        "2",
                        "--compact-max-output-chars",
                        "0",
                        "--compact-max-text",
                        "90",
                        "--cwd",
                        base,
                        "continue",
                        "task",
                    ]
                )

        self.assertEqual(exit_code, 0)
        get_compact_context.assert_called_once_with(
            "run-1",
            Path(base).resolve(),
            max_failures=3,
            max_files=4,
            max_commands=5,
            max_checks=2,
            max_output_chars=0,
            max_text=90,
        )
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "compacted context")
        self.assertIn("done", stdout.getvalue())

    def test_main_one_shot_compact_reports_missing_context_without_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_compact_context", return_value=(None, None, "No sessions found.")),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--compact", "--cwd", base, "continue", "task"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue().strip(), "No sessions found.")
        create_chat_client.assert_not_called()

    def test_main_rejects_resume_and_compact_together(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["--resume", "run-1", "--compact", "run-2", "continue"])

        self.assertEqual(exit_code, 2)
        self.assertIn("--resume/--session-id and --compact cannot be used together.", stdout.getvalue())

    def test_main_rejects_resume_compact_limit_without_matching_context_flag(self) -> None:
        cases = [
            (["--resume-max-checks", "2", "continue"], "--resume-max-checks can only be used with --resume or --session-id."),
            (["--resume-max-files", "2", "continue"], "--resume-max-files can only be used with --resume or --session-id."),
            (["--resume-max-output-chars", "0", "continue"], "--resume-max-output-chars can only be used with --resume or --session-id."),
            (["--compact-max-checks", "2", "continue"], "--compact-max-checks can only be used with --compact."),
            (["--compact-max-files", "2", "continue"], "--compact-max-files can only be used with --compact."),
            (["--compact-max-output-chars", "0", "continue"], "--compact-max-output-chars can only be used with --compact."),
        ]

        for argv, message in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(argv)
                self.assertEqual(exit_code, 2)
                self.assertIn(message, stdout.getvalue())

    def test_main_resume_off_clears_context_before_next_agent_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["/resume run-1", "/resume off", "fresh task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("run-1", "previous context", "Resume context loaded from session run-1."),
                        (None, None, "Resume context cleared."),
                        ("new-run", "new context", "Resume context loaded from session new-run."),
                    ],
                ),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])
        self.assertIn("Resume context cleared.", stdout.getvalue())

    def test_main_clear_clears_context_before_next_agent_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["/resume run-1", "/clear", "fresh task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("run-1", "previous context", "Resume context loaded from session run-1."),
                        ("new-run", "new context", "Resume context loaded from session new-run."),
                    ],
                ),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])
        self.assertIn("Cleared chat history and resume context.", stdout.getvalue())

    def test_main_compact_passes_compacted_context_to_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch(
                    "builtins.input",
                    side_effect=[
                        "/compact run-1 --max-failures 3 --max-files 4 --max-commands 5 --max-checks 2 --max-output-chars 0 --max-text 90",
                        "continue task",
                        "/exit",
                    ],
                ),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_compact_context", return_value=("run-1", "compacted context", "Compacted context loaded from session run-1.")) as get_compact_context,
                patch("vibeagent.cli.get_resume_context", return_value=("new-run", "new context", "Resume context loaded from session new-run.")),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Compacted context loaded", output)
        get_compact_context.assert_called_once_with(
            "run-1",
            max_failures=3,
            max_files=4,
            max_commands=5,
            max_checks=2,
            max_output_chars=0,
            max_text=90,
        )
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "compacted context")

    def test_main_updates_approval_policy_and_passes_handler_to_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="test-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["/approval allow", "write file", "/approval deny", "run command", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Approval policy: allow", output)
        self.assertIn("Approval policy: deny", output)
        first_handler = run_agent.call_args_list[0].kwargs["approval_handler"]
        second_handler = run_agent.call_args_list[1].kwargs["approval_handler"]
        self.assertEqual(run_agent.call_args_list[0].kwargs["approval_policy"], "allow")
        self.assertEqual(run_agent.call_args_list[1].kwargs["approval_policy"], "deny")
        request = ApprovalRequest(action_type="write_file", target="note.txt", risk="write")
        self.assertTrue(first_handler(request).approved)
        self.assertFalse(second_handler(request).approved)

    def test_main_interactive_system_prompt_commands_affect_code_and_chat_turns(self) -> None:
        result = AgentResult(
            success=True,
            message="done",
            run_dir=Path(tempfile.gettempdir()),
            run_id="test-run",
            iterations=1,
            observations=[],
            steps=[],
        )
        stdout = io.StringIO()
        run_agent = Mock(return_value=result)
        run_chat = Mock(return_value="chat response")

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/system-prompt You are a release engineer.",
                    "/append-system-prompt Prefer focused tests.",
                    "inspect code",
                    "/chat explain",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_agent", run_agent),
            patch("vibeagent.cli.run_chat", run_chat),
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["system_prompt"], "You are a release engineer.")
        self.assertEqual(run_agent.call_args.kwargs["append_system_prompt"], "Prefer focused tests.")
        self.assertEqual(run_chat.call_args.kwargs["system_prompt"], "You are a release engineer.")
        self.assertEqual(run_chat.call_args.kwargs["append_system_prompt"], "Prefer focused tests.")
        output = stdout.getvalue()
        self.assertIn("System prompt set", output)
        self.assertIn("Appended system prompt set", output)

    def test_main_interactive_system_prompt_status_and_clear(self) -> None:
        result = AgentResult(
            success=True,
            message="done",
            run_dir=Path(tempfile.gettempdir()),
            run_id="test-run",
            iterations=1,
            observations=[],
            steps=[],
        )
        stdout = io.StringIO()
        run_agent = Mock(return_value=result)

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/system-prompt You are terse.",
                    "/append-system-prompt Prefer focused tests.",
                    "/status",
                    "/system-prompt off",
                    "/append-system-prompt off",
                    "inspect code",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_agent", run_agent),
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("systemPrompt: custom", output)
        self.assertIn("appendSystemPrompt: set", output)
        self.assertIn("System prompt cleared.", output)
        self.assertIn("Appended system prompt cleared.", output)
        self.assertIsNone(run_agent.call_args.kwargs["system_prompt"])
        self.assertIsNone(run_agent.call_args.kwargs["append_system_prompt"])

    def test_main_interactive_task_keyboard_interrupt_returns_to_prompt(self) -> None:
        stdout = io.StringIO()

        with (
            patch("builtins.input", side_effect=["write file", "/exit"]),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_agent", side_effect=KeyboardInterrupt) as run_agent,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Interrupted.", output)
        self.assertNotIn("Error:", output)
        self.assertEqual(run_agent.call_count, 1)


if __name__ == "__main__":
    unittest.main()
