import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliStartCommandFlagTests(unittest.TestCase):
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
