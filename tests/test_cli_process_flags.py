import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliProcessFlagTests(unittest.TestCase):
    def test_main_runs_processes_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_processes_text", return_value="Processes:\n  processes: 0") as get_processes_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--processes"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Processes:", stdout.getvalue())
        get_processes_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_processes_local_flag_exits_nonzero_for_failed_process_state(self) -> None:
        cases = [
            ("Processes:\n  processes: 1\n  running: 0\n  items:\n    - bg-1: pid=123; status=exited(7); cwd=.; command=pytest", 1),
            ("Processes:\n  processes: 1\n  running: 0\n  items:\n    - bg-1: pid=123; status=signaled(SIGTERM); cwd=.; command=server", 1),
            ("Processes:\n  processes: 1\n  running: 0\n  items:\n    - bg-1: pid=123; status=exited(0); cwd=.; command=pytest", 0),
            ("Processes:\n  processes: 1\n  running: 1\n  items:\n    - bg-1: pid=123; status=running; cwd=.; command=server", 0),
        ]

        for text, expected_exit_code in cases:
            with self.subTest(text=text), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch("vibeagent.cli.get_processes_text", return_value=text),
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, "--processes"])

            self.assertEqual(exit_code, expected_exit_code)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            create_chat_client.assert_not_called()

    def test_main_processes_json_outputs_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "processes": {
                    "total": 1,
                    "running": 1,
                    "items": [
                        {
                            "processId": "bg-1",
                            "pid": 1234,
                            "command": "npm run dev",
                            "cwd": ".",
                            "running": True,
                            "exitCode": None,
                            "signal": None,
                            "status": "running",
                        }
                    ],
                },
                "message": "Found 1 background process(es).",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_processes_report", return_value=report) as get_processes_report,
                patch("vibeagent.cli.format_processes_report_text", return_value="Processes:\n  processes: 1\n  running: 1") as format_processes_report,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--processes"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["processes"], report)
        get_processes_report.assert_called_once_with(Path(base).resolve())
        format_processes_report.assert_called_once_with(report)
        create_chat_client.assert_not_called()
