import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliLocalInspectionFlagTests(unittest.TestCase):
    def test_main_runs_tool_local_flag_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--tool", "read_file"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Tool: read_file", stdout.getvalue())
        self.assertIn("input:", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_runs_tool_local_flag_with_json_output(self) -> None:
        stdout = io.StringIO()
        report = {
            "ok": True,
            "found": True,
            "name": "write_file",
            "category": "edit",
            "description": "Write a file after approval.",
            "approvalRequired": True,
            "required": ["path", "content"],
            "properties": [{"name": "path", "type": "string", "required": True}],
            "schema": {"type": "object", "properties": {"path": {"type": "string"}}},
            "message": "Found tool: write_file.",
        }

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tool_report", return_value=report) as get_tool_report,
            patch("vibeagent.cli.format_tool_report_text", return_value="Tool: write_file\n  approvalRequired: yes"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--tool", "write_file"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "completed")
        self.assertIn("Tool: write_file", payload["text"])
        self.assertIn("approvalRequired: yes", payload["text"])
        self.assertEqual(payload["tool"], report)
        get_tool_report.assert_called_once_with("write_file")
        create_chat_client.assert_not_called()

    def test_main_tool_local_flag_exits_nonzero_for_missing_tool(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tool_text", return_value="Tool not found: missing_tool."),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--tool", "missing_tool"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "Tool not found: missing_tool.\n")
        create_chat_client.assert_not_called()

    def test_main_tool_local_flag_reports_json_failure_for_missing_tool(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tool_report", return_value={"ok": False, "found": False, "name": "missing_tool", "suggestions": [], "message": "Tool not found: missing_tool."}),
            patch("vibeagent.cli.format_tool_report_text", return_value="Tool not found: missing_tool."),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--tool", "missing_tool"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Tool not found: missing_tool.")
        self.assertEqual(payload["tool"]["name"], "missing_tool")
        create_chat_client.assert_not_called()

    def test_main_runs_permissions_local_flag_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_permissions_report") as get_permissions_report,
            patch("vibeagent.cli.get_permissions_text", return_value="Permissions:\n  approvalPolicy: deny") as get_permissions_text,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--approval", "deny", "--permissions"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Permissions:", stdout.getvalue())
        get_permissions_report.assert_not_called()
        get_permissions_text.assert_called_once_with("deny", ".")
        create_chat_client.assert_not_called()

    def test_main_runs_permissions_json_with_structured_payload(self) -> None:
        report = {
            "approvalPolicy": "allow",
            "approvalRequiredTools": {"count": 1, "tools": ["write_file"], "byCategory": {"edit": ["write_file"]}},
            "readOnlyTools": {"count": 1, "tools": ["read_file"]},
            "commandHardBlocks": {"active": 1, "total": 1, "checks": [{"command": "code .", "active": True, "reason": "GUI application launch is blocked."}]},
        }
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_permissions_report", return_value=report) as get_permissions_report,
            patch("vibeagent.cli.format_permissions_report_text", return_value="Permissions:\n  approvalPolicy: allow") as format_permissions_report_text,
            patch("vibeagent.cli.get_permissions_text") as get_permissions_text,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--approval", "allow", "--permissions"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["success"])
        self.assertIn("Permissions:", payload["text"])
        permissions = payload["permissions"]
        self.assertEqual(permissions["approvalPolicy"], "allow")
        self.assertIn("write_file", permissions["approvalRequiredTools"]["tools"])
        self.assertIn("read_file", permissions["readOnlyTools"]["tools"])
        self.assertEqual(permissions["commandHardBlocks"]["active"], permissions["commandHardBlocks"]["total"])
        self.assertTrue(any(check["command"] == "code ." and check["active"] for check in permissions["commandHardBlocks"]["checks"]))
        get_permissions_report.assert_called_once_with("allow", ".")
        format_permissions_report_text.assert_called_once_with(report)
        get_permissions_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_checks_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checks_report", return_value={"suggestedChecks": {"shown": 1}}) as get_checks_report,
                patch("vibeagent.cli.get_checks_text", return_value="Checks:\n  suggestedChecks: 1/1") as get_checks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checks"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checks:", stdout.getvalue())
        get_checks_report.assert_not_called()
        get_checks_text.assert_called_once_with(Path(base).resolve(), max_checks=20)
        create_chat_client.assert_not_called()

    def test_main_runs_checks_local_flag_with_max_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checks_report", return_value={"suggestedChecks": {"shown": 1}}) as get_checks_report,
                patch("vibeagent.cli.get_checks_text", return_value="Checks:\n  suggestedChecks: 1/3") as get_checks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--checks", "--checks-max", "1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Checks:", stdout.getvalue())
        get_checks_report.assert_not_called()
        get_checks_text.assert_called_once_with(Path(base).resolve(), max_checks=1)
        create_chat_client.assert_not_called()

    def test_main_runs_checks_json_with_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            stdout = io.StringIO()
            report = {
                "projectRoot": str(root.resolve()),
                "suggestedChecks": {
                    "shown": 2,
                    "total": 2,
                    "truncated": False,
                    "commands": [
                        {"command": "npm run test"},
                        {"command": "python -m unittest discover -s tests"},
                    ],
                },
                "changedFiles": [],
                "message": "Suggested 2 check(s).",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_checks_report", return_value=report) as get_checks_report,
                patch("vibeagent.cli.format_checks_report_text", return_value="Checks:\n  suggestedChecks: 2/2") as format_checks_report_text,
                patch("vibeagent.cli.get_checks_text") as get_checks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--checks", "--checks-max", "10"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["success"])
        self.assertIn("Checks:", payload["text"])
        checks = payload["checks"]
        self.assertEqual(checks["projectRoot"], str(root.resolve()))
        suggested = checks["suggestedChecks"]
        self.assertIsInstance(suggested["commands"], list)
        commands = [item["command"] for item in suggested["commands"] if isinstance(item, dict)]
        self.assertIn("npm run test", commands)
        self.assertIn("python -m unittest discover -s tests", commands)
        get_checks_report.assert_called_once_with(Path(base).resolve(), max_checks=10)
        format_checks_report_text.assert_called_once_with(report)
        get_checks_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_checks_max_without_checks_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--checks-max", "1", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--checks-max can only be used with --checks.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_check_suggested_checks_max_without_check_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--check-suggested-checks-max", "1", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--check-suggested-checks-max can only be used with --check-suggested-checks.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_run_suggested_checks_max_without_run_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--run-suggested-checks-max", "1", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--run-suggested-checks-max can only be used with --run-suggested-checks.\n")
        create_chat_client.assert_not_called()

    def test_main_runs_check_suggested_checks_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_suggested_checks_text", return_value="Check suggested checks:\n  ok: yes") as get_check_suggested_checks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-suggested-checks", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check suggested checks:", stdout.getvalue())
        get_check_suggested_checks_text.assert_called_once_with(Path(base).resolve(), "2", max_checks=10)
        create_chat_client.assert_not_called()

    def test_main_runs_check_suggested_checks_local_flag_with_named_max(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_check_suggested_checks_text", return_value="Check suggested checks:\n  ok: yes") as get_check_suggested_checks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--check-suggested-checks", "--check-suggested-checks-max", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Check suggested checks:", stdout.getvalue())
        get_check_suggested_checks_text.assert_called_once_with(Path(base).resolve(), None, max_checks=2)
        create_chat_client.assert_not_called()

    def test_main_runs_run_suggested_checks_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_suggested_checks_text", return_value="Run suggested checks:\n  ok: yes") as get_run_suggested_checks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--run-suggested-checks",
                        "2",
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
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Run suggested checks:", stdout.getvalue())
        get_run_suggested_checks_text.assert_called_once_with(
            Path(base).resolve(),
            "2",
            max_checks=10,
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

    def test_main_runs_run_suggested_checks_local_flag_with_named_max(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_run_suggested_checks_text", return_value="Run suggested checks:\n  ok: yes") as get_run_suggested_checks_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--run-suggested-checks", "--run-suggested-checks-max", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Run suggested checks:", stdout.getvalue())
        get_run_suggested_checks_text.assert_called_once_with(
            Path(base).resolve(),
            None,
            max_checks=2,
            timeout_ms=30000,
            max_output_chars=12000,
            stop_on_failure=True,
            extract_output_contexts=False,
            extract_output_diagnostics=False,
            context_lines=5,
            max_diagnostics=50,
            max_contexts=20,
            max_bytes_per_context=20000,
        )
        create_chat_client.assert_not_called()

    def test_main_suggested_checks_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base).resolve()
            cases = [
                (
                    ["--check-suggested-checks", "2"],
                    "vibeagent.cli.get_check_suggested_checks_report",
                    "vibeagent.cli.format_check_suggested_checks_report_text",
                    "checkSuggestedChecks",
                    "Check suggested checks:\n  ok: yes",
                    {"argument": "2", "max_checks": 10},
                ),
                (
                    [
                        "--run-suggested-checks",
                        "2",
                        "--run-timeout-ms",
                        "2000",
                        "--run-max-chars",
                        "3000",
                        "--run-continue-on-failure",
                        "--run-output-contexts",
                        "--run-output-diagnostics",
                    ],
                    "vibeagent.cli.get_run_suggested_checks_report",
                    "vibeagent.cli.format_run_suggested_checks_report_text",
                    "runSuggestedChecks",
                    "Run suggested checks:\n  ok: yes",
                    {
                        "argument": "2",
                        "max_checks": 10,
                        "timeout_ms": 2000,
                        "max_output_chars": 3000,
                        "stop_on_failure": False,
                        "extract_output_contexts": True,
                        "extract_output_diagnostics": True,
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

    def test_main_parses_interactive_run_suggested_check_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-suggested-checks --timeout-ms 2000 --max-chars 3000 --continue-on-failure --output-contexts --output-diagnostics --context-lines 2 --max-diagnostics 7 --max-contexts 5 --max-bytes 1000 -- 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_suggested_checks_text", return_value="Run suggested checks:\n  ok: yes") as get_run_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run suggested checks:", output)
        get_run_suggested_checks_text.assert_called_once_with(
            argument="2",
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

    def test_main_parses_interactive_run_suggested_check_named_max_option(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-suggested-checks --max-checks 2 --timeout-ms 2000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_suggested_checks_text", return_value="Run suggested checks:\n  ok: yes") as get_run_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run suggested checks:", output)
        get_run_suggested_checks_text.assert_called_once_with(
            argument=None,
            max_checks=2,
            timeout_ms=2000,
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_check_suggested_check_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/check-suggested-checks --max-checks 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_check_suggested_checks_text", return_value="Check suggested checks:\n  ok: yes") as get_check_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Check suggested checks:", output)
        get_check_suggested_checks_text.assert_called_once_with(max_checks=2)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_check_suggested_check_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/check-suggested-checks --max-checks 0",
                    "/check-suggested-checks --bad",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_check_suggested_checks_text") as get_check_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /check-suggested-checks [--max-checks N]", output)
        self.assertIn("--max-checks must be a positive integer.", output)
        self.assertIn("Unknown option: --bad", output)
        get_check_suggested_checks_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_run_suggested_check_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-suggested-checks --timeout-ms 99 -- 2",
                    "/run-suggested-checks --context-lines -1 -- 2",
                    "/run-suggested-checks --output-diagnostics=true -- 2",
                    "/run-suggested-checks --output-contexts -- 1 2",
                    "/run-suggested-checks --max-checks 1 -- 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_suggested_checks_text") as get_run_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /run-suggested-checks [--max-checks N]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("--output-diagnostics does not take a value.", output)
        self.assertIn("expected at most one max value.", output)
        self.assertIn("provide either --max-checks or trailing max, not both.", output)
        get_run_suggested_checks_text.assert_not_called()
        create_chat_client.assert_not_called()
