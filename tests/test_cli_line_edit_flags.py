import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliLineEditFlagTests(unittest.TestCase):
    def test_main_runs_line_edit_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_replace_lines_text", return_value="Check replace lines:\n  ok: yes") as get_check_replace_lines_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-replace-lines", "app.py", "2", "3", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check replace lines:", stdout.getvalue())
        get_check_replace_lines_text.assert_called_once_with(Path(base).resolve(), path="app.py", start_line="2", end_line="3", content="new\\n")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_replace_lines_text", return_value="Replace lines:\n  ok: yes") as get_replace_lines_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--replace-lines", "app.py", "2", "2", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Replace lines:", stdout.getvalue())
        get_replace_lines_text.assert_called_once_with(Path(base).resolve(), path="app.py", start_line="2", end_line="2", content="new\\n")
        create_chat_client.assert_not_called()

        cases = [
            (
                "--check-replace-lines",
                "vibeagent.cli.get_check_replace_lines_report",
                "Check replace lines:",
                "checkReplaceLines",
            ),
            (
                "--replace-lines",
                "vibeagent.cli.get_replace_lines_report",
                "Replace lines:",
                "replaceLines",
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
                    "startLine": 2,
                    "endLine": 2,
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
                    exit_code = main(["--json", "--cwd", base, flag, "app.py", "2", "2", "new\\n"])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path="app.py", start_line="2", end_line="2", content="new\\n")
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_insert_lines_text", return_value="Check insert lines:\n  ok: yes") as get_check_insert_lines_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-insert-lines", "app.py", "2", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check insert lines:", stdout.getvalue())
        get_check_insert_lines_text.assert_called_once_with(Path(base).resolve(), path="app.py", line="2", content="new\\n")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_insert_lines_text", return_value="Insert lines:\n  ok: yes") as get_insert_lines_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--insert-lines", "app.py", "2", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Insert lines:", stdout.getvalue())
        get_insert_lines_text.assert_called_once_with(Path(base).resolve(), path="app.py", line="2", content="new\\n")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_append_file_text", return_value="Check append:\n  ok: yes") as get_check_append_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-append", "app.py", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check append:", stdout.getvalue())
        get_check_append_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", content="new\\n")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_append_file_text", return_value="Append:\n  ok: yes") as get_append_file_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--append", "app.py", "new\\n"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Append:", stdout.getvalue())
        get_append_file_text.assert_called_once_with(Path(base).resolve(), path="app.py", content="new\\n")
        create_chat_client.assert_not_called()

        json_cases = [
            (
                "--check-insert-lines",
                "vibeagent.cli.get_check_insert_lines_report",
                "Check insert lines:",
                "checkInsertLines",
                ["app.py", "2", "new\\n"],
                {"path": "app.py", "line": "2", "content": "new\\n"},
                {"line": 2},
            ),
            (
                "--insert-lines",
                "vibeagent.cli.get_insert_lines_report",
                "Insert lines:",
                "insertLines",
                ["app.py", "2", "new\\n"],
                {"path": "app.py", "line": "2", "content": "new\\n"},
                {"line": 2},
            ),
            (
                "--check-append",
                "vibeagent.cli.get_check_append_file_report",
                "Check append:",
                "checkAppend",
                ["app.py", "tail\\n"],
                {"path": "app.py", "content": "tail\\n"},
                {},
            ),
            (
                "--append",
                "vibeagent.cli.get_append_file_report",
                "Append:",
                "append",
                ["app.py", "tail\\n"],
                {"path": "app.py", "content": "tail\\n"},
                {},
            ),
        ]
        for flag, getter_target, title, payload_key, cli_args, expected_kwargs, report_extra in json_cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": "app.py",
                    "message": "ok",
                    "diff": {"text": "+new", "lines": ["+new"], "lineCount": 1},
                    **report_extra,
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_line_edit_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, flag, *cli_args])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()
