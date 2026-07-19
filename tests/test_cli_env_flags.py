import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliEnvFlagTests(unittest.TestCase):
    def test_main_runs_env_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_env_text", return_value="Environment:\n  tools: 3/9") as get_env_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--env"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Environment:", stdout.getvalue())
        get_env_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_env_local_flag_as_json_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "platform": "linux",
                "pythonVersion": "3.11",
                "pythonExecutable": "/usr/bin/python3",
                "gitRepo": False,
                "tools": {"available": 2, "total": 2, "items": []},
                "message": "Environment inspected.",
            }
            rendered = "Environment:\n  tools: 2/2"

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_env_report", return_value=report) as get_env_report,
                patch("vibeagent.cli.format_env_report_text", return_value=rendered) as format_env_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--env"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["text"], rendered)
        self.assertEqual(payload["env"], report)
        get_env_report.assert_called_once_with(Path(base).resolve())
        format_env_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()
