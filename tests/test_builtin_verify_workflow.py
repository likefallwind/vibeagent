from __future__ import annotations

from contextlib import redirect_stdout
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.agent import AgentResult
from vibeagent.builtin_verify_workflow import build_verify_workflow, parse_verify_goal
from vibeagent.cli import main
from vibeagent.cli_project_command_expansion import expand_one_shot_project_command
from vibeagent.command_parsing import LocalCommand, parse_local_command


class BuiltinVerifyWorkflowTests(unittest.TestCase):
    def test_builds_evidence_driven_application_workflow(self) -> None:
        workflow = build_verify_workflow('"login flow"')

        self.assertIn('Verification goal: "login flow"', workflow.task)
        self.assertIn("externally observable acceptance criteria", workflow.task)
        self.assertIn("most specific run-* skill", workflow.task)
        self.assertIn("start_command", workflow.task)
        self.assertIn("port_check", workflow.task)
        self.assertIn("http_check or http_fetch", workflow.task)
        self.assertIn("browser-capable", workflow.task)
        self.assertIn("report the visual and interaction criteria as unverified", workflow.task)
        self.assertIn("Never stop a process that was already running", workflow.task)
        self.assertIn("PASS, FAIL, or UNVERIFIED", workflow.task)
        self.assertEqual(workflow.metadata["name"], "verify")
        self.assertEqual(workflow.metadata["goal"], "login flow")

    def test_default_goal_covers_current_changes(self) -> None:
        workflow = build_verify_workflow(None)

        self.assertIn("behavior affected by the current changes", workflow.task)
        self.assertIsNone(workflow.metadata["goal"])

    def test_goal_parser_is_bounded_and_fail_closed(self) -> None:
        self.assertEqual(parse_verify_goal("-- --generated app"), "--generated app")
        for argument, message in (
            ("--fix", "Unknown"),
            ("'unterminated", "invalid"),
            ("x" * 4001, "4000"),
            ("bad\x00goal", "NUL"),
        ):
            with self.subTest(argument=argument), self.assertRaisesRegex(ValueError, message):
                parse_verify_goal(argument)

    def test_one_shot_verify_expands_before_provider_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-verify-") as base:
            task, metadata = expand_one_shot_project_command(Path(base), "/verify api health")

        self.assertIn('Verification goal: "api health"', task)
        self.assertEqual(metadata["source"], "builtin_command")
        self.assertEqual(metadata["name"], "verify")

    def test_existing_run_command_keeps_finite_shell_semantics(self) -> None:
        self.assertEqual(
            parse_local_command("/run python3 --version"),
            LocalCommand(type="run", argument="python3 --version"),
        )

    def test_interactive_verify_runs_with_workflow_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-verify-") as base:
            root = Path(base)
            result = AgentResult(True, "verified", root, "verify-run", 1, [], [])
            run_agent = Mock(return_value=result)
            with (
                patch("builtins.input", side_effect=["/verify login flow", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertIn('Verification goal: "login flow"', run_agent.call_args.args[0])
        self.assertEqual(run_agent.call_args.kwargs["task_metadata"]["name"], "verify")

    def test_print_verify_runs_with_workflow_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-verify-") as base:
            root = Path(base)
            result = AgentResult(True, "verified", root, "verify-run", 1, [], [])
            run_agent = Mock(return_value=result)
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(root), "--print", "/verify api health"])

        self.assertEqual(exit_code, 0)
        self.assertIn('Verification goal: "api health"', run_agent.call_args.args[0])
        self.assertEqual(run_agent.call_args.kwargs["task_metadata"]["source"], "builtin_command")

    def test_invalid_print_verify_fails_before_provider_creation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-verify-") as base:
            create_client = Mock()
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", create_client),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--print", "/verify --fix"])

        self.assertNotEqual(exit_code, 0)
        create_client.assert_not_called()
        self.assertIn("Unknown /verify option", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
