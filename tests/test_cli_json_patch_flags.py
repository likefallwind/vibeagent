import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliJsonPatchFlagTests(unittest.TestCase):
    def test_main_runs_json_patch_local_flags_without_creating_client(self) -> None:
        operations = '[{"op":"replace","path":"/private","value":true}]'
        parsed_operations = [{"op": "replace", "path": "/private", "value": True}]
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_json_patch_text", return_value="Check JSON patch:\n  ok: yes") as get_check_json_patch_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-json-patch", "package.json", operations])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check JSON patch:", stdout.getvalue())
        get_check_json_patch_text.assert_called_once_with(Path(base).resolve(), path="package.json", operations=parsed_operations)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_json_patch_text", return_value="JSON patch:\n  ok: yes") as get_json_patch_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--json-patch", "package.json", operations])

        self.assertEqual(exit_code, 0)
        self.assertIn("JSON patch:", stdout.getvalue())
        get_json_patch_text.assert_called_once_with(Path(base).resolve(), path="package.json", operations=parsed_operations)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"projectRoot": str(Path(base).resolve()), "kind": "check_json_patch", "ok": True, "path": "package.json", "operations": {"total": 1, "items": parsed_operations}, "message": "JSON patch preview succeeded.", "diff": ""}

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_json_patch_report", return_value=report) as get_check_json_patch_report,
                patch("vibeagent.cli.format_json_patch_report_text", return_value="Check JSON patch:\n  ok: yes") as format_json_patch_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--check-json-patch", "package.json", operations])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["checkJsonPatch"], report)
        self.assertEqual(payload["text"], "Check JSON patch:\n  ok: yes")
        get_check_json_patch_report.assert_called_once_with(Path(base).resolve(), path="package.json", operations=parsed_operations)
        format_json_patch_report_text.assert_called_once_with("Check JSON patch:", report)
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"projectRoot": str(Path(base).resolve()), "kind": "json_patch", "ok": True, "path": "package.json", "operations": {"total": 1, "items": parsed_operations}, "message": "JSON patch applied.", "diff": ""}

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_json_patch_report", return_value=report) as get_json_patch_report,
                patch("vibeagent.cli.format_json_patch_report_text", return_value="JSON patch:\n  ok: yes") as format_json_patch_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--json-patch", "package.json", operations])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["jsonPatch"], report)
        self.assertEqual(payload["text"], "JSON patch:\n  ok: yes")
        get_json_patch_report.assert_called_once_with(Path(base).resolve(), path="package.json", operations=parsed_operations)
        format_json_patch_report_text.assert_called_once_with("JSON patch:", report)
        create_chat_client.assert_not_called()
