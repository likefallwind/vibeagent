import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.agent import AgentResult
from vibeagent.cli import format_error, main, prompt_approval
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

    def test_main_handles_session_commands_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("builtins.input", side_effect=["/sessions", "/session run-1", "/last", "/exit"]),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_sessions_text", return_value="Recent sessions:\n  run-1"),
            patch("vibeagent.cli.get_session_text", return_value="Session: run-1") as get_session_text,
            patch("vibeagent.cli.get_last_session_text", return_value="Session: run-1"),
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Recent sessions:", output)
        self.assertIn("Session: run-1", output)
        get_session_text.assert_called_once_with("run-1")
        create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
