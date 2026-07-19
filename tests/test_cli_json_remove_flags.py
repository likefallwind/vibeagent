import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliJsonRemoveFlagTests(unittest.TestCase):
    def test_main_runs_json_remove_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_json_remove_text", return_value="Check JSON remove:\n  ok: yes") as get_check_json_remove_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-json-remove", "package.json", "/scripts/dev"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check JSON remove:", stdout.getvalue())
        get_check_json_remove_text.assert_called_once_with(Path(base).resolve(), path="package.json", pointer="/scripts/dev")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_json_remove_text", return_value="JSON remove:\n  ok: yes") as get_json_remove_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--json-remove", "package.json", "/keywords/0"])

        self.assertEqual(exit_code, 0)
        self.assertIn("JSON remove:", stdout.getvalue())
        get_json_remove_text.assert_called_once_with(Path(base).resolve(), path="package.json", pointer="/keywords/0")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"projectRoot": str(Path(base).resolve()), "kind": "check_json_remove", "ok": True, "path": "package.json", "pointer": "/scripts/dev", "message": "JSON remove preview succeeded.", "diff": ""}

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_json_remove_report", return_value=report) as get_check_json_remove_report,
                patch("vibeagent.cli.format_json_pointer_report_text", return_value="Check JSON remove:\n  ok: yes") as format_json_pointer_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--check-json-remove", "package.json", "/scripts/dev"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["checkJsonRemove"], report)
        self.assertEqual(payload["text"], "Check JSON remove:\n  ok: yes")
        get_check_json_remove_report.assert_called_once_with(Path(base).resolve(), path="package.json", pointer="/scripts/dev")
        format_json_pointer_report_text.assert_called_once_with("Check JSON remove:", report)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"projectRoot": str(Path(base).resolve()), "kind": "json_remove", "ok": True, "path": "package.json", "pointer": "/keywords/0", "message": "JSON value removed.", "diff": ""}

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_json_remove_report", return_value=report) as get_json_remove_report,
                patch("vibeagent.cli.format_json_pointer_report_text", return_value="JSON remove:\n  ok: yes") as format_json_pointer_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--json-remove", "package.json", "/keywords/0"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["jsonRemove"], report)
        self.assertEqual(payload["text"], "JSON remove:\n  ok: yes")
        get_json_remove_report.assert_called_once_with(Path(base).resolve(), path="package.json", pointer="/keywords/0")
        format_json_pointer_report_text.assert_called_once_with("JSON remove:", report)
        create_chat_client.assert_not_called()
