import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliGitReadFlagTests(unittest.TestCase):
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
