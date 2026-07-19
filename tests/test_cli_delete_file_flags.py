import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliDeleteFileFlagTests(unittest.TestCase):
    def test_main_runs_delete_file_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_delete_file_text", return_value="Check delete:\n  ok: yes") as get_check_delete_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-delete", "old.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check delete:", stdout.getvalue())
        get_check_delete_file_text.assert_called_once_with(Path(base).resolve(), path="old.py")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_delete_file_text", return_value="Delete:\n  ok: yes") as get_delete_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--delete", "old.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Delete:", stdout.getvalue())
        get_delete_file_text.assert_called_once_with(Path(base).resolve(), path="old.py")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-delete",
                "vibeagent.cli.get_check_delete_file_report",
                "Check delete:",
                "checkDelete",
            ),
            (
                "--delete",
                "vibeagent.cli.get_delete_file_report",
                "Delete:",
                "delete",
            ),
        ]
        for flag, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": "old.py",
                    "message": "ok",
                    "diff": {"text": "-old", "lines": ["-old"], "lineCount": 1},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_line_edit_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, "old.py"])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path="old.py")
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_runs_delete_files_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_delete_files_text", return_value="Check delete files:\n  ok: yes") as get_check_delete_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-delete-files", "old.py", "other.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check delete files:", stdout.getvalue())
        get_check_delete_files_text.assert_called_once_with(Path(base).resolve(), paths=["old.py", "other.py"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_delete_files_text", return_value="Delete files:\n  ok: yes") as get_delete_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--delete-files", "old.py", "other.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Delete files:", stdout.getvalue())
        get_delete_files_text.assert_called_once_with(Path(base).resolve(), paths=["old.py", "other.py"])
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-delete-files",
                "vibeagent.cli.get_check_delete_files_report",
                "Check delete files:",
                "checkDeleteFiles",
            ),
            (
                "--delete-files",
                "vibeagent.cli.get_delete_files_report",
                "Delete files:",
                "deleteFiles",
            ),
        ]
        for flag, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "paths": {"total": 2, "items": ["old.py", "other.py"]},
                    "message": "ok",
                    "diff": {"text": "-old", "lines": ["-old"], "lineCount": 1},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_path_list_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, "old.py", "other.py"])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), paths=["old.py", "other.py"])
                formatter.assert_called_once_with(title, report, include_diff=True)
                create_chat_client.assert_not_called()
