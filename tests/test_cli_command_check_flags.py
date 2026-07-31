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
        self.assertIn("provide --cwd at most once.", output)
        get_command_check_text.assert_not_called()
        get_check_run_sequence_text.assert_not_called()
        get_check_start_text.assert_not_called()
        get_start_text.assert_not_called()
        create_chat_client.assert_not_called()
