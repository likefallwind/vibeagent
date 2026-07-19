import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliPythonRefactorFlagTests(unittest.TestCase):
    def test_main_runs_python_rename_preview_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_rename_preview_text", return_value="Python rename preview:\n  replacements: 2") as get_python_rename_preview_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-rename-preview", "run_agent", "execute_agent", "--python-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python rename preview:", stdout.getvalue())
        get_python_rename_preview_text.assert_called_once_with(Path(base).resolve(), symbol="run_agent", new_name="execute_agent", path="src")
        create_chat_client.assert_not_called()

    def test_main_runs_python_rename_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_rename_text", return_value="Python rename:\n  replacements: 2") as get_python_rename_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-rename", "run_agent", "execute_agent", "--python-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python rename:", stdout.getvalue())
        get_python_rename_text.assert_called_once_with(Path(base).resolve(), symbol="run_agent", new_name="execute_agent", path="src")
        create_chat_client.assert_not_called()

    def test_main_runs_replace_python_definition_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_replace_python_definition_text", return_value="Check replace Python definition:\n  ok: yes") as get_check_replace_python_definition_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--check-replace-python-def",
                        "Runner.run",
                        "    def run(self):\n        return 2\n",
                        "--python-path",
                        "src",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Check replace Python definition:", stdout.getvalue())
        get_check_replace_python_definition_text.assert_called_once_with(
            Path(base).resolve(),
            symbol="Runner.run",
            content="    def run(self):\n        return 2\n",
            path="src",
        )
        create_chat_client.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_replace_python_definition_text", return_value="Replace Python definition:\n  ok: yes") as get_replace_python_definition_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--replace-python-def",
                        "Runner.run",
                        "    def run(self):\n        return 2\n",
                        "--python-path",
                        "src",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Replace Python definition:", stdout.getvalue())
        get_replace_python_definition_text.assert_called_once_with(
            Path(base).resolve(),
            symbol="Runner.run",
            content="    def run(self):\n        return 2\n",
            path="src",
        )
        create_chat_client.assert_not_called()

    def test_main_runs_python_refactor_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--python-rename-preview", "run_agent", "execute_agent", "--python-path", "src"],
                "vibeagent.cli.get_python_rename_preview_report",
                "vibeagent.cli.format_python_rename_report_text",
                "Python rename preview:",
                "pythonRenamePreview",
                {"symbol": "run_agent", "new_name": "execute_agent", "path": "src"},
            ),
            (
                ["--python-rename", "run_agent", "execute_agent", "--python-path", "src"],
                "vibeagent.cli.get_python_rename_report",
                "vibeagent.cli.format_python_rename_report_text",
                "Python rename:",
                "pythonRename",
                {"symbol": "run_agent", "new_name": "execute_agent", "path": "src"},
            ),
            (
                ["--check-replace-python-def", "Runner.run", "    def run(self):\n        return 2\n", "--python-path", "src"],
                "vibeagent.cli.get_check_replace_python_definition_report",
                "vibeagent.cli.format_replace_python_definition_report_text",
                "Check replace Python definition:",
                "checkReplacePythonDefinition",
                {"symbol": "Runner.run", "content": "    def run(self):\n        return 2\n", "path": "src"},
            ),
            (
                ["--replace-python-def", "Runner.run", "    def run(self):\n        return 2\n", "--python-path", "src"],
                "vibeagent.cli.get_replace_python_definition_report",
                "vibeagent.cli.format_replace_python_definition_report_text",
                "Replace Python definition:",
                "replacePythonDefinition",
                {"symbol": "Runner.run", "content": "    def run(self):\n        return 2\n", "path": "src"},
            ),
        ]

        for argv_tail, getter_target, formatter_target, title, payload_key, expected_kwargs in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{payload_key}: ok"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch(formatter_target, return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
                formatter.assert_called_once_with(title, report)
                create_chat_client.assert_not_called()

    def test_main_check_replace_python_definition_local_flag_exits_nonzero_for_failed_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch(
                    "vibeagent.cli.get_check_replace_python_definition_text",
                    return_value="Check replace Python definition:\n  ok: no\n  message: Path does not exist: missing.py",
                ) as get_check_replace_python_definition_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--check-replace-python-def",
                        "Runner.run",
                        "    def run(self):\n        return 2\n",
                        "--python-path",
                        "missing.py",
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "Check replace Python definition:\n  ok: no\n  message: Path does not exist: missing.py\n")
        get_check_replace_python_definition_text.assert_called_once_with(
            Path(base).resolve(),
            symbol="Runner.run",
            content="    def run(self):\n        return 2\n",
            path="missing.py",
        )
        create_chat_client.assert_not_called()

    def test_main_check_replace_python_definition_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"ok": False, "message": "Python definition not found: Runner.run"}

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_replace_python_definition_report", return_value=report) as get_check_replace_python_definition_report,
                patch("vibeagent.cli.format_replace_python_definition_report_text", return_value="Check replace Python definition:\n  ok: no") as formatter,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--check-replace-python-def", "Runner.run", "content"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Check replace Python definition:\n  ok: no")
        self.assertEqual(payload["checkReplacePythonDefinition"], report)
        get_check_replace_python_definition_report.assert_called_once_with(Path(base).resolve(), symbol="Runner.run", content="content", path=None)
        formatter.assert_called_once_with("Check replace Python definition:", report)
        create_chat_client.assert_not_called()
