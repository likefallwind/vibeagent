import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.agent import AgentResult
from vibeagent.cli import main
from vibeagent.cli_args import parse_args
from vibeagent.cli_pull_request_resume import prepare_pull_request_resume


class CliResumeContextTests(unittest.TestCase):
    def test_from_pr_resolves_to_resume_session_before_startup(self) -> None:
        args = parse_args(["--cwd", "/tmp", "--from-pr", "42"])
        with patch(
            "vibeagent.cli_pull_request_resume.resolve_session_from_pull_request",
            return_value="linked-run",
        ) as resolve:
            prepare_pull_request_resume(args)

        self.assertEqual(args.resume, "linked-run")
        resolve.assert_called_once_with(Path("/tmp").resolve(), "42")

    def test_from_pr_rejects_other_resume_selectors(self) -> None:
        args = parse_args(["--from-pr", "42", "--resume", "other-run"])
        with self.assertRaisesRegex(ValueError, "cannot be combined"):
            prepare_pull_request_resume(args)

    def test_main_status_command_reports_local_state_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/status",
                    "/chat",
                    "/approval allow",
                    "/resume run-1",
                    "/status",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_resume_context", return_value=("run-1", "context", "Resume context loaded from session run-1.")),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--allow-dangerously-skip-permissions"])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("mode: code", output)
        self.assertIn("approval: ask", output)
        self.assertIn("resume: none", output)
        self.assertIn("mode: chat", output)
        self.assertIn("approval: allow", output)
        self.assertIn("permissionMode: bypassPermissions", output)
        self.assertIn("resume: run-1", output)
        create_chat_client.assert_not_called()

    def test_main_passes_resume_context_to_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch(
                    "builtins.input",
                    side_effect=[
                        "/resume run-1 --max-failures 3 --max-files 4 --max-commands 5 --max-checks 2 --max-output-chars 0 --max-text 90",
                        "continue task",
                        "/exit",
                    ],
                ),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("run-1", "previous context", "Resume context loaded from session run-1."),
                        ("new-run", "new context", "Resume context loaded from session new-run."),
                    ],
                ) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            get_resume_context.call_args_list[0].kwargs,
            {
                "max_failures": 3,
                "max_files": 4,
                "max_commands": 5,
                "max_checks": 2,
                "max_output_chars": 0,
                "max_text": 90,
            },
        )
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "previous context")
        self.assertEqual(run_agent.call_args.kwargs["workspace"].run_id, "run-1")

    def test_main_starts_interactive_with_resume_context_from_cli_args(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("run-1", "startup context", "Resume context loaded from session run-1."),
                        ("new-run", "new context", "Resume context loaded from session new-run."),
                    ],
                ) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--resume", "run-1", "--resume-max-files", "4"])

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_any_call("run-1", Path(base).resolve(), max_files=4)
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "startup context")
        self.assertEqual(run_agent.call_args.kwargs["workspace"].run_id, "run-1")
        self.assertIn("Resume context loaded from session run-1.", stdout.getvalue())

    def test_main_continue_without_task_starts_interactive_with_latest_resume_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("latest-run", "latest context", "Resume context loaded from session latest-run."),
                        ("new-run", "new context", "Resume context loaded from session new-run."),
                    ],
                ) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "-c"])

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_any_call(None, Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "latest context")

    def test_main_startup_resume_missing_context_does_not_create_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_resume_context", return_value=(None, None, "Session not found: missing")),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--resume", "missing"])

        self.assertEqual(exit_code, 2)
        self.assertIn("Session not found: missing", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_starts_interactive_with_compact_context_from_cli_args(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_compact_context",
                    return_value=("run-1", "startup compact context", "Compacted context loaded from session run-1."),
                ) as get_compact_context,
                patch("vibeagent.cli.get_resume_context", return_value=("new-run", "new context", "Resume context loaded from session new-run.")),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--compact", "run-1", "--compact-max-checks", "2"])

        self.assertEqual(exit_code, 0)
        get_compact_context.assert_called_once_with("run-1", Path(base).resolve(), max_checks=2)
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "startup compact context")

    def test_main_starts_interactive_with_session_id_resume_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("run-1", "startup resume context", "Resume context loaded from session run-1."),
                        ("new-run", "new context", "Resume context loaded from session new-run."),
                    ],
                ) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--session-id", "run-1", "--resume-max-checks", "2"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(get_resume_context.call_args_list[0].args, ("run-1", Path(base).resolve()))
        self.assertEqual(get_resume_context.call_args_list[0].kwargs, {"max_checks": 2})
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "startup resume context")

    def test_main_starts_interactive_with_session_id_latest_resume_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("latest-run", "startup latest context", "Resume context loaded from session latest-run."),
                        ("new-run", "new context", "Resume context loaded from session new-run."),
                    ],
                ) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--session-id", "latest"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(get_resume_context.call_args_list[0].args, (None, Path(base).resolve()))
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "startup latest context")

    def test_main_resume_off_clears_context_before_next_agent_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["/resume run-1", "/resume off", "fresh task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("run-1", "previous context", "Resume context loaded from session run-1."),
                        (None, None, "Resume context cleared."),
                        ("new-run", "new context", "Resume context loaded from session new-run."),
                    ],
                ),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])
        self.assertIn("Resume context cleared.", stdout.getvalue())

    def test_main_clear_clears_context_before_next_agent_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["/resume run-1", "/clear", "fresh task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("run-1", "previous context", "Resume context loaded from session run-1."),
                        ("new-run", "new context", "Resume context loaded from session new-run."),
                    ],
                ),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])
        self.assertIn("Cleared chat history and resume context.", stdout.getvalue())

    def test_main_compact_passes_compacted_context_to_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch(
                    "builtins.input",
                    side_effect=[
                        "/compact run-1 --max-failures 3 --max-files 4 --max-commands 5 --max-checks 2 --max-output-chars 0 --max-text 90",
                        "continue task",
                        "/exit",
                    ],
                ),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_compact_context", return_value=("run-1", "compacted context", "Compacted context loaded from session run-1.")) as get_compact_context,
                patch("vibeagent.cli.get_resume_context", return_value=("new-run", "new context", "Resume context loaded from session new-run.")),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Compacted context loaded", output)
        get_compact_context.assert_called_once_with(
            "run-1",
            max_failures=3,
            max_files=4,
            max_commands=5,
            max_checks=2,
            max_output_chars=0,
            max_text=90,
        )
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "compacted context")


if __name__ == "__main__":
    unittest.main()
