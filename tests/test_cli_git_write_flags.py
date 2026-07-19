import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliGitWriteFlagTests(unittest.TestCase):
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
