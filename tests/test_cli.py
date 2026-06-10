import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.agent import AgentResult
from vibeagent.cli import build_approval_handler, format_error, handle_approval_command, main, prompt_approval
from vibeagent.types import ApprovalRequest, TaskStep


class Http401Error(Exception):
    status = 401


class CliTests(unittest.TestCase):
    def test_format_error_uses_provider_neutral_401_guidance(self) -> None:
        text = format_error(Http401Error("unauthorized"))

        self.assertIn("unauthorized", text)
        self.assertIn("configured model provider rejected the API key", text)
        self.assertIn("Check /model", text)
        self.assertNotIn("MiniMax rejected", text)
        self.assertNotIn("DEEPSEEK_API_KEY", text)

    def test_format_error_returns_plain_error_for_other_errors(self) -> None:
        self.assertEqual(format_error(ValueError("bad")), "bad")

    def test_prompt_approval_accepts_y_and_yes(self) -> None:
        request = ApprovalRequest(
            action_type="write_file",
            target="note.txt",
            risk="This will create or replace a file in the active project.",
        )

        for answer in ("y", "yes"):
            with self.subTest(answer=answer):
                with patch("builtins.input", return_value=answer), patch("sys.stdout", new_callable=io.StringIO):
                    decision = prompt_approval(request)

                self.assertTrue(decision.approved)

    def test_prompt_approval_denies_other_input(self) -> None:
        request = ApprovalRequest(
            action_type="run_command",
            target="npm test",
            risk="This will run a shell command from the active project directory.",
        )

        with patch("builtins.input", return_value="n"), patch("sys.stdout", new_callable=io.StringIO):
            decision = prompt_approval(request)

        self.assertFalse(decision.approved)

    def test_prompt_approval_prints_target_and_risk_without_file_content(self) -> None:
        request = ApprovalRequest(
            action_type="write_file",
            target="report.md",
            risk="This will create or replace a file in the active project.",
        )
        large_file_content = "secret\n" * 500

        with patch("builtins.input", return_value="n"), patch("sys.stdout", new_callable=io.StringIO) as stdout:
            prompt_approval(request)

        output = stdout.getvalue()
        self.assertIn("write_file", output)
        self.assertIn("report.md", output)
        self.assertIn("create or replace", output)
        self.assertNotIn(large_file_content, output)

    def test_handle_approval_command_shows_and_updates_policy(self) -> None:
        self.assertEqual(handle_approval_command(None, "ask"), ("ask", "Approval policy: ask"))
        self.assertEqual(handle_approval_command("allow", "ask"), ("allow", "Approval policy: allow"))
        self.assertEqual(handle_approval_command("deny", "allow"), ("deny", "Approval policy: deny"))
        self.assertEqual(handle_approval_command("bad", "deny"), ("deny", "Usage: /approval [ask|allow|deny]"))

    def test_build_approval_handler_uses_policy_without_prompting(self) -> None:
        request = ApprovalRequest(
            action_type="run_command",
            target="python -m unittest",
            risk="This will run a shell command.",
        )

        self.assertTrue(build_approval_handler("allow")(request).approved)
        denied = build_approval_handler("deny")(request)
        self.assertFalse(denied.approved)
        self.assertIn("Denied by policy", denied.message)

    def test_main_prints_only_final_agent_message_for_code_tasks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="这是最终回复。",
                run_dir=Path(base),
                run_id="test-run",
                iterations=3,
                observations=[],
                steps=[
                    TaskStep(
                        id=1,
                        label="List files .",
                        action_type="list_files",
                        target=".",
                        status="completed",
                        message="Found 0 file(s).",
                    )
                ],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["现在用的什么 模型", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("这是最终回复。", output)
        self.assertNotIn("[thinking]", output)
        self.assertNotIn("Success", output)
        self.assertNotIn("Project directory:", output)
        self.assertNotIn("Iterations:", output)
        self.assertNotIn("Steps:", output)
        self.assertNotIn("List files .", output)
        self.assertNotIn("logger", run_agent.call_args.kwargs)

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
        self.assertIsNone(run_agent.call_args.kwargs["prior_context"])
        handler = run_agent.call_args.kwargs["approval_handler"]
        self.assertTrue(handler(ApprovalRequest(action_type="write_file", target="note.txt", risk="write")).approved)

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
            )
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "fix", "the", "test"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "code")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["message"], "done")
        self.assertEqual(payload["runId"], "one-shot")
        self.assertEqual(payload["iterations"], 2)
        self.assertEqual(payload["steps"], 1)

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
                        "--model-name",
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
                json.dumps({"max_iterations": 9, "command_timeout_ms": 45000}),
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

    def test_main_one_shot_code_task_cli_execution_flags_win_over_project_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps({"max_iterations": 9, "command_timeout_ms": 45000}),
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
                exit_code = main(["--cwd", base, "--max-iterations", "4", "--command-timeout-ms", "1000", "fix"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["max_iterations"], 4)
        self.assertEqual(run_agent.call_args.kwargs["command_timeout_ms"], 1000)

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

    def test_main_runs_local_flags_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_doctor_text", return_value="Doctor:\n  provider: minimax") as get_doctor_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--doctor"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Doctor:", stdout.getvalue())
        self.assertEqual(get_doctor_text.call_args.args[0], Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_local_flag_with_json_output(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_model_text", return_value="Model provider: minimax"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--model"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload, {"kind": "local", "success": True, "text": "Model provider: minimax"})
        create_chat_client.assert_not_called()

    def test_main_local_model_flag_uses_provider_overrides(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_model_text", return_value="Model provider: deepseek") as get_model_text,
            redirect_stdout(stdout),
        ):
            exit_code = main(
                [
                    "--model",
                    "--provider",
                    "deepseek",
                    "--model-name",
                    "deepseek-reasoner",
                    "--base-url",
                    "https://deepseek.example",
                    "--api-key",
                    "secret-key",
                ]
            )

        provider_env = get_model_text.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertIn("Model provider: deepseek", stdout.getvalue())
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["OPENAI_COMPAT_MODEL"], "deepseek-reasoner")
        self.assertEqual(provider_env["OPENAI_COMPAT_BASE_URL"], "https://deepseek.example")
        self.assertEqual(provider_env["OPENAI_COMPAT_API_KEY"], "secret-key")
        create_chat_client.assert_not_called()

    def test_main_local_model_flag_uses_project_provider_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps({"provider": "deepseek", "model": "deepseek-reasoner"}),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with (
                patch.dict("vibeagent.cli.os.environ", {}, clear=True),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_model_text", return_value="Model provider: deepseek") as get_model_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--model"])

        provider_env = get_model_text.call_args.args[0]
        self.assertEqual(exit_code, 0)
        self.assertIn("Model provider: deepseek", stdout.getvalue())
        self.assertEqual(provider_env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(provider_env["VIBEAGENT_MODEL"], "deepseek-reasoner")
        create_chat_client.assert_not_called()

    def test_main_save_config_writes_non_secret_project_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--save-config",
                        "--provider",
                        "deepseek",
                        "--model-name",
                        "deepseek-reasoner",
                        "--base-url",
                        "https://deepseek.example",
                        "--max-iterations",
                        "15",
                        "--command-timeout-ms",
                        "60000",
                    ]
                )
            data = json.loads((Path(base) / ".vibeagent" / "config.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "Saved .vibeagent/config.json.\n")
        self.assertEqual(data["provider"], "deepseek")
        self.assertEqual(data["model"], "deepseek-reasoner")
        self.assertEqual(data["base_url"], "https://deepseek.example")
        self.assertEqual(data["max_iterations"], 15)
        self.assertEqual(data["command_timeout_ms"], 60000)
        self.assertNotIn("api_key", data)
        create_chat_client.assert_not_called()

    def test_main_save_config_rejects_api_key_without_writing_secret(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--save-config", "--provider", "deepseek", "--api-key", "secret-key"])
            config_path = Path(base) / ".vibeagent" / "config.json"

        self.assertEqual(exit_code, 1)
        self.assertIn("--save-config does not write API keys", stdout.getvalue())
        self.assertFalse(config_path.exists())
        create_chat_client.assert_not_called()

    def test_main_save_config_with_json_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--save-config", "--provider", "minimax"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload, {"kind": "local", "success": True, "text": "Saved .vibeagent/config.json."})
        create_chat_client.assert_not_called()

    def test_main_local_session_flag_uses_requested_run_id_and_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_text", return_value="Session: run-1") as get_session_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session", "run-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session: run-1", stdout.getvalue())
        get_session_text.assert_called_once_with("run-1", Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_local_status_flag_uses_approval_setting(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--approval", "deny", "--status"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Status:", stdout.getvalue())
        self.assertIn("approval: deny", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_main_local_flag_rejects_task_text(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--doctor", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "Local command flags cannot be combined with a task.\n")
        create_chat_client.assert_not_called()

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

    def test_main_runs_one_shot_chat_task_from_args(self) -> None:
        stdout = io.StringIO()
        run_chat = Mock(return_value="你好")

        with (
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_chat", run_chat),
            patch("vibeagent.cli.run_agent") as run_agent,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--chat", "随便聊聊"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "你好\n")
        run_chat.assert_called_once()
        self.assertEqual(run_chat.call_args.args[0], "随便聊聊")
        self.assertEqual(run_chat.call_args.kwargs["history"], [])
        run_agent.assert_not_called()

    def test_main_runs_one_shot_chat_task_with_json_output(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_chat", return_value="你好"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--json", "--chat", "随便聊聊"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload, {"kind": "chat", "message": "你好", "success": True})

    def test_main_one_shot_code_task_can_load_resume_context(self) -> None:
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
                patch("vibeagent.cli.get_resume_context", return_value=("run-1", "previous context", "Resume context loaded from session run-1.")),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", base, "--resume", "run-1", "continue", "task"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["base_dir"], Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "previous context")

    def test_main_one_shot_resume_without_run_id_loads_newest_context(self) -> None:
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
                exit_code = main(["--cwd", base, "--resume", "--", "continue", "task"])

        self.assertEqual(exit_code, 0)
        get_resume_context.assert_called_once_with(None, Path(base).resolve())
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "latest context")

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
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"], "Project directory not found: missing-dir")
        create_chat_client.assert_not_called()

    def test_main_one_shot_code_task_reports_missing_resume_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_resume_context", return_value=(None, None, "Session not found: missing")),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--resume", "missing", "continue"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "Session not found: missing\n")
        create_chat_client.assert_not_called()

    def test_main_handles_session_commands_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
                patch("builtins.input", side_effect=["/sessions", "/usage", "/cost", "/doctor", "/session run-1", "/last", "/resume run-1", "/compact run-1", "/context", "/init", "/clear", "/exit"]),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_sessions_text", return_value="Recent sessions:\n  run-1"),
                patch("vibeagent.cli.get_usage_text", return_value="Usage:\n  sessions: 1"),
                patch("vibeagent.cli.get_cost_text", return_value="Cost:\n  estimatedCostUsd: $0.000001"),
                patch("vibeagent.cli.get_doctor_text", return_value="Doctor:\n  provider: minimax"),
                patch("vibeagent.cli.get_session_text", return_value="Session: run-1") as get_session_text,
                patch("vibeagent.cli.get_last_session_text", return_value="Session: run-1"),
                patch("vibeagent.cli.get_resume_context", return_value=("run-1", "context", "Resume context loaded from session run-1.")),
                patch("vibeagent.cli.get_compact_context", return_value=("run-1", "context", "Compacted context loaded from session run-1.")),
                patch("vibeagent.cli.get_context_text", return_value="Context:\n  resume: run-1"),
                patch("vibeagent.cli.init_project_instructions", return_value="Created AGENTS.md."),
                redirect_stdout(stdout),
            ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Recent sessions:", output)
        self.assertIn("Usage:", output)
        self.assertIn("Cost:", output)
        self.assertIn("Doctor:", output)
        self.assertIn("Session: run-1", output)
        self.assertIn("Resume context loaded", output)
        self.assertIn("Compacted context loaded", output)
        self.assertIn("Context:", output)
        self.assertIn("Created AGENTS.md.", output)
        self.assertIn("Cleared chat history and resume context.", output)
        get_session_text.assert_called_once_with("run-1")
        create_chat_client.assert_not_called()

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
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("mode: code", output)
        self.assertIn("approval: ask", output)
        self.assertIn("resume: none", output)
        self.assertIn("mode: chat", output)
        self.assertIn("approval: allow", output)
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
                patch("builtins.input", side_effect=["/resume run-1", "continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_resume_context", side_effect=[
                    ("run-1", "previous context", "Resume context loaded from session run-1."),
                    ("new-run", "new context", "Resume context loaded from session new-run."),
                ]),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "previous context")

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
                patch("builtins.input", side_effect=["/compact run-1", "continue task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.get_compact_context", return_value=("run-1", "compacted context", "Compacted context loaded from session run-1.")),
                patch("vibeagent.cli.get_resume_context", return_value=("new-run", "new context", "Resume context loaded from session new-run.")),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Compacted context loaded", output)
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "compacted context")

    def test_main_updates_approval_policy_and_passes_handler_to_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="test-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["/approval allow", "write file", "/approval deny", "run command", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Approval policy: allow", output)
        self.assertIn("Approval policy: deny", output)
        first_handler = run_agent.call_args_list[0].kwargs["approval_handler"]
        second_handler = run_agent.call_args_list[1].kwargs["approval_handler"]
        request = ApprovalRequest(action_type="write_file", target="note.txt", risk="write")
        self.assertTrue(first_handler(request).approved)
        self.assertFalse(second_handler(request).approved)


if __name__ == "__main__":
    unittest.main()
