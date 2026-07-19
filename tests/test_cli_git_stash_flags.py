import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliGitStashFlagTests(unittest.TestCase):
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
