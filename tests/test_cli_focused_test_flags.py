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

    def test_main_parses_interactive_run_focused_test_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-focused-tests --max-paths 3 --max-candidates 4 --max-commands 5 --timeout-ms 2000 --max-chars 3000 --continue-on-failure --output-contexts --output-diagnostics --context-lines 2 --max-diagnostics 7 --max-contexts 5 --max-bytes 1000 -- pkg/actions.py tests/test_actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_focused_test_commands_text", return_value="Run focused test commands:\n  ok: yes") as get_run_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run focused test commands:", output)
        get_run_focused_test_commands_text.assert_called_once_with(
            argument="pkg/actions.py tests/test_actions.py",
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

    def test_main_parses_interactive_related_and_focused_test_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/related-tests --max-paths 3 --max-candidates 4 -- pkg/actions.py",
                    "/focused-tests --max-paths 5 --max-candidates 6 --max-commands 7 -- pkg/actions.py",
                    "/check-focused-tests --max-paths 8 --max-candidates 9 --max-commands 10 -- pkg/actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_related_tests_text", return_value="Related tests:\n  candidates: 1/1") as get_related_tests_text,
            patch("vibeagent.cli.get_focused_test_commands_text", return_value="Focused test commands:\n  commands: 1/1") as get_focused_test_commands_text,
            patch("vibeagent.cli.get_check_focused_test_commands_text", return_value="Check focused test commands:\n  ok: yes") as get_check_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Related tests:", output)
        self.assertIn("Focused test commands:", output)
        self.assertIn("Check focused test commands:", output)
        get_related_tests_text.assert_called_once_with(argument="pkg/actions.py", max_paths=3, max_candidates=4)
        get_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py", max_paths=5, max_candidates=6, max_commands=7)
        get_check_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py", max_paths=8, max_candidates=9, max_commands=10)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_test_limit_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/related-tests --max-paths 0 -- pkg/actions.py",
                    "/focused-tests --max-commands 0 -- pkg/actions.py",
                    "/check-focused-tests --unknown 1 -- pkg/actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_related_tests_text") as get_related_tests_text,
            patch("vibeagent.cli.get_focused_test_commands_text") as get_focused_test_commands_text,
            patch("vibeagent.cli.get_check_focused_test_commands_text") as get_check_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /related-tests [--max-paths N]", output)
        self.assertIn("--max-paths must be a positive integer.", output)
        self.assertIn("Usage: /focused-tests [--max-paths N]", output)
        self.assertIn("--max-commands must be a positive integer.", output)
        self.assertIn("Usage: /check-focused-tests [--max-paths N]", output)
        self.assertIn("Unknown option: --unknown", output)
        get_related_tests_text.assert_not_called()
        get_focused_test_commands_text.assert_not_called()
        get_check_focused_test_commands_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_run_focused_test_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-focused-tests --timeout-ms 99 -- pkg/actions.py",
                    "/run-focused-tests --max-bytes 0 -- pkg/actions.py",
                    "/run-focused-tests --output-contexts=true -- pkg/actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_focused_test_commands_text") as get_run_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /run-focused-tests [--max-paths N]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("--output-contexts does not take a value.", output)
        get_run_focused_test_commands_text.assert_not_called()
        create_chat_client.assert_not_called()
