import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliRunCommandFlagTests(unittest.TestCase):
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
