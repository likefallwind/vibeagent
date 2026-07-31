import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliChangeDiffFlagTests(unittest.TestCase):
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
                    "/diff-hunks --max-hunks 1 --max-hunks 2 app.py",
                    "/diff-contexts --context-lines -1 app.py",
                    "/diff-contexts --context-lines 1 --context-lines 2 app.py",
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
        self.assertIn("provide --max-hunks at most once.", output)
        self.assertIn("Usage: /diff-contexts [--staged|--cached] [--context-lines N] [--max-hunks N] [--max-bytes N] [path]", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("provide --context-lines at most once.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_diff_hunks_text.assert_not_called()
        get_diff_contexts_text.assert_not_called()
        create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
