import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliExecutableFlagTests(unittest.TestCase):
    def test_main_runs_executable_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_set_executable_text", return_value="Check executable:\n  ok: yes") as get_check_set_executable_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-executable", "tool.sh", "false"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check executable:", stdout.getvalue())
        get_check_set_executable_text.assert_called_once_with(Path(base).resolve(), path="tool.sh", executable="false")
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_set_executable_text", return_value="Set executable:\n  ok: yes") as get_set_executable_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--set-executable", "tool.sh"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Set executable:", stdout.getvalue())
        get_set_executable_text.assert_called_once_with(Path(base).resolve(), path="tool.sh", executable=None)
        create_chat_client.assert_not_called()

        cases = [
            (
                ["--check-executable", "tool.sh", "false"],
                "vibeagent.cli.get_check_set_executable_report",
                "Check executable:",
                "checkSetExecutable",
                "false",
            ),
            (
                ["--set-executable", "tool.sh"],
                "vibeagent.cli.get_set_executable_report",
                "Set executable:",
                "setExecutable",
                None,
            ),
        ]
        for cli_args, getter_target, title, payload_key, expected_executable in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {
                    "projectRoot": str(Path(base).resolve()),
                    "kind": payload_key,
                    "ok": True,
                    "path": "tool.sh",
                    "executable": expected_executable != "false",
                    "modeBefore": "-rw-r--r--",
                    "modeAfter": "-rwxr-xr-x",
                    "message": "ok",
                }
                rendered = f"{title}\n  ok: yes"
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_executable_report_text", return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *cli_args])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], rendered)
                getter.assert_called_once_with(Path(base).resolve(), path="tool.sh", executable=expected_executable)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()
