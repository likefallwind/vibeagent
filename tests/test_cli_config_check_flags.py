import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliConfigCheckFlagTests(unittest.TestCase):
    def test_main_runs_config_check_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_config_check_text", return_value="Config check:\n  ok: yes") as get_config_check_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--config-check", "pyproject.toml"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Config check:", stdout.getvalue())
        get_config_check_text.assert_called_once_with(Path(base).resolve(), "pyproject.toml")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "path": "pyproject.toml",
                "files": {"shown": 1, "total": 1, "items": [{"path": "pyproject.toml", "ok": True, "format": "toml", "line": None, "column": None, "message": "ok"}]},
                "truncated": False,
                "message": "Checked 1/1 config file(s); 0 failed.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_config_check_report", return_value=report) as get_config_check_report,
                patch("vibeagent.cli.format_config_check_report_text", return_value="Config check:\n  ok: yes") as format_config_check_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--config-check", "pyproject.toml"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["configCheck"], report)
        self.assertEqual(payload["text"], "Config check:\n  ok: yes")
        get_config_check_report.assert_called_once_with(Path(base).resolve(), "pyproject.toml")
        format_config_check_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_config_check_local_flag_exits_nonzero_when_not_ok(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_config_check_text", return_value="Config check:\n  ok: no\n  message: invalid"),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--config-check", "pyproject.toml"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Config check:", stdout.getvalue())
        self.assertIn("ok: no", stdout.getvalue())
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "path": "pyproject.toml",
                "files": {"shown": 1, "total": 1, "items": [{"path": "pyproject.toml", "ok": False, "format": "toml", "line": 1, "column": 1, "message": "invalid"}]},
                "truncated": False,
                "message": "Checked 1/1 config file(s); 1 failed.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_config_check_report", return_value=report) as get_config_check_report,
                patch("vibeagent.cli.format_config_check_report_text", return_value="Config check:\n  ok: no\n  message: invalid") as format_config_check_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--config-check", "pyproject.toml"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["configCheck"], report)
        self.assertIn("ok: no", payload["text"])
        get_config_check_report.assert_called_once_with(Path(base).resolve(), "pyproject.toml")
        format_config_check_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()
