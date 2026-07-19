import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliJsonSetFlagTests(unittest.TestCase):
    def test_main_runs_json_set_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_json_set_text", return_value="Check JSON set:\n  ok: yes") as get_check_json_set_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-json-set", "package.json", "/private", "true", "--json-create-missing"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check JSON set:", stdout.getvalue())
        get_check_json_set_text.assert_called_once_with(
            Path(base).resolve(),
            path="package.json",
            pointer="/private",
            value=True,
            create_missing=True,
        )
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_json_set_text", return_value="JSON set:\n  ok: yes") as get_json_set_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--json-set", "package.json", "/scripts/test", '"npm test"'])

        self.assertEqual(exit_code, 0)
        self.assertIn("JSON set:", stdout.getvalue())
        get_json_set_text.assert_called_once_with(
            Path(base).resolve(),
            path="package.json",
            pointer="/scripts/test",
            value="npm test",
            create_missing=False,
        )
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"projectRoot": str(Path(base).resolve()), "kind": "check_json_set", "ok": True, "path": "package.json", "pointer": "/private", "value": True, "createMissing": True, "message": "JSON set preview succeeded.", "diff": ""}

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_json_set_report", return_value=report) as get_check_json_set_report,
                patch("vibeagent.cli.format_json_pointer_report_text", return_value="Check JSON set:\n  ok: yes") as format_json_pointer_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--check-json-set", "package.json", "/private", "true", "--json-create-missing"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["checkJsonSet"], report)
        self.assertEqual(payload["text"], "Check JSON set:\n  ok: yes")
        get_check_json_set_report.assert_called_once_with(
            Path(base).resolve(),
            path="package.json",
            pointer="/private",
            value=True,
            create_missing=True,
        )
        format_json_pointer_report_text.assert_called_once_with("Check JSON set:", report)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"projectRoot": str(Path(base).resolve()), "kind": "json_set", "ok": True, "path": "package.json", "pointer": "/scripts/test", "value": "npm test", "createMissing": False, "message": "JSON value set.", "diff": ""}

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_json_set_report", return_value=report) as get_json_set_report,
                patch("vibeagent.cli.format_json_pointer_report_text", return_value="JSON set:\n  ok: yes") as format_json_pointer_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--json-set", "package.json", "/scripts/test", '"npm test"'])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["jsonSet"], report)
        self.assertEqual(payload["text"], "JSON set:\n  ok: yes")
        get_json_set_report.assert_called_once_with(
            Path(base).resolve(),
            path="package.json",
            pointer="/scripts/test",
            value="npm test",
            create_missing=False,
        )
        format_json_pointer_report_text.assert_called_once_with("JSON set:", report)
        create_chat_client.assert_not_called()

    def test_main_check_json_set_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "kind": "check_json_set",
                "ok": False,
                "path": "missing.json",
                "pointer": "/a",
                "value": 1,
                "createMissing": False,
                "message": "File does not exist",
                "diff": "",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_json_set_report", return_value=report) as get_check_json_set_report,
                patch("vibeagent.cli.format_json_pointer_report_text", return_value="Check JSON set:\n  ok: no\n  message: File does not exist") as format_json_pointer_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--check-json-set", "missing.json", "/a", "1"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["checkJsonSet"], report)
        self.assertIn("ok: no", payload["text"])
        get_check_json_set_report.assert_called_once_with(
            Path(base).resolve(),
            path="missing.json",
            pointer="/a",
            value=1,
            create_missing=False,
        )
        format_json_pointer_report_text.assert_called_once_with("Check JSON set:", report)
        create_chat_client.assert_not_called()
