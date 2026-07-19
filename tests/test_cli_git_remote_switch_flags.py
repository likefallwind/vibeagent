import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliGitRemoteSwitchFlagTests(unittest.TestCase):
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
