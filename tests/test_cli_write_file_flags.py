import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliWriteFileFlagTests(unittest.TestCase):
    def test_main_runs_write_file_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_write_file_text", return_value="Check write:\n  ok: yes") as get_check_write_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-write", "app.py", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check write:", stdout.getvalue())
        get_check_write_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", content="new\\n")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_write_file_text", return_value="Write:\n  ok: yes") as get_write_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--write", "app.py", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Write:", stdout.getvalue())
        get_write_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", content="new\\n")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-write",
                "vibeagent.cli.get_check_write_file_report",
                "Check write:",
                "checkWrite",
            ),
            (
                "--write",
                "vibeagent.cli.get_write_file_report",
                "Write:",
                "write",
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
                    "diff": {"text": "+new", "lines": ["+new"], "lineCount": 1},
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_line_edit_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, "app.py", "new\\n"])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path="app.py", content="new\\n")
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_check_write_local_flag_exits_nonzero_when_not_ok(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch(
                    "vibeagent.cli.get_check_write_file_text",
                    return_value="Check write:\n  ok: no\n  message: Path is protected",
                ),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-write", ".git/config", "new\\n"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Check write:", stdout.getvalue())
        self.assertIn("ok: no", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_runs_write_files_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_write_files_text", return_value="Check write files:\n  ok: yes") as get_check_write_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-write-files", "app.py", "a\\n", "test.py", "b\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check write files:", stdout.getvalue())
        get_check_write_files_text.assert_called_once_with(Path(base).resolve(), files=["app.py", "a\\n", "test.py", "b\\n"])
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_write_files_text", return_value="Write files:\n  ok: yes") as get_write_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--write-files", "app.py", "a\\n", "test.py", "b\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Write files:", stdout.getvalue())
        get_write_files_text.assert_called_once_with(Path(base).resolve(), files=["app.py", "a\\n", "test.py", "b\\n"])
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-write-files",
                "vibeagent.cli.get_check_write_files_report",
                "Check write files:",
                "checkWriteFiles",
            ),
            (
                "--write-files",
                "vibeagent.cli.get_write_files_report",
                "Write files:",
                "writeFiles",
            ),
        ]
        for flag, getter_target, title, payload_key in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "files": {
                        "total": 2,
                        "items": [
                            {"path": "app.py", "ok": True, "message": "ok", "diff": {"text": "+a", "lines": ["+a"], "lineCount": 1}},
                            {"path": "test.py", "ok": True, "message": "ok", "diff": {"text": "+b", "lines": ["+b"], "lineCount": 1}},
                        ],
                    },
                    "message": "ok",
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_write_files_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, "app.py", "a\\n", "test.py", "b\\n"])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), files=["app.py", "a\\n", "test.py", "b\\n"])
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()
