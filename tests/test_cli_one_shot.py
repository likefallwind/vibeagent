import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent import MACHINE_OUTPUT_SCHEMA_VERSION, __version__
from vibeagent.agent import AgentResult
from vibeagent.cli import main
from vibeagent.cli_runner import run_one_shot
from vibeagent.types import ApprovalRequest, PlanItem, TaskStep
from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.session_branching import read_session_branch_info
from vibeagent.workspace_core import create_run_workspace


class CliOneShotTests(unittest.TestCase):
    def test_direct_runner_rejects_session_id_for_chat_before_client(self) -> None:
        create_chat_client = Mock()
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = run_one_shot(
                "hello",
                request_mode="chat",
                approval_policy="ask",
                session_id="123e4567-e89b-12d3-a456-426614174000",
                create_chat_client_func=create_chat_client,
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("--session-id requires a coding session.", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_runs_one_shot_code_task_from_args(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--approval",
                        "allow",
                        "--cwd",
                        base,
                        "--max-iterations",
                        "7",
                        "--command-timeout-ms",
                        "1234",
                        "--max-output-tokens",
                        "8192",
                        "--model-retries",
                        "2",
                        "--model-retry-delay-ms",
                        "25",
                        "--model-timeout-ms",
                        "45000",
                        "fix",
                        "the",
                        "test",
                    ]
                )

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("done", output)
        self.assertNotIn("VibeAgent v0.1", output)
        self.assertEqual(run_agent.call_args.args[0], "fix the test")
        self.assertEqual(run_agent.call_args.kwargs["base_dir"], Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["max_iterations"], 7)
        self.assertEqual(run_agent.call_args.kwargs["command_timeout_ms"], 1234)
        self.assertEqual(run_agent.call_args.kwargs["max_output_tokens"], 8192)
        self.assertEqual(run_agent.call_args.kwargs["model_retries"], 2)
        self.assertEqual(run_agent.call_args.kwargs["model_retry_delay_ms"], 25)
        self.assertEqual(run_agent.call_args.kwargs["model_timeout_ms"], 45000)
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])
        self.assertEqual(run_agent.call_args.kwargs["approval_policy"], "allow")
        handler = run_agent.call_args.kwargs["approval_handler"]
        self.assertTrue(handler(ApprovalRequest(action_type="write_file", target="note.txt", risk="write")).approved)

    def test_main_runs_one_shot_chat_task_from_args(self) -> None:
        stdout = io.StringIO()
        run_chat = Mock(return_value="你好")

        with (
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_chat", run_chat),
            patch("vibeagent.cli.run_agent") as run_agent,
            redirect_stdout(stdout),
        ):
            exit_code = main(
                [
                    "--chat",
                    "--max-output-tokens",
                    "8192",
                    "--model-retries",
                    "2",
                    "--model-retry-delay-ms",
                    "25",
                    "--model-timeout-ms",
                    "45000",
                    "随便聊聊",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "你好\n")
        run_chat.assert_called_once()
        self.assertEqual(run_chat.call_args.args[0], "随便聊聊")
        self.assertEqual(run_chat.call_args.kwargs["history"], [])
        self.assertEqual(run_chat.call_args.kwargs["max_output_tokens"], 8192)
        self.assertEqual(run_chat.call_args.kwargs["model_retries"], 2)
        self.assertEqual(run_chat.call_args.kwargs["model_retry_delay_ms"], 25)
        self.assertEqual(run_chat.call_args.kwargs["model_timeout_ms"], 45000)
        run_agent.assert_not_called()

    def test_main_runs_one_shot_chat_task_with_json_output(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_chat", return_value="你好"),
            patch("vibeagent.cli_runner.monotonic", side_effect=[20.0, 20.045]),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--chat", "随便聊聊"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload,
            {
                "durationMs": 45,
                "duration_ms": 45,
                "exitCode": 0,
                "exit_code": 0,
                "kind": "chat",
                "message": "你好",
                "numTurns": 1,
                "num_turns": 1,
                "result": "你好",
                "schemaVersion": MACHINE_OUTPUT_SCHEMA_VERSION,
                "success": True,
                "status": "completed",
                "stopReason": "completed",
                "stop_reason": "completed",
                "version": __version__,
            },
        )

    def test_main_passes_system_prompt_to_one_shot_chat(self) -> None:
        run_chat = Mock(return_value="好")

        with (
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_chat", run_chat),
            redirect_stdout(io.StringIO()),
        ):
            exit_code = main(["--chat", "--system-prompt", "You are terse.", "随便聊聊"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_chat.call_args.kwargs["system_prompt"], "You are terse.")
        self.assertIsNone(run_chat.call_args.kwargs["append_system_prompt"])

    def test_main_reports_prompt_file_errors_as_json_before_provider_creation(self) -> None:
        stdout = io.StringIO()
        create_client = Mock()

        with (
            patch("vibeagent.cli.create_chat_client", create_client),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--system-prompt-file", "missing-prompt.txt", "inspect"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["exitCode"], 2)
        self.assertIn("Cannot read --system-prompt-file", payload["error"])
        create_client.assert_not_called()

    def test_main_reports_dynamic_agent_errors_before_provider_creation(self) -> None:
        stdout = io.StringIO()
        create_client = Mock()

        with (
            patch("vibeagent.cli.create_chat_client", create_client),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--agents", '{"reviewer":{"prompt":"missing description"}}', "inspect"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertIn("Invalid --agents profile", payload["error"])
        create_client.assert_not_called()

    def test_main_rejects_dynamic_agents_in_one_shot_chat_mode(self) -> None:
        stdout = io.StringIO()
        create_client = Mock()

        with (
            patch("vibeagent.cli.create_chat_client", create_client),
            redirect_stdout(stdout),
        ):
            exit_code = main(
                [
                    "--chat",
                    "--agents",
                    '{"reviewer":{"description":"Review","prompt":"Inspect"}}',
                    "hello",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("coding sessions only", stdout.getvalue())
        create_client.assert_not_called()

    def test_main_reports_missing_additional_directory_before_provider_creation(self) -> None:
        stdout = io.StringIO()
        create_client = Mock()

        with (
            patch("vibeagent.cli.create_chat_client", create_client),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--add-dir", "missing-shared", "inspect"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertFalse(payload["success"])
        self.assertIn("Cannot resolve --add-dir", payload["error"])
        create_client.assert_not_called()

    def test_main_passes_additional_directory_to_one_shot_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            project = root / "project"
            shared = root / "shared"
            project.mkdir()
            shared.mkdir()
            result = AgentResult(
                success=True,
                message="done",
                run_dir=project,
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            previous_cwd = Path.cwd()
            os.chdir(root)
            try:
                with (
                    patch("vibeagent.cli.create_chat_client", return_value=object()),
                    patch("vibeagent.cli.run_agent", run_agent),
                    redirect_stdout(io.StringIO()),
                ):
                    exit_code = main(["--cwd", str(project), "--add-dir", "shared", "inspect"])
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["additional_directories"], (shared.resolve(),))

    def test_main_runs_one_shot_code_task_from_stdin(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("sys.stdin", io.StringIO("fix from stdin\n")),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["-"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.args[0], "fix from stdin")

    def test_main_runs_one_shot_code_task_from_stream_json_stdin(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            input_records = "\n".join(
                [
                    json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": "fix from"}]}}),
                    json.dumps({"type": "user", "text": "stream json"}),
                ]
            )

            with (
                patch("sys.stdin", io.StringIO(input_records)),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--input-format", "stream-json", "-"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.args[0], "fix from\nstream json")

    def test_main_stream_json_session_id_loads_resume_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            input_records = json.dumps(
                {
                    "session_id": "run-1",
                    "messages": [{"role": "user", "content": "continue task"}],
                }
            )

            with (
                patch("sys.stdin", io.StringIO(input_records)),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                patch(
                    "vibeagent.cli.get_resume_context",
                    return_value=("run-1", "previous context", "Resume context loaded from session run-1."),
                ) as get_resume_context,
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--input-format", "stream-json", "--cwd", base, "-"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.args[0], "continue task")
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "previous context")
        get_resume_context.assert_called_once_with("run-1", Path(base).resolve())

    def test_main_stream_json_session_id_does_not_override_explicit_resume(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            source = create_run_workspace(Path(base), "explicit-run")
            append_session_event(source.session_dir, "task", {"task": "Explicit resume"})
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            input_records = json.dumps({"session_id": "run-1", "type": "user", "text": "continue task"})

            with (
                patch("sys.stdin", io.StringIO(input_records)),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                patch(
                    "vibeagent.cli.get_resume_context",
                    return_value=("explicit-run", "explicit context", "Resume context loaded from session explicit-run."),
                ) as get_resume_context,
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--input-format", "stream-json", "--cwd", base, "--resume", "explicit-run", "-"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "explicit context")
        get_resume_context.assert_called_once_with("explicit-run", Path(base).resolve())

    def test_main_runs_one_shot_code_task_from_json_stdin(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            input_record = json.dumps(
                {
                    "session_id": "run-1",
                    "messages": [
                        {"role": "system", "content": "Prefer focused checks."},
                        {"role": "assistant", "content": "I saw tests/test_app.py."},
                        {"role": "user", "input": "continue task"},
                    ],
                }
            )

            with (
                patch("sys.stdin", io.StringIO(input_record)),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                patch(
                    "vibeagent.cli.get_resume_context",
                    return_value=("run-1", "previous context", "Resume context loaded from session run-1."),
                ) as get_resume_context,
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--input-format", "json", "--cwd", base, "-"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.args[0], "continue task")
        self.assertEqual(run_agent.call_args.kwargs["system_prompt"], "Prefer focused checks.")
        self.assertIn("previous context", run_agent.call_args.kwargs["prior_context"])
        self.assertIn("Structured input assistant messages:", run_agent.call_args.kwargs["prior_context"])
        self.assertIn("tests/test_app.py", run_agent.call_args.kwargs["prior_context"])
        get_resume_context.assert_called_once_with("run-1", Path(base).resolve())

    def test_main_runs_one_shot_code_task_from_responses_style_json_input(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            input_record = json.dumps(
                {
                    "input": [
                        {"role": "system", "content": "Prefer focused checks."},
                        {"role": "assistant", "content": [{"type": "output_text", "text": "I saw tests/test_app.py."}]},
                        {"role": "user", "content": [{"type": "input_text", "text": "continue task"}]},
                    ],
                }
            )

            with (
                patch("sys.stdin", io.StringIO(input_record)),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--input-format", "json", "--cwd", base, "-"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.args[0], "continue task")
        self.assertEqual(run_agent.call_args.kwargs["system_prompt"], "Prefer focused checks.")
        self.assertIn("Structured input assistant messages:", run_agent.call_args.kwargs["prior_context"])
        self.assertIn("tests/test_app.py", run_agent.call_args.kwargs["prior_context"])

    def test_main_stream_json_stdin_parse_error_does_not_call_agent(self) -> None:
        stdout = io.StringIO()

        with (
            patch("sys.stdin", io.StringIO("{not json}\n")),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--input-format", "stream-json", "-"])

        self.assertEqual(exit_code, 2)
        self.assertIn("Invalid stream-json input on line 1", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_stream_json_future_schema_version_does_not_call_agent(self) -> None:
        stdout = io.StringIO()
        raw = json.dumps(
            {
                "schemaVersion": MACHINE_OUTPUT_SCHEMA_VERSION + 1,
                "type": "user",
                "text": "continue task",
            }
        )

        with (
            patch("sys.stdin", io.StringIO(raw)),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--input-format", "stream-json", "-"])

        self.assertEqual(exit_code, 2)
        self.assertIn("Unsupported schemaVersion", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_json_stdin_parse_error_does_not_call_agent(self) -> None:
        stdout = io.StringIO()

        with (
            patch("sys.stdin", io.StringIO("{not json}\n")),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--input-format", "json", "-"])

        self.assertEqual(exit_code, 2)
        self.assertIn("Invalid json input", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_json_stdin_parse_error_reports_exit_code_in_json(self) -> None:
        stdout = io.StringIO()

        with (
            patch("sys.stdin", io.StringIO("{not json}\n")),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--input-format", "json", "-"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["exitCode"], 2)
        self.assertEqual(payload["exit_code"], 2)
        self.assertEqual(payload["status"], "failed")
        self.assertIn("Invalid json input", payload["error"])
        create_chat_client.assert_not_called()

    def test_main_rejects_input_format_stream_json_without_stdin_task(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["--input-format", "stream-json", "inspect"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            stdout.getvalue(),
            "--input-format stream-json requires task '-' so input can be read from stdin.\n",
        )

    def test_main_rejects_input_format_json_without_stdin_task(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["--input-format", "json", "inspect"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            stdout.getvalue(),
            "--input-format json requires task '-' so input can be read from stdin.\n",
        )

    def test_main_one_shot_empty_stdin_returns_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("sys.stdin", io.StringIO("\n")),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["-"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "No task provided.\n")
        create_chat_client.assert_not_called()

    def test_main_one_shot_empty_stdin_returns_json_error_status(self) -> None:
        stdout = io.StringIO()

        with (
            patch("sys.stdin", io.StringIO("\n")),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli_runner.monotonic", side_effect=[50.0, 50.067]),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "-"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["kind"], "error")
        self.assertEqual(payload["durationMs"], 67)
        self.assertEqual(payload["duration_ms"], 67)
        self.assertEqual(payload["exitCode"], 1)
        self.assertEqual(payload["exit_code"], 1)
        self.assertEqual(payload["version"], __version__)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["stopReason"], "failed")
        self.assertEqual(payload["stop_reason"], "failed")
        self.assertEqual(payload["error"], "No task provided.")
        create_chat_client.assert_not_called()

    def test_main_one_shot_code_task_exits_nonzero_when_completion_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
                completion_ready=False,
                completion_blockers=["Final review did not report ready."],
            )
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(stdout),
            ):
                exit_code = main(["fix", "the", "test"])

        self.assertEqual(exit_code, 1)
        self.assertIn("done", stdout.getvalue())
        self.assertIn("Completion blockers:", stdout.getvalue())
        self.assertIn("Final review did not report ready.", stdout.getvalue())

    def test_main_print_mode_outputs_only_final_code_message(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
                completion_ready=False,
                completion_blockers=["Final review did not report ready."],
                final_review_changed_files=["M app.py"],
            )
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(stdout),
            ):
                exit_code = main(["-p", "--cwd", base, "fix", "the", "test"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "done\n")

    def test_main_passes_appended_system_prompt_to_one_shot_code_task(self) -> None:
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
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--append-system-prompt", "Prefer focused tests.", "inspect"])

        self.assertEqual(exit_code, 0)
        self.assertIsNone(run_agent.call_args.kwargs["system_prompt"])
        self.assertEqual(run_agent.call_args.kwargs["append_system_prompt"], "Prefer focused tests.")

    def test_main_passes_dynamic_system_section_exclusion_to_code_agent(self) -> None:
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
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(
                    [
                        "-p",
                        "--cwd",
                        base,
                        "--exclude-dynamic-system-prompt-sections",
                        "inspect",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertTrue(
            run_agent.call_args.kwargs["exclude_dynamic_system_prompt_sections"]
        )

    def test_main_passes_mcp_config_paths_to_one_shot_code_task(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "extra.mcp.json").write_text('{"mcpServers": {}}', encoding="utf-8")
            result = AgentResult(
                success=True,
                message="done",
                run_dir=root,
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--mcp-config", "extra.mcp.json", "inspect"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["mcp_config_paths"], (root / "extra.mcp.json",))
        self.assertFalse(run_agent.call_args.kwargs["strict_mcp_config"])

    def test_main_passes_strict_mcp_config_to_one_shot_code_task(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "extra.mcp.json").write_text('{"mcpServers": {}}', encoding="utf-8")
            result = AgentResult(
                success=True,
                message="done",
                run_dir=root,
                run_id="new-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--mcp-config", "extra.mcp.json", "--strict-mcp-config", "inspect"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["mcp_config_paths"], (root / "extra.mcp.json",))
        self.assertTrue(run_agent.call_args.kwargs["strict_mcp_config"])

    def test_main_missing_mcp_config_path_does_not_create_client(self) -> None:
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--mcp-config", "missing.json", "inspect"])

        self.assertEqual(exit_code, 2)
        self.assertIn("--mcp-config file not found: missing.json.", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_one_shot_code_task_can_load_resume_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            source = create_run_workspace(Path(base), "run-1")
            append_session_event(source.session_dir, "task", {"task": "Continue task"})
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
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_resume_context", return_value=("run-1", "previous context", "Resume context loaded from session run-1.")) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--resume",
                        "run-1",
                        "--resume-max-failures",
                        "3",
                        "--resume-max-files",
                        "4",
                        "--resume-max-commands",
                        "5",
                        "--resume-max-checks",
                        "2",
                        "--resume-max-output-chars",
                        "0",
                        "--resume-max-text",
                        "90",
                        "continue",
                        "task",
                    ]
                )

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_called_once_with(
            "run-1",
            Path(base).resolve(),
            max_failures=3,
            max_files=4,
            max_commands=5,
            max_checks=2,
            max_output_chars=0,
            max_text=90,
        )
        self.assertEqual(run_agent.call_args.kwargs["base_dir"], Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "previous context")

    def test_main_one_shot_json_forks_resumed_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-branch-") as base:
            root = Path(base)
            source_dir = root / ".vibeagent" / "sessions" / "source-run"
            append_session_event(source_dir, "task", {"task": "source task"})
            source_events = source_dir.joinpath("events.jsonl").read_bytes()
            stdout = io.StringIO()

            def run_agent(task, **kwargs):
                workspace = kwargs["workspace"]
                return AgentResult(True, "done", root, workspace.run_id, 1, [], [])

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    return_value=("source-run", "source context", "Resume loaded."),
                ),
                patch("vibeagent.cli.run_agent", side_effect=run_agent) as run_agent_mock,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--resume",
                        "source-run",
                        "--fork-session",
                        "try alternative",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            branch_id = payload["sessionBranch"]["runId"]
            branch_info = read_session_branch_info(root, branch_id)

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["sessionBranch"]["sourceRunId"], "source-run")
            self.assertEqual(run_agent_mock.call_args.kwargs["task_source_run_id"], "source-run")
            self.assertEqual(branch_info.source_run_id, "source-run")  # type: ignore[union-attr]
            self.assertEqual(source_dir.joinpath("events.jsonl").read_bytes(), source_events)

    def test_main_one_shot_session_id_creates_exact_fresh_workspace(self) -> None:
        session_id = "123e4567-e89b-12d3-a456-426614174000"
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            def run_agent_impl(_task: str, **kwargs) -> AgentResult:
                workspace = kwargs["workspace"]
                self.assertEqual(workspace.run_id, session_id)
                self.assertEqual(workspace.session_dir, Path(base) / ".vibeagent" / "sessions" / session_id)
                return AgentResult(
                    success=True,
                    message="done",
                    run_dir=Path(base),
                    run_id=session_id,
                    iterations=1,
                    observations=[],
                    steps=[],
                )

            run_agent = Mock(side_effect=run_agent_impl)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_resume_context") as get_resume_context,
                patch("vibeagent.cli.get_compact_context") as get_compact_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--session-id", session_id, "continue", "task"])

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_not_called()
        get_compact_context.assert_not_called()
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])

    def test_main_one_shot_rejects_invalid_session_id_before_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-id", "latest", "continue", "task"])

        self.assertEqual(exit_code, 2)
        self.assertIn("--session-id must be a valid UUID.", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_one_shot_rejects_existing_session_id_before_client(self) -> None:
        session_id = "123e4567-e89b-12d3-a456-426614174000"
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            (Path(base) / ".vibeagent" / "sessions" / session_id).mkdir(parents=True)
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-id", session_id, "continue"])

        self.assertEqual(exit_code, 1)
        self.assertIn(f"Session already exists: {session_id}", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_rejects_resume_with_session_id(self) -> None:
        session_id = "123e4567-e89b-12d3-a456-426614174000"
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-id", session_id, "--resume", "explicit-run", "continue", "task"])

        self.assertEqual(exit_code, 2)
        self.assertIn("--session-id cannot be combined", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_one_shot_continue_loads_newest_context_without_picker(self) -> None:
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
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_resume_context",
                    return_value=("latest-run", "latest context", "Resume context loaded from session latest-run."),
                ) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--continue", "--", "continue", "task"])

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_called_once_with(None, Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "latest context")

    def test_main_one_shot_code_task_auto_loads_latest_compact_context(self) -> None:
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
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_compact_context",
                    return_value=("latest-run", "latest compact context", "Compacted context loaded from session latest-run."),
                ) as get_compact_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "continue", "task"])

        self.assertEqual(exit_code, 0)
        get_compact_context.assert_called_once_with(None, Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "latest compact context")

    def test_main_one_shot_no_auto_compact_runs_without_prior_context(self) -> None:
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
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_compact_context") as get_compact_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--no-auto-compact", "continue", "task"])

        self.assertEqual(exit_code, 0)
        get_compact_context.assert_not_called()
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])

    def test_main_one_shot_json_reports_auto_loaded_compact_context(self) -> None:
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
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch(
                    "vibeagent.cli.get_compact_context",
                    return_value=("latest-run", "latest compact context", "Compacted context loaded from session latest-run."),
                ),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "continue", "task"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "latest compact context")
        self.assertEqual(payload["priorContext"], {"loaded": True, "source": "auto_compact", "runId": "latest-run"})

    def test_main_one_shot_json_reports_no_auto_compact_context(self) -> None:
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
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_compact_context") as get_compact_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--no-auto-compact", "continue", "task"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        get_compact_context.assert_not_called()
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])
        self.assertEqual(payload["priorContext"], {"loaded": False, "source": "none", "runId": None})

    def test_main_one_shot_code_task_without_sessions_runs_without_prior_context(self) -> None:
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
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_compact_context", return_value=(None, None, "No sessions found.")) as get_compact_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "continue", "task"])

        self.assertEqual(exit_code, 0)
        get_compact_context.assert_called_once_with(None, Path(base).resolve())
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])
        self.assertNotIn("No sessions found.", stdout.getvalue())

    def test_main_one_shot_resume_without_cwd_uses_current_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            source = create_run_workspace(Path(base), "run-1")
            append_session_event(source.session_dir, "task", {"task": "Continue task"})
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
            previous_cwd = Path.cwd()

            try:
                os.chdir(base)
                with (
                    patch("vibeagent.cli.create_chat_client", return_value=object()),
                    patch(
                        "vibeagent.cli.get_resume_context",
                        return_value=("run-1", "previous context", "Resume context loaded from session run-1."),
                    ) as get_resume_context,
                    patch("vibeagent.cli.run_agent", run_agent),
                    redirect_stdout(io.StringIO()),
                ):
                    exit_code = main(["--resume", "run-1", "continue", "task"])
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_called_once_with("run-1", Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["base_dir"], Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "previous context")

    def test_main_one_shot_resume_off_runs_without_prior_context(self) -> None:
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
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_resume_context", return_value=(None, None, "Resume context cleared.")) as get_resume_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--resume", "off", "fresh", "task"])

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_called_once_with("off", Path(base).resolve())
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])

    def test_main_one_shot_code_task_reports_missing_resume_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_resume_context") as get_resume_context,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--resume", "missing", "continue"])

        self.assertEqual(exit_code, 2)
        self.assertIn("requires an interactive text terminal", stdout.getvalue())
        create_chat_client.assert_not_called()
        get_resume_context.assert_not_called()

    def test_main_one_shot_compact_passes_compacted_context_to_agent(self) -> None:
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
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_compact_context", return_value=("run-1", "compacted context", "Compacted context loaded from session run-1.")) as get_compact_context,
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--compact",
                        "run-1",
                        "--compact-max-failures",
                        "3",
                        "--compact-max-files",
                        "4",
                        "--compact-max-commands",
                        "5",
                        "--compact-max-checks",
                        "2",
                        "--compact-max-output-chars",
                        "0",
                        "--compact-max-text",
                        "90",
                        "--cwd",
                        base,
                        "continue",
                        "task",
                    ]
                )

        self.assertEqual(exit_code, 0)
        get_compact_context.assert_called_once_with(
            "run-1",
            Path(base).resolve(),
            max_failures=3,
            max_files=4,
            max_commands=5,
            max_checks=2,
            max_output_chars=0,
            max_text=90,
        )
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "compacted context")
        self.assertIn("done", stdout.getvalue())

    def test_main_one_shot_compact_reports_missing_context_without_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_compact_context", return_value=(None, None, "No sessions found.")),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--compact", "--cwd", base, "continue", "task"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue().strip(), "No sessions found.")
        create_chat_client.assert_not_called()

    def test_main_rejects_resume_and_compact_together(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["--resume", "run-1", "--compact", "run-2", "continue"])

        self.assertEqual(exit_code, 2)
        self.assertIn("--resume and --compact cannot be used together.", stdout.getvalue())

    def test_main_rejects_resume_compact_limit_without_matching_context_flag(self) -> None:
        cases = [
            (["--resume-max-checks", "2", "continue"], "--resume-max-checks can only be used with --resume."),
            (["--resume-max-files", "2", "continue"], "--resume-max-files can only be used with --resume."),
            (["--resume-max-output-chars", "0", "continue"], "--resume-max-output-chars can only be used with --resume."),
            (["--compact-max-checks", "2", "continue"], "--compact-max-checks can only be used with --compact."),
            (["--compact-max-files", "2", "continue"], "--compact-max-files can only be used with --compact."),
            (["--compact-max-output-chars", "0", "continue"], "--compact-max-output-chars can only be used with --compact."),
        ]

        for argv, message in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(argv)
                self.assertEqual(exit_code, 2)
                self.assertIn(message, stdout.getvalue())

    def test_main_one_shot_invalid_cwd_returns_error_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--cwd", "missing-dir", "continue"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Project directory not found: missing-dir", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_one_shot_error_with_json_output(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--cwd", "missing-dir", "continue"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["kind"], "error")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["error"], "Project directory not found: missing-dir")
        create_chat_client.assert_not_called()

    def test_main_print_mode_keeps_json_machine_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(stdout),
            ):
                exit_code = main(["-p", "--json", "--cwd", base, "fix", "the", "test"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "code")
        self.assertEqual(payload["exitCode"], 0)
        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(payload["message"], "done")
        self.assertEqual(payload["result"], "done")

    def test_main_runs_one_shot_code_task_with_json_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=2,
                observations=[],
                steps=[TaskStep(id=1, label="Read file", action_type="read_file", target="app.py", status="completed")],
                plan=[
                    PlanItem(step="Inspect failure", status="completed"),
                    PlanItem(step="Run verification", status="pending"),
                ],
                completion_ready=False,
                completion_blockers=["1 suggested verification check(s) are still pending after the latest project change."],
                completion_warnings=["Suggested verification checks are still pending after the latest project change."],
                verification_checks=["python -m unittest discover -s tests"],
                pending_verification_checks=["npm test"],
                failed_verification_checks=["npm test (exit=1)"],
                completion_blocked_count=1,
                latest_completion_blockers=["Final review did not report ready."],
                latest_completion_pending_verification_checks=["npm test"],
                latest_completion_failed_verification_checks=["npm run build (exit=1)"],
                latest_completion_final_review_issues=["Changed Python files have syntax errors."],
                latest_completion_final_review_changed_files=["M app.py"],
                latest_completion_tool_errors=["read_file: Tool execution failed: boom"],
                latest_completion_checkpoint_failures=["checkpoint_create: git diff failed."],
                latest_completion_active_background_processes=["bg-1: pid=123, cwd=web, command=npm run dev"],
                latest_completion_denied_approvals=["write_file note.txt: denied"],
                latest_completion_next_actions=["Use run_session_verification to run pending recorded checks."],
                final_review_changed_files=["M app.py"],
            )
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_compact_context", return_value=(None, None, "No sessions found.")),
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "fix", "the", "test"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["kind"], "code")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["stopReason"], "blocked")
        self.assertEqual(payload["stop_reason"], "blocked")
        self.assertEqual(payload["exitCode"], 1)
        self.assertEqual(payload["exit_code"], 1)
        self.assertEqual(payload["message"], "done")
        self.assertEqual(payload["result"], "done")
        self.assertEqual(payload["runId"], "one-shot")
        self.assertEqual(payload["sessionId"], "one-shot")
        self.assertEqual(payload["session_id"], "one-shot")
        self.assertEqual(payload["run_dir"], payload["runDir"])
        self.assertEqual(payload["iterations"], 2)
        self.assertEqual(payload["numTurns"], 2)
        self.assertEqual(payload["num_turns"], 2)
        self.assertEqual(payload["steps"], 1)
        self.assertEqual(payload["priorContext"], {"loaded": False, "source": "auto_compact", "runId": None})
        self.assertEqual(payload["prior_context"], payload["priorContext"])
        self.assertEqual(
            payload["plan"],
            [
                {"status": "completed", "step": "Inspect failure"},
                {"status": "pending", "step": "Run verification"},
            ],
        )
        self.assertFalse(payload["completionReady"])
        self.assertEqual(payload["completion_ready"], payload["completionReady"])
        self.assertEqual(payload["completionBlockers"], ["1 suggested verification check(s) are still pending after the latest project change."])
        self.assertEqual(payload["completion_blockers"], payload["completionBlockers"])
        self.assertEqual(payload["completionWarnings"], ["Suggested verification checks are still pending after the latest project change."])
        self.assertEqual(payload["completion_warnings"], payload["completionWarnings"])
        self.assertEqual(payload["completionBlockedCount"], 1)
        self.assertEqual(payload["completion_blocked_count"], payload["completionBlockedCount"])
        self.assertEqual(payload["latestCompletionBlockers"], ["Final review did not report ready."])
        self.assertEqual(payload["latest_completion_blockers"], payload["latestCompletionBlockers"])
        self.assertEqual(payload["latestCompletionPendingChecks"], ["npm test"])
        self.assertEqual(payload["latest_completion_pending_checks"], payload["latestCompletionPendingChecks"])
        self.assertEqual(payload["latestCompletionFailedChecks"], ["npm run build (exit=1)"])
        self.assertEqual(payload["latest_completion_failed_checks"], payload["latestCompletionFailedChecks"])
        self.assertEqual(payload["latestCompletionFinalReviewIssues"], ["Changed Python files have syntax errors."])
        self.assertEqual(payload["latest_completion_final_review_issues"], payload["latestCompletionFinalReviewIssues"])
        self.assertEqual(payload["latestCompletionFinalReviewChangedFiles"], ["M app.py"])
        self.assertEqual(payload["latest_completion_final_review_changed_files"], payload["latestCompletionFinalReviewChangedFiles"])
        self.assertEqual(payload["latestCompletionToolErrors"], ["read_file: Tool execution failed: boom"])
        self.assertEqual(payload["latest_completion_tool_errors"], payload["latestCompletionToolErrors"])
        self.assertEqual(payload["latestCompletionCheckpointFailures"], ["checkpoint_create: git diff failed."])
        self.assertEqual(payload["latest_completion_checkpoint_failures"], payload["latestCompletionCheckpointFailures"])
        self.assertEqual(payload["latestCompletionActiveProcesses"], ["bg-1: pid=123, cwd=web, command=npm run dev"])
        self.assertEqual(payload["latest_completion_active_processes"], payload["latestCompletionActiveProcesses"])
        self.assertEqual(payload["latestCompletionDeniedApprovals"], ["write_file note.txt: denied"])
        self.assertEqual(payload["latest_completion_denied_approvals"], payload["latestCompletionDeniedApprovals"])
        self.assertEqual(payload["latestCompletionNextActions"], ["Use run_session_verification to run pending recorded checks."])
        self.assertEqual(payload["latest_completion_next_actions"], payload["latestCompletionNextActions"])
        self.assertEqual(payload["changedFiles"], ["M app.py"])
        self.assertEqual(payload["changed_files"], payload["changedFiles"])
        self.assertEqual(payload["verificationChecks"], ["python -m unittest discover -s tests"])
        self.assertEqual(payload["verification_checks"], payload["verificationChecks"])
        self.assertEqual(payload["pendingVerificationChecks"], ["npm test"])
        self.assertEqual(payload["pending_verification_checks"], payload["pendingVerificationChecks"])
        self.assertEqual(payload["failedVerificationChecks"], ["npm test (exit=1)"])
        self.assertEqual(payload["failed_verification_checks"], payload["failedVerificationChecks"])

    def test_main_resumes_from_structured_input_run_id_alias(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdin_payload = json.dumps(
                {
                    "runId": "previous-run",
                    "input": [{"role": "user", "content": "continue the fix"}],
                }
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)
            get_resume_context = Mock(return_value=("previous-run", "Previous session context.", "Resume loaded."))

            with (
                patch("sys.stdin", io.StringIO(stdin_payload)),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_resume_context", get_resume_context),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--input-format", "json", "--cwd", base, "-"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["priorContext"], {"loaded": True, "source": "resume", "runId": "previous-run"})
        get_resume_context.assert_called_once()
        self.assertEqual(get_resume_context.call_args.args[:2], ("previous-run", Path(base).resolve()))
        self.assertEqual(run_agent.call_args.args[0], "continue the fix")
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "Previous session context.")

    def test_main_one_shot_code_task_handles_keyboard_interrupt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=KeyboardInterrupt),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "fix", "the", "test"])

        self.assertEqual(exit_code, 130)
        self.assertEqual(stdout.getvalue().strip(), "Interrupted.")

    def test_main_one_shot_code_task_handles_keyboard_interrupt_with_json_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=KeyboardInterrupt),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "fix", "the", "test"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 130)
        self.assertEqual(payload["kind"], "interrupted")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "interrupted")
        self.assertEqual(payload["error"], "Interrupted.")

    def test_main_local_flag_handles_keyboard_interrupt(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.get_review_report", side_effect=KeyboardInterrupt),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--review"])

        self.assertEqual(exit_code, 130)
        self.assertEqual(stdout.getvalue().strip(), "Interrupted.")

    def test_main_one_shot_code_task_uses_provider_overrides(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()) as create_chat_client,
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--provider",
                        "minimax",
                        "--model",
                        "MiniMax-custom",
                        "--base-url",
                        "https://minimax.example",
                        "--api-key",
                        "secret-key",
                        "fix",
                    ]
                )

        provider_env = create_chat_client.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertIn("done", stdout.getvalue())
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "minimax")
        self.assertEqual(provider_env["MINIMAX_MODEL"], "MiniMax-custom")
        self.assertEqual(provider_env["MINIMAX_BASE_URL"], "https://minimax.example")
        self.assertEqual(provider_env["MINIMAX_API_KEY"], "secret-key")

    def test_main_one_shot_code_task_uses_project_provider_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps(
                    {
                        "provider": "deepseek",
                        "model": "deepseek-reasoner",
                        "base_url": "https://deepseek.example",
                    }
                ),
                encoding="utf-8",
            )
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.create_chat_client", return_value=object()) as create_chat_client,
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "fix"])

        provider_env = create_chat_client.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["VIBEAGENT_MODEL"], "deepseek-reasoner")
        self.assertEqual(provider_env["VIBEAGENT_BASE_URL"], "https://deepseek.example")

    def test_main_one_shot_code_task_uses_current_project_provider_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps({"provider": "deepseek", "model": "deepseek-reasoner"}),
                encoding="utf-8",
            )
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.Path.cwd", return_value=Path(base).resolve()),
                patch("vibeagent.cli.create_chat_client", return_value=object()) as create_chat_client,
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["fix"])

        provider_env = create_chat_client.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["VIBEAGENT_MODEL"], "deepseek-reasoner")

    def test_main_one_shot_code_task_uses_project_execution_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps(
                    {
                        "max_iterations": 9,
                        "command_timeout_ms": 45000,
                        "max_output_tokens": 8192,
                        "model_retries": 0,
                        "model_retry_delay_ms": 0,
                        "model_timeout_ms": 45000,
                    }
                ),
                encoding="utf-8",
            )
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "fix"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["max_iterations"], 9)
        self.assertEqual(run_agent.call_args.kwargs["command_timeout_ms"], 45000)
        self.assertEqual(run_agent.call_args.kwargs["max_output_tokens"], 8192)
        self.assertEqual(run_agent.call_args.kwargs["model_retries"], 0)
        self.assertEqual(run_agent.call_args.kwargs["model_retry_delay_ms"], 0)
        self.assertEqual(run_agent.call_args.kwargs["model_timeout_ms"], 45000)

    def test_main_one_shot_code_task_cli_execution_flags_win_over_project_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps(
                    {
                        "max_iterations": 9,
                        "command_timeout_ms": 45000,
                        "max_output_tokens": 8192,
                        "model_retries": 0,
                        "model_retry_delay_ms": 0,
                        "model_timeout_ms": 45000,
                    }
                ),
                encoding="utf-8",
            )
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--max-iterations",
                        "4",
                        "--command-timeout-ms",
                        "1000",
                        "--max-output-tokens",
                        "2048",
                        "--model-retries",
                        "3",
                        "--model-retry-delay-ms",
                        "50",
                        "--model-timeout-ms",
                        "60000",
                        "fix",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["max_iterations"], 4)
        self.assertEqual(run_agent.call_args.kwargs["command_timeout_ms"], 1000)
        self.assertEqual(run_agent.call_args.kwargs["max_output_tokens"], 2048)
        self.assertEqual(run_agent.call_args.kwargs["model_retries"], 3)
        self.assertEqual(run_agent.call_args.kwargs["model_retry_delay_ms"], 50)
        self.assertEqual(run_agent.call_args.kwargs["model_timeout_ms"], 60000)

    def test_main_cli_provider_override_wins_over_project_provider_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps({"provider": "deepseek", "model": "deepseek-reasoner"}),
                encoding="utf-8",
            )
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.create_chat_client", return_value=object()) as create_chat_client,
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--provider", "minimax", "--model-name", "MiniMax-custom", "fix"])

        provider_env = create_chat_client.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "minimax")
        self.assertEqual(provider_env["MINIMAX_MODEL"], "MiniMax-custom")
        self.assertEqual(provider_env["VIBEAGENT_MODEL"], "deepseek-reasoner")

    def test_main_model_alias_sets_one_shot_provider_model(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="one-shot",
                iterations=1,
                observations=[],
                steps=[],
            )

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.create_chat_client", return_value=object()) as create_chat_client,
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--provider", "minimax", "--model", "MiniMax-custom", "fix"])

        provider_env = create_chat_client.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "minimax")
        self.assertEqual(provider_env["MINIMAX_MODEL"], "MiniMax-custom")
