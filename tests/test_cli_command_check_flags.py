import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliCommandCheckFlagTests(unittest.TestCase):
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
