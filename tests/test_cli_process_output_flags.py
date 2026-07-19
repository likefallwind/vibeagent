import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliProcessOutputFlagTests(unittest.TestCase):
    def test_main_runs_process_output_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_text", return_value="Process:\n  ok: no") as get_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--process-output", "bg-1", "--process-max-chars", "2000"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Process:", stdout.getvalue())
        get_process_text.assert_called_once_with(Path(base).resolve(), process_id="bg-1", max_output_chars=2000)
        create_chat_client.assert_not_called()

    def test_main_process_output_local_flag_exits_nonzero_for_failed_process_state(self) -> None:
        cases = [
            ("Process:\n  ok: yes\n  status: exited(7)", 1),
            ("Process:\n  ok: yes\n  status: signaled(SIGTERM)", 1),
            ("Process:\n  ok: yes\n  status: exited(0)", 0),
            ("Process:\n  ok: yes\n  status: running", 0),
        ]

        for text, expected_exit_code in cases:
            with self.subTest(text=text), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch("vibeagent.cli.get_process_text", return_value=text),
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, "--process-output", "bg-1"])

            self.assertEqual(exit_code, expected_exit_code)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            create_chat_client.assert_not_called()

    def test_main_process_output_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 1234,
                "status": "running",
                "running": True,
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
                "message": "Process bg-1 is running.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_report", return_value=report) as get_process_report,
                patch("vibeagent.cli.format_process_report_text", return_value="Process:\n  ok: yes\n  status: running") as format_process_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--process-output", "bg-1", "--process-max-chars", "2000"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["process"], report)
        get_process_report.assert_called_once_with(Path(base).resolve(), process_id="bg-1", max_output_chars=2000)
        format_process_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()
