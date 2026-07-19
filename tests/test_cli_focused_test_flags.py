import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliFocusedTestFlagTests(unittest.TestCase):
    def test_main_runs_focused_tests_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_focused_test_commands_text", return_value="Focused test commands:\n  commands: 1/1") as get_focused_test_commands_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--focused-tests", "pkg/actions.py", "tests/test_actions.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Focused test commands:", stdout.getvalue())
        get_focused_test_commands_text.assert_called_once_with(Path(base).resolve(), "pkg/actions.py tests/test_actions.py")
        create_chat_client.assert_not_called()

    def test_main_runs_focused_tests_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_focused_test_commands_text", return_value="Focused test commands:\n  commands: 1/2") as get_focused_test_commands_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--focused-tests",
                        "pkg/actions.py",
                        "--focused-tests-max-paths",
                        "3",
                        "--focused-tests-max-candidates",
                        "4",
                        "--focused-tests-max-commands",
                        "5",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Focused test commands:", stdout.getvalue())
        get_focused_test_commands_text.assert_called_once_with(Path(base).resolve(), "pkg/actions.py", max_paths=3, max_candidates=4, max_commands=5)
        create_chat_client.assert_not_called()

    def test_main_runs_check_focused_tests_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_focused_test_commands_text", return_value="Check focused test commands:\n  ok: yes") as get_check_focused_test_commands_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-focused-tests", "pkg/actions.py", "tests/test_actions.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check focused test commands:", stdout.getvalue())
        get_check_focused_test_commands_text.assert_called_once_with(Path(base).resolve(), "pkg/actions.py tests/test_actions.py")
        create_chat_client.assert_not_called()

    def test_main_rejects_focused_tests_bounds_without_focused_tests_local_flag(self) -> None:
        cases = [
            (["--focused-tests-max-paths", "3"], "--focused-tests-max-paths can only be used with --focused-tests, --check-focused-tests, or --run-focused-tests."),
            (["--focused-tests-max-candidates", "4"], "--focused-tests-max-candidates can only be used with --focused-tests, --check-focused-tests, or --run-focused-tests."),
            (["--focused-tests-max-commands", "5"], "--focused-tests-max-commands can only be used with --focused-tests, --check-focused-tests, or --run-focused-tests."),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with redirect_stdout(stdout):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertIn(expected, stdout.getvalue())

    def test_main_runs_run_focused_tests_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_focused_test_commands_text", return_value="Run focused test commands:\n  ok: yes") as get_run_focused_test_commands_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--run-focused-tests",
                        "pkg/actions.py",
                        "tests/test_actions.py",
                        "--run-timeout-ms",
                        "2000",
                        "--run-max-chars",
                        "3000",
                        "--run-continue-on-failure",
                        "--run-output-contexts",
                        "--run-output-diagnostics",
                        "--run-output-context-lines",
                        "2",
                        "--run-output-diagnostic-max",
                        "7",
                        "--run-output-context-max",
                        "5",
                        "--run-output-context-max-bytes",
                        "1000",
                        "--focused-tests-max-paths",
                        "3",
                        "--focused-tests-max-candidates",
                        "4",
                        "--focused-tests-max-commands",
                        "5",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Run focused test commands:", stdout.getvalue())
        get_run_focused_test_commands_text.assert_called_once_with(
            Path(base).resolve(),
            "pkg/actions.py tests/test_actions.py",
            max_paths=3,
            max_candidates=4,
            max_commands=5,
            timeout_ms=2000,
            max_output_chars=3000,
            stop_on_failure=False,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_focused_tests_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base).resolve()
            cases = [
                (
                    ["--focused-tests", "pkg/actions.py", "--focused-tests-max-paths", "3", "--focused-tests-max-candidates", "4", "--focused-tests-max-commands", "5"],
                    "vibeagent.cli.get_focused_test_commands_report",
                    "vibeagent.cli.format_focused_test_commands_report_text",
                    "focusedTests",
                    "Focused test commands:\n  commands: 1/1",
                    {"argument": "pkg/actions.py", "max_paths": 3, "max_candidates": 4, "max_commands": 5},
                ),
                (
                    ["--check-focused-tests", "pkg/actions.py"],
                    "vibeagent.cli.get_check_focused_test_commands_report",
                    "vibeagent.cli.format_check_focused_test_commands_report_text",
                    "checkFocusedTests",
                    "Check focused test commands:\n  ok: yes",
                    {"argument": "pkg/actions.py"},
                ),
                (
                    [
                        "--run-focused-tests",
                        "pkg/actions.py",
                        "--run-timeout-ms",
                        "2000",
                        "--run-max-chars",
                        "3000",
                        "--run-continue-on-failure",
                        "--run-output-contexts",
                    ],
                    "vibeagent.cli.get_run_focused_test_commands_report",
                    "vibeagent.cli.format_run_focused_test_commands_report_text",
                    "runFocusedTests",
                    "Run focused test commands:\n  ok: yes",
                    {
                        "argument": "pkg/actions.py",
                        "timeout_ms": 2000,
                        "max_output_chars": 3000,
                        "stop_on_failure": False,
                        "extract_output_contexts": True,
                        "extract_output_diagnostics": False,
                        "context_lines": 5,
                        "max_diagnostics": 50,
                        "max_contexts": 20,
                        "max_bytes_per_context": 20000,
                    },
                ),
            ]

            for argv_tail, report_target, format_target, payload_key, text, expected_kwargs in cases:
                with self.subTest(payload_key=payload_key):
                    stdout = io.StringIO()
                    report = {"projectRoot": str(root), "ok": True, "message": "ok"}
                    with (
                        patch("vibeagent.cli.create_chat_client") as create_chat_client,
                        patch(report_target, return_value=report) as get_report,
                        patch(format_target, return_value=text) as format_report,
                        redirect_stdout(stdout),
                    ):
                        exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], text)
                get_report.assert_called_once_with(root, **expected_kwargs)
                format_report.assert_called_once_with(report)
                create_chat_client.assert_not_called()
