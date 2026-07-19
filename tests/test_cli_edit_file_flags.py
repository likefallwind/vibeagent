import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliEditFileFlagTests(unittest.TestCase):
    def test_main_runs_edit_file_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_edit_file_text", return_value="Check edit:\n  ok: yes") as get_check_edit_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-edit", "app.py", "old", "new"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check edit:", stdout.getvalue())
        get_check_edit_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", old="old", new="new")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_edit_file_text", return_value="Edit:\n  ok: yes") as get_edit_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--edit", "app.py", "old", "new"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Edit:", stdout.getvalue())
        get_edit_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", old="old", new="new")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-edit",
                "vibeagent.cli.get_check_edit_file_report",
                "Check edit:",
                "checkEdit",
            ),
            (
                "--edit",
                "vibeagent.cli.get_edit_file_report",
                "Edit:",
                "edit",
            ),
        ]
        for flag, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": "app.py",
                    "message": "ok",
                    "diff": {"text": "-old\n+new", "lines": ["-old", "+new"], "lineCount": 2},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_line_edit_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, "app.py", "old", "new"])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path="app.py", old="old", new="new")
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_multi_edit_file_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_multi_edit_file_text", return_value="Check multi edit:\n  ok: yes") as get_check_multi_edit_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-multi-edit", "app.py", "old", "new", "print", "log"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check multi edit:", stdout.getvalue())
        get_check_multi_edit_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", edits=["old", "new", "print", "log"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_multi_edit_file_text", return_value="Multi edit:\n  ok: yes") as get_multi_edit_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--multi-edit", "app.py", "old", "new", "print", "log"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Multi edit:", stdout.getvalue())
        get_multi_edit_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", edits=["old", "new", "print", "log"])
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-multi-edit",
                "vibeagent.cli.get_check_multi_edit_file_report",
                "Check multi edit:",
                "checkMultiEdit",
            ),
            (
                "--multi-edit",
                "vibeagent.cli.get_multi_edit_file_report",
                "Multi edit:",
                "multiEdit",
            ),
        ]
        for flag, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": "app.py",
                    "message": "ok",
                    "diff": {"text": "-old\n+new", "lines": ["-old", "+new"], "lineCount": 2},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_line_edit_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, "app.py", "old", "new", "print", "log"])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path="app.py", edits=["old", "new", "print", "log"])
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()
