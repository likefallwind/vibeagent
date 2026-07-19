import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliSessionVerificationFlagTests(unittest.TestCase):
    def test_main_runs_session_files_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_files_report", return_value={"session": "run-1", "ok": True}) as get_session_files_report,
                patch("vibeagent.cli.get_session_files_text", return_value="Session files:\n  session: run-1") as get_session_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-files", "run-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session files:", stdout.getvalue())
        get_session_files_report.assert_not_called()
        get_session_files_text.assert_called_once_with(Path(base).resolve(), "run-1")
        create_chat_client.assert_not_called()

    def test_main_runs_session_files_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "files": {"total": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_files_report", return_value=report) as get_session_files_report,
                patch("vibeagent.cli.get_session_files_text", return_value="unused") as get_session_files_text,
                patch(
                    "vibeagent.cli.format_session_files_report_text",
                    return_value="Session files:\n  session: run-1",
                ) as format_session_files_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--session-files", "run-1", "--session-max-files", "3"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionFiles"], report)
        get_session_files_report.assert_called_once_with(Path(base).resolve(), "run-1", max_files=3)
        format_session_files_report_text.assert_called_once_with(report)
        get_session_files_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_failures_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_failures_report", return_value={"session": "run-1", "ok": True}) as get_session_failures_report,
                patch("vibeagent.cli.get_session_failures_text", return_value="Session failures:\n  session: run-1") as get_session_failures_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-failures", "run-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session failures:", stdout.getvalue())
        get_session_failures_report.assert_not_called()
        get_session_failures_text.assert_called_once_with(Path(base).resolve(), "run-1")
        create_chat_client.assert_not_called()

    def test_main_session_failures_exits_nonzero_when_failures_exist(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "session": "run-1",
                "exists": True,
                "ok": False,
                "status": "failed",
                "failures": {"total": 1, "shown": 1, "items": [{"name": "run_command"}]},
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_failures_report", return_value=report) as get_session_failures_report,
                patch(
                    "vibeagent.cli.format_session_failures_report_text",
                    return_value=(
                        "Session failures:\n"
                        "  session: run-1\n"
                        "  failures: 1\n"
                        "  shown: 1/1\n"
                        "  - #2 command: run_command\n"
                    ),
                ) as format_session_failures_report_text,
                patch(
                    "vibeagent.cli.get_session_failures_text",
                    return_value="old text path",
                ) as get_session_failures_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-failures", "run-1", "--json"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertIn("failures: 1", payload["text"])
        self.assertEqual(payload["sessionFailures"], report)
        get_session_failures_report.assert_called_once_with(Path(base).resolve(), "run-1")
        format_session_failures_report_text.assert_called_once_with(report)
        get_session_failures_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_verification_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_verification_report", return_value={"session": "run-1", "ok": True}) as get_session_verification_report,
                patch("vibeagent.cli.get_session_verification_text", return_value="Session verification:\n  session: run-1") as get_session_verification_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-verification", "run-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session verification:", stdout.getvalue())
        get_session_verification_report.assert_not_called()
        get_session_verification_text.assert_called_once_with(Path(base).resolve(), "run-1")
        create_chat_client.assert_not_called()

    def test_main_runs_session_verification_local_flag_with_max_checks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_verification_report", return_value={"session": "run-1", "ok": True}) as get_session_verification_report,
                patch("vibeagent.cli.get_session_verification_text", return_value="Session verification:\n  session: run-1") as get_session_verification_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-verification", "run-1", "--session-max-checks", "3"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session verification:", stdout.getvalue())
        get_session_verification_report.assert_not_called()
        get_session_verification_text.assert_called_once_with(Path(base).resolve(), "run-1", max_checks=3)
        create_chat_client.assert_not_called()

    def test_main_session_verification_exits_nonzero_with_pending_checks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "session": "run-1",
                "exists": True,
                "ok": False,
                "ready": False,
                "status": "blocked",
                "pending": {"total": 1, "items": ["npm test"]},
                "failed": {"total": 0, "items": []},
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_verification_report", return_value=report) as get_session_verification_report,
                patch(
                    "vibeagent.cli.format_session_verification_report_text",
                    return_value=(
                        "Session verification:\n"
                        "  verified: none\n"
                        "  pendingChecks: 1/1\n"
                        "    - npm test\n"
                        "  failedChecks: none"
                    ),
                ) as format_session_verification_report_text,
                patch(
                    "vibeagent.cli.get_session_verification_text",
                    return_value="old text path",
                ) as get_session_verification_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-verification", "run-1", "--json"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertIn("pendingChecks:", payload["text"])
        self.assertEqual(payload["sessionVerification"], report)
        get_session_verification_report.assert_called_once_with(Path(base).resolve(), "run-1")
        format_session_verification_report_text.assert_called_once_with(report)
        get_session_verification_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_run_session_verification_json_uses_local_flag(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "session": "run-1",
                "ok": False,
                "selectedCount": 1,
                "commands": {"shown": 1, "total": 1},
                "results": [{"command": "npm test", "exitCode": 1}],
                "message": "Ran 1/1 session verification command(s); one or more failed.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_session_verification_report", return_value=report) as get_report,
                patch(
                    "vibeagent.cli.format_run_session_verification_report_text",
                    return_value=(
                        "Run session verification:\n"
                        "  session: run-1\n"
                        "  ok: no\n"
                        "  commands: 1/1\n"
                        "  message: failed"
                    ),
                ) as format_text,
                patch("vibeagent.cli.get_run_session_verification_text", return_value="old text path") as get_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--run-session-verification",
                        "run-1",
                        "--session-max-checks",
                        "2",
                        "--run-session-no-pending",
                        "--run-timeout-ms",
                        "1000",
                        "--run-max-chars",
                        "2000",
                        "--run-output-contexts",
                        "--run-output-diagnostics",
                        "--run-output-context-lines",
                        "0",
                        "--run-output-diagnostic-max",
                        "3",
                        "--run-output-context-max",
                        "4",
                        "--run-output-context-max-bytes",
                        "1000",
                        "--json",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["runSessionVerification"], report)
        get_report.assert_called_once_with(
            Path(base).resolve(),
            "run-1",
            max_checks=2,
            timeout_ms=1000,
            max_output_chars=2000,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=0,
            max_diagnostics=3,
            max_contexts=4,
            max_bytes_per_context=1000,
            include_pending=False,
        )
        format_text.assert_called_once_with(report)
        get_text.assert_not_called()
        create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
