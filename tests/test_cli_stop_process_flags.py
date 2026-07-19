import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliStopProcessFlagTests(unittest.TestCase):
    def test_main_runs_stop_process_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stop_process_text", return_value="Check stop process:\n  ok: yes") as get_check_stop_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-stop-process", "bg-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check stop process:", stdout.getvalue())
        get_check_stop_process_text.assert_called_once_with(Path(base).resolve(), "bg-1")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stop_process_text", return_value="Stop process:\n  ok: no") as get_stop_process_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--stop-process", "bg-1"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Stop process:", stdout.getvalue())
        get_stop_process_text.assert_called_once_with(Path(base).resolve(), "bg-1")
        create_chat_client.assert_not_called()

    def test_main_stop_process_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            check_stdout = io.StringIO()
            check_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 123,
                "command": "npm run dev",
                "cwd": "web",
                "running": True,
                "exitCode": None,
                "signal": None,
                "status": "running",
                "message": "Process bg-1 is running and can be stopped.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stop_process_report", return_value=check_report) as get_check_stop_process_report,
                patch("vibeagent.cli.format_check_stop_process_report_text", return_value="Check stop process:\n  ok: yes") as format_check_stop_process_report,
                redirect_stdout(check_stdout),
            ):
                check_exit = main(["--json", "--cwd", base, "--check-stop-process", "bg-1"])

            stop_stdout = io.StringIO()
            stop_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "processId": "missing",
                "pid": None,
                "exitCode": None,
                "signal": None,
                "result": "unknown",
                "message": "Unknown background process id.",
            }
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client_stop,
                patch("vibeagent.cli.get_stop_process_report", return_value=stop_report) as get_stop_process_report,
                patch("vibeagent.cli.format_stop_process_report_text", return_value="Stop process:\n  ok: no") as format_stop_process_report,
                redirect_stdout(stop_stdout),
            ):
                stop_exit = main(["--json", "--cwd", base, "--stop-process", "missing"])

        check_payload = json.loads(check_stdout.getvalue())
        stop_payload = json.loads(stop_stdout.getvalue())
        self.assertEqual(check_exit, 0)
        self.assertTrue(check_payload["success"])
        self.assertEqual(check_payload["checkStopProcess"], check_report)
        get_check_stop_process_report.assert_called_once_with(Path(base).resolve(), "bg-1")
        format_check_stop_process_report.assert_called_once_with(check_report)
        create_chat_client.assert_not_called()
        self.assertEqual(stop_exit, 1)
        self.assertFalse(stop_payload["success"])
        self.assertEqual(stop_payload["status"], "failed")
        self.assertEqual(stop_payload["stopProcess"], stop_report)
        get_stop_process_report.assert_called_once_with(Path(base).resolve(), "missing")
        format_stop_process_report.assert_called_once_with(stop_report)
        create_chat_client_stop.assert_not_called()

    def test_main_runs_stop_all_processes_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stop_all_processes_text", return_value="Check stop processes:\n  processes: 1") as get_check_stop_all_processes_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-stop-all-processes"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check stop processes:", stdout.getvalue())
        get_check_stop_all_processes_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_stop_all_processes_text", return_value="Stop processes:\n  stopped: 1") as get_stop_all_processes_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--stop-all-processes"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Stop processes:", stdout.getvalue())
        get_stop_all_processes_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_stop_all_processes_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            check_stdout = io.StringIO()
            check_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processes": {
                    "total": 1,
                    "running": 1,
                    "items": [
                        {
                            "processId": "bg-1",
                            "pid": 123,
                            "command": "npm run dev",
                            "cwd": "web",
                            "running": True,
                            "exitCode": None,
                            "signal": None,
                            "status": "running",
                        }
                    ],
                },
                "message": "stop_all_processes would stop 1 background process(es), 1 still running.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_stop_all_processes_report", return_value=check_report) as get_check_stop_all_processes_report,
                patch("vibeagent.cli.format_check_stop_all_processes_report_text", return_value="Check stop processes:\n  processes: 1") as format_check_stop_all_processes_report,
                redirect_stdout(check_stdout),
            ):
                check_exit = main(["--json", "--cwd", base, "--check-stop-all-processes"])

            stop_stdout = io.StringIO()
            stop_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "stopped": {
                    "total": 1,
                    "items": [
                        {
                            "processId": "bg-1",
                            "pid": 123,
                            "command": "npm run dev",
                            "cwd": "web",
                            "ok": True,
                            "exitCode": -15,
                            "signal": "SIGTERM",
                            "result": "signaled(SIGTERM)",
                            "message": "Stopped process bg-1.",
                        }
                    ],
                },
                "message": "Stopped 1 background process(es).",
            }
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client_stop,
                patch("vibeagent.cli.get_stop_all_processes_report", return_value=stop_report) as get_stop_all_processes_report,
                patch("vibeagent.cli.format_stop_all_processes_report_text", return_value="Stop processes:\n  stopped: 1") as format_stop_all_processes_report,
                redirect_stdout(stop_stdout),
            ):
                stop_exit = main(["--json", "--cwd", base, "--stop-all-processes"])

        check_payload = json.loads(check_stdout.getvalue())
        stop_payload = json.loads(stop_stdout.getvalue())
        self.assertEqual(check_exit, 0)
        self.assertTrue(check_payload["success"])
        self.assertEqual(check_payload["checkStopAllProcesses"], check_report)
        get_check_stop_all_processes_report.assert_called_once_with(Path(base).resolve())
        format_check_stop_all_processes_report.assert_called_once_with(check_report)
        create_chat_client.assert_not_called()
        self.assertEqual(stop_exit, 0)
        self.assertTrue(stop_payload["success"])
        self.assertEqual(stop_payload["stopAllProcesses"], stop_report)
        get_stop_all_processes_report.assert_called_once_with(Path(base).resolve())
        format_stop_all_processes_report.assert_called_once_with(stop_report)
        create_chat_client_stop.assert_not_called()
