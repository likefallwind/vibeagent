from __future__ import annotations

from contextlib import redirect_stdout
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.agent import AgentResult
from vibeagent.builtin_model_workflows import (
    build_batch_workflow,
    build_code_review_workflow,
    build_security_review_workflow,
    build_simplify_workflow,
    parse_batch_instruction,
    parse_code_review_arguments,
    parse_security_review_arguments,
    parse_simplify_arguments,
)
from vibeagent.cli_project_command_expansion import expand_one_shot_project_command
from vibeagent.cli import main


class BuiltinModelWorkflowTests(unittest.TestCase):
    def test_builds_read_only_default_code_review(self) -> None:
        workflow = build_code_review_workflow(None)

        self.assertIn("call deep_review exactly once", workflow.task)
        self.assertIn('"max_iterations": 4', workflow.task)
        self.assertIn("read-only review", workflow.task)
        self.assertNotIn("After the review, inspect every verified finding", workflow.task)
        self.assertEqual(workflow.metadata["name"], "code-review")
        self.assertFalse(workflow.metadata["fix"])

    def test_builds_fix_workflow_with_effort_and_target(self) -> None:
        workflow = build_code_review_workflow('xhigh --fix "src/auth flow.py"')

        self.assertIn('"max_iterations": 6', workflow.task)
        self.assertIn('"target": "src/auth flow.py"', workflow.task)
        self.assertIn("fix justified issues", workflow.task)
        self.assertEqual(workflow.metadata["effort"], "xhigh")
        self.assertEqual(workflow.metadata["target"], "src/auth flow.py")
        self.assertTrue(workflow.metadata["fix"])

    def test_parses_end_of_options_target(self) -> None:
        self.assertEqual(
            parse_code_review_arguments("medium --fix -- --generated"),
            (True, "medium", "--generated"),
        )

    def test_rejects_unsupported_or_invalid_options(self) -> None:
        for argument, message in (
            ("--comment", "not supported"),
            ("ultra", "cloud review"),
            ("--fix --fix", "at most once"),
            ("--unknown", "Unknown"),
            ("'unterminated", "invalid"),
        ):
            with self.subTest(argument=argument), self.assertRaisesRegex(ValueError, message):
                parse_code_review_arguments(argument)

    def test_one_shot_code_review_expands_before_provider_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-code-review-") as base:
            task, metadata = expand_one_shot_project_command(
                Path(base),
                "/code-review high main...feature",
            )

        self.assertIn("call deep_review exactly once", task)
        self.assertIn('"target": "main...feature"', task)
        self.assertEqual(metadata["source"], "builtin_command")
        self.assertEqual(metadata["name"], "code-review")

    def test_builds_simplify_with_all_cleanup_perspectives(self) -> None:
        workflow = build_simplify_workflow('"src/auth flow.py"')

        self.assertIn('"review_kind": "cleanup"', workflow.task)
        for perspective in ("reuse", "simplicity", "efficiency", "abstraction"):
            self.assertIn(f'"{perspective}"', workflow.task)
        self.assertIn('"target": "src/auth flow.py"', workflow.task)
        self.assertIn("behavior-preserving", workflow.task)
        self.assertIn("focused verification and final_review", workflow.task)
        self.assertEqual(workflow.metadata["name"], "simplify")

    def test_simplify_argument_parser_is_bounded_and_fail_closed(self) -> None:
        self.assertEqual(parse_simplify_arguments("-- --generated"), "--generated")
        for argument, message in (
            ("--fix", "Unknown"),
            ("'unterminated", "invalid"),
            ("x" * 1001, "1000"),
        ):
            with self.subTest(argument=argument), self.assertRaisesRegex(ValueError, message):
                parse_simplify_arguments(argument)

    def test_one_shot_simplify_expands_before_provider_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-simplify-") as base:
            task, metadata = expand_one_shot_project_command(Path(base), "/simplify src")

        self.assertIn('"review_kind": "cleanup"', task)
        self.assertIn('"target": "src"', task)
        self.assertEqual(metadata["source"], "builtin_command")
        self.assertEqual(metadata["name"], "simplify")

    def test_builds_interactive_batch_orchestration_contract(self) -> None:
        workflow = build_batch_workflow('migrate "src"\nto async IO')

        self.assertIn('User batch instruction: "migrate \\"src\\"\\nto async IO"', workflow.task)
        self.assertIn("5 to 30 genuinely independent", workflow.task)
        self.assertIn("exact non-overlapping owned paths", workflow.task)
        self.assertIn("Approve and launch, Revise plan, and Cancel", workflow.task)
        self.assertIn("Do not edit files", workflow.task)
        self.assertIn("does not change the active approval policy", workflow.task)
        self.assertIn("mode=code and isolation=worktree", workflow.task)
        self.assertIn("Start all units before waiting", workflow.task)
        self.assertIn("check_github_pr_create then github_pr_create", workflow.task)
        self.assertIn("Use tool_search first", workflow.task)
        self.assertIn("Collect every agent with TaskOutput", workflow.task)
        self.assertEqual(workflow.metadata["name"], "batch")
        self.assertTrue(workflow.metadata["interactive_only"])

    def test_batch_instruction_is_required_and_bounded(self) -> None:
        self.assertEqual(parse_batch_instruction("  migrate src  "), "migrate src")
        for argument, message in (
            (None, "requires"),
            ("   ", "requires"),
            ("x" * 4001, "4000"),
            ("bad\x00task", "NUL"),
        ):
            with self.subTest(argument=argument), self.assertRaisesRegex(ValueError, message):
                parse_batch_instruction(argument)

    def test_one_shot_batch_is_rejected_before_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-batch-") as base:
            with self.assertRaisesRegex(ValueError, "interactive session"):
                expand_one_shot_project_command(Path(base), "/batch migrate src")

    def test_builds_read_only_security_review_with_all_domains(self) -> None:
        workflow = build_security_review_workflow(None)

        self.assertIn("git_show on origin/HEAD", workflow.task)
        self.assertIn('"review_kind": "security"', workflow.task)
        for perspective in ("access_control", "injection", "data_exposure", "supply_chain"):
            self.assertIn(f'"{perspective}"', workflow.task)
        self.assertIn('"base_ref": "origin/HEAD"', workflow.task)
        self.assertIn("strictly read-only", workflow.task)
        self.assertIn("attacker capability, exploit path", workflow.task)
        self.assertEqual(workflow.metadata["name"], "security-review")

    def test_security_review_rejects_arguments(self) -> None:
        self.assertIsNone(parse_security_review_arguments(None))
        with self.assertRaisesRegex(ValueError, "does not accept"):
            parse_security_review_arguments("main")

    def test_one_shot_security_review_expands_before_provider_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-security-review-") as base:
            task, metadata = expand_one_shot_project_command(Path(base), "/security-review")

        self.assertIn('"review_kind": "security"', task)
        self.assertIn('"base_ref": "origin/HEAD"', task)
        self.assertEqual(metadata["source"], "builtin_command")
        self.assertEqual(metadata["name"], "security-review")

    def test_non_workflow_builtin_remains_unexpanded(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-code-review-") as base:
            task, metadata = expand_one_shot_project_command(Path(base), "/help")

        self.assertEqual(task, "/help")
        self.assertIsNone(metadata)

    def test_interactive_code_review_runs_as_code_workflow_with_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-code-review-") as base:
            root = Path(base)
            result = AgentResult(True, "review done", root, "review-run", 1, [], [])
            run_agent = Mock(return_value=result)
            with (
                patch("builtins.input", side_effect=["/code-review medium --fix src", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertIn("call deep_review exactly once", run_agent.call_args.args[0])
        self.assertIn('"max_iterations": 3', run_agent.call_args.args[0])
        self.assertEqual(run_agent.call_args.kwargs["task_metadata"]["name"], "code-review")
        self.assertTrue(run_agent.call_args.kwargs["task_metadata"]["fix"])

    def test_print_mode_code_review_expands_before_agent_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-code-review-") as base:
            root = Path(base)
            result = AgentResult(True, "review done", root, "review-run", 1, [], [])
            run_agent = Mock(return_value=result)
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(root), "--print", "/code-review high main"])

        self.assertEqual(exit_code, 0)
        self.assertIn('"target": "main"', run_agent.call_args.args[0])
        self.assertEqual(run_agent.call_args.kwargs["task_metadata"]["source"], "builtin_command")

    def test_interactive_simplify_runs_as_code_workflow_with_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-simplify-") as base:
            root = Path(base)
            result = AgentResult(True, "simplified", root, "simplify-run", 1, [], [])
            run_agent = Mock(return_value=result)
            with (
                patch("builtins.input", side_effect=["/simplify vibeagent/cli.py", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertIn('"review_kind": "cleanup"', run_agent.call_args.args[0])
        self.assertEqual(run_agent.call_args.kwargs["task_metadata"]["name"], "simplify")

    def test_interactive_batch_runs_as_code_workflow_with_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-batch-") as base:
            root = Path(base)
            result = AgentResult(True, "batch launched", root, "batch-run", 1, [], [])
            run_agent = Mock(return_value=result)
            with (
                patch("builtins.input", side_effect=["/batch migrate src to async IO", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertIn("5 to 30 genuinely independent", run_agent.call_args.args[0])
        self.assertEqual(run_agent.call_args.kwargs["task_metadata"]["name"], "batch")

    def test_interactive_batch_requires_instruction_before_agent_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-batch-") as base:
            run_agent = Mock()
            stdout = io.StringIO()
            with (
                patch("builtins.input", side_effect=["/batch", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base])

        self.assertEqual(exit_code, 0)
        run_agent.assert_not_called()
        self.assertIn("requires an implementation instruction", stdout.getvalue())

    def test_print_mode_batch_fails_before_provider_creation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-batch-") as base:
            create_client = Mock()
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", create_client),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--print", "/batch migrate src"])

        self.assertNotEqual(exit_code, 0)
        create_client.assert_not_called()
        self.assertIn("interactive session", stdout.getvalue())

    def test_interactive_security_review_runs_read_only_workflow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-security-review-") as base:
            root = Path(base)
            result = AgentResult(True, "security review done", root, "security-run", 1, [], [])
            run_agent = Mock(return_value=result)
            with (
                patch("builtins.input", side_effect=["/security-review", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertIn('"review_kind": "security"', run_agent.call_args.args[0])
        self.assertIn("strictly read-only", run_agent.call_args.args[0])
        self.assertEqual(run_agent.call_args.kwargs["task_metadata"]["name"], "security-review")

    def test_invalid_print_security_review_fails_before_provider_creation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-security-review-") as base:
            create_client = Mock()
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", create_client),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--print", "/security-review main"])

        self.assertNotEqual(exit_code, 0)
        create_client.assert_not_called()
        self.assertIn("does not accept", stdout.getvalue())

    def test_invalid_print_mode_simplify_fails_before_provider_creation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-simplify-") as base:
            create_client = Mock()
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", create_client),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--print", "/simplify --fix"])

        self.assertNotEqual(exit_code, 0)
        create_client.assert_not_called()
        self.assertIn("Unknown", stdout.getvalue())

    def test_unsupported_print_mode_option_fails_before_provider_creation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-code-review-") as base:
            create_client = Mock()
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", create_client),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--print", "/code-review --comment"])

        self.assertNotEqual(exit_code, 0)
        create_client.assert_not_called()
        self.assertIn("not supported", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
