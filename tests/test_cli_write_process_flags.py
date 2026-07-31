import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliWriteProcessFlagTests(unittest.TestCase):
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
        get_write_process_text.assert_called_once_with(Path(base).resolve(), process_id="bg-1", content="hello\\n", stdin_file=None)
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
        get_check_write_process_text.assert_called_once_with(Path(base).resolve(), process_id="bg-1", content="hello\\n", stdin_file=None)
        create_chat_client.assert_not_called()

    def test_main_reads_write_process_stdin_from_project_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "input.txt").write_text("hello\nfrom file\n", encoding="utf-8")
            check_stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_write_process_text", return_value="Check write process:\n  ok: yes") as get_check_write_process_text,
                redirect_stdout(check_stdout),
            ):
                check_exit = main(["--cwd", base, "--check-write-process", "bg-1", "--write-stdin-file", "input.txt"])

            write_stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client_write,
                patch("vibeagent.cli.get_write_process_text", return_value="Write process:\n  ok: yes") as get_write_process_text,
                redirect_stdout(write_stdout),
            ):
                write_exit = main(["--cwd", base, "--write-process", "bg-1", "--write-stdin-file", "input.txt"])

        self.assertEqual(check_exit, 0)
        self.assertEqual(write_exit, 0)
        get_check_write_process_text.assert_called_once_with(root.resolve(), process_id="bg-1", content=None, stdin_file="input.txt")
        get_write_process_text.assert_called_once_with(root.resolve(), process_id="bg-1", content=None, stdin_file="input.txt")
        create_chat_client.assert_not_called()
        create_chat_client_write.assert_not_called()

    def test_main_rejects_write_process_stdin_file_outside_project_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_write_process_text") as get_write_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--write-process", "bg-1", "--write-stdin-file", "../input.txt"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Path escapes the project directory", stdout.getvalue())
        get_write_process_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_write_process_stdin_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "input.txt").write_text("hello\nfrom file\n", encoding="utf-8")
            stdout = io.StringIO()

            with (
                patch(
                    "builtins.input",
                    side_effect=[
                        "/check-write-process bg-1 --stdin-file input.txt",
                        "/write-process bg-1 --stdin-file=input.txt",
                        "/exit",
                    ],
                ),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_write_process_text", return_value="Check write process:\n  ok: yes") as get_check_write_process_text,
                patch("vibeagent.cli.get_write_process_text", return_value="Write process:\n  ok: yes") as get_write_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Check write process:", output)
        self.assertIn("Write process:", output)
        get_check_write_process_text.assert_called_once_with(process_id="bg-1", content=None, stdin_file="input.txt")
        get_write_process_text.assert_called_once_with(process_id="bg-1", content=None, stdin_file="input.txt")
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_write_process_stdin_file_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "input.txt").write_text("hello\n", encoding="utf-8")
            stdout = io.StringIO()

            with (
                patch(
                    "builtins.input",
                    side_effect=[
                        "/write-process bg-1 text --stdin-file input.txt",
                        "/write-process bg-1 --stdin-file",
                        "/write-process bg-1 --stdin-file input.txt --stdin-file=input.txt",
                        "/write-process bg-1 --stdin-file ../input.txt",
                        "/exit",
                    ],
                ),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_write_process_text") as get_write_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("text and --stdin-file cannot be used together", output)
        self.assertIn("--stdin-file requires a value", output)
        self.assertIn("provide --stdin-file at most once", output)
        self.assertIn("Path escapes the project directory", output)
        get_write_process_text.assert_not_called()
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
        get_check_write_process_report.assert_called_once_with(Path(base).resolve(), process_id="bg-1", content="hello\\n", stdin_file=None)
        format_check_write_process_report.assert_called_once_with(check_report)
        create_chat_client.assert_not_called()
        self.assertEqual(write_exit, 1)
        self.assertFalse(write_payload["success"])
        self.assertEqual(write_payload["status"], "failed")
        self.assertEqual(write_payload["writeProcess"], write_report)
        get_write_process_report.assert_called_once_with(Path(base).resolve(), process_id="missing", content="hello\\n", stdin_file=None)
        format_write_process_report.assert_called_once_with(write_report)
        create_chat_client_write.assert_not_called()
