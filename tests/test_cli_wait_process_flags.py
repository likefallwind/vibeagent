import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliWaitProcessFlagTests(unittest.TestCase):
    def test_main_runs_wait_process_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_wait_process_text", return_value="Wait process:\n  ok: no") as get_wait_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--wait-process",
                        "bg-1",
                        "--wait-timeout-ms",
                        "2000",
                        "--wait-max-chars",
                        "3000",
                        "--wait-stdout",
                        "ready",
                        "--wait-regex",
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertIn("Wait process:", stdout.getvalue())
        get_wait_process_text.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            timeout_ms=2000,
            max_output_chars=3000,
            stdout_contains="ready",
            stderr_contains=None,
            regex=True,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_wait_process_local_flag_inherits_process_output_limit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_wait_process_text", return_value="Wait process:\n  ok: no") as get_wait_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--wait-process", "bg-1"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Wait process:", stdout.getvalue())
        get_wait_process_text.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            timeout_ms=5000,
            max_output_chars=None,
            stdout_contains=None,
            stderr_contains=None,
            regex=False,
        )
        create_chat_client.assert_not_called()

    def test_main_wait_process_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 1234,
                "status": "running",
                "running": True,
                "timedOut": False,
                "matched": True,
                "matchedStream": "stdout",
                "matchedPattern": "ready",
                "timeoutMs": 5000,
                "exitCode": None,
                "signal": None,
                "maxOutputChars": 2000,
                "stdout": "ready\n",
                "stderr": "",
                "analysis": {
                    "diagnostics": {"shown": 0, "total": 0, "items": []},
                    "diagnosticsTruncated": False,
                    "contexts": {"shown": 0, "totalRefs": 0, "items": []},
                    "contextsTruncated": False,
                },
                "message": "Matched stdout pattern.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_wait_process_report", return_value=report) as get_wait_process_report,
                patch("vibeagent.cli.format_wait_process_report_text", return_value="Wait process:\n  matched: yes") as format_wait_process_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--wait-process",
                        "bg-1",
                        "--wait-timeout-ms",
                        "5000",
                        "--wait-max-chars",
                        "2000",
                        "--wait-stdout",
                        "ready",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["waitProcess"], report)
        get_wait_process_report.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            timeout_ms=5000,
            max_output_chars=2000,
            stdout_contains="ready",
            stderr_contains=None,
            regex=False,
        )
        format_wait_process_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_wait_process_local_flag_exits_nonzero_for_failed_process_state(self) -> None:
        cases = [
            ("Wait process:\n  ok: yes\n  status: exited(7)\n  timedOut: no", 1),
            ("Wait process:\n  ok: yes\n  status: running\n  timedOut: yes", 1),
            ("Wait process:\n  ok: yes\n  status: signaled(SIGTERM)\n  timedOut: no", 1),
            ("Wait process:\n  ok: yes\n  status: exited(0)\n  timedOut: no", 0),
        ]

        for text, expected_exit_code in cases:
            with self.subTest(text=text), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch("vibeagent.cli.get_wait_process_text", return_value=text),
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, "--wait-process", "bg-1"])

            self.assertEqual(exit_code, expected_exit_code)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            create_chat_client.assert_not_called()
