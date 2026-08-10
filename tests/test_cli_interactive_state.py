import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.agent import AgentResult
from vibeagent.cli import main
from vibeagent.types import ApprovalRequest


class CliInteractiveStateTests(unittest.TestCase):
    def test_main_interactive_agent_profile_is_forwarded_to_code_turns(self) -> None:
        result = AgentResult(
            success=True,
            message="done",
            run_dir=Path(tempfile.gettempdir()),
            run_id="test-run",
            iterations=1,
            observations=[],
            steps=[],
        )
        run_agent = Mock(return_value=result)

        with (
            patch("builtins.input", side_effect=["inspect code", "/exit"]),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_agent", run_agent),
            redirect_stdout(io.StringIO()),
        ):
            exit_code = main(["--agent", "reviewer"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["agent"], "reviewer")

    def test_main_interactive_prompt_files_are_resolved_before_changing_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            project = root / "project"
            project.mkdir()
            (root / "system.txt").write_text("System from file.", encoding="utf-8")
            (root / "append.txt").write_text("Append from file.", encoding="utf-8")
            result = AgentResult(
                success=True,
                message="done",
                run_dir=project,
                run_id="test-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            previous_cwd = Path.cwd()
            os.chdir(root)
            try:
                with (
                    patch("builtins.input", side_effect=["inspect code", "/exit"]),
                    patch("vibeagent.cli.create_chat_client", return_value=object()),
                    patch("vibeagent.cli.run_agent", run_agent),
                    redirect_stdout(io.StringIO()),
                ):
                    exit_code = main(
                        [
                            "--cwd",
                            str(project),
                            "--system-prompt-file",
                            "system.txt",
                            "--append-system-prompt-file",
                            "append.txt",
                        ]
                    )
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["system_prompt"], "System from file.")
        self.assertEqual(run_agent.call_args.kwargs["append_system_prompt"], "Append from file.")

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
        self.assertEqual(run_agent.call_args_list[0].kwargs["approval_policy"], "allow")
        self.assertEqual(run_agent.call_args_list[1].kwargs["approval_policy"], "deny")
        request = ApprovalRequest(action_type="write_file", target="note.txt", risk="write")
        self.assertTrue(first_handler(request).approved)
        self.assertFalse(second_handler(request).approved)

    def test_main_interactive_system_prompt_commands_affect_code_and_chat_turns(self) -> None:
        result = AgentResult(
            success=True,
            message="done",
            run_dir=Path(tempfile.gettempdir()),
            run_id="test-run",
            iterations=1,
            observations=[],
            steps=[],
        )
        stdout = io.StringIO()
        run_agent = Mock(return_value=result)
        run_chat = Mock(return_value="chat response")

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/system-prompt You are a release engineer.",
                    "/append-system-prompt Prefer focused tests.",
                    "inspect code",
                    "/chat explain",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_agent", run_agent),
            patch("vibeagent.cli.run_chat", run_chat),
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["system_prompt"], "You are a release engineer.")
        self.assertEqual(run_agent.call_args.kwargs["append_system_prompt"], "Prefer focused tests.")
        self.assertEqual(run_chat.call_args.kwargs["system_prompt"], "You are a release engineer.")
        self.assertEqual(run_chat.call_args.kwargs["append_system_prompt"], "Prefer focused tests.")
        output = stdout.getvalue()
        self.assertIn("System prompt set", output)
        self.assertIn("Appended system prompt set", output)

    def test_main_interactive_system_prompt_status_and_clear(self) -> None:
        result = AgentResult(
            success=True,
            message="done",
            run_dir=Path(tempfile.gettempdir()),
            run_id="test-run",
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
                    "/system-prompt You are terse.",
                    "/append-system-prompt Prefer focused tests.",
                    "/status",
                    "/system-prompt off",
                    "/append-system-prompt off",
                    "inspect code",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_agent", run_agent),
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("systemPrompt: custom", output)
        self.assertIn("appendSystemPrompt: set", output)
        self.assertIn("System prompt cleared.", output)
        self.assertIn("Appended system prompt cleared.", output)
        self.assertIsNone(run_agent.call_args.kwargs["system_prompt"])
        self.assertIsNone(run_agent.call_args.kwargs["append_system_prompt"])

    def test_main_interactive_task_keyboard_interrupt_returns_to_prompt(self) -> None:
        stdout = io.StringIO()

        with (
            patch("builtins.input", side_effect=["write file", "/exit"]),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_agent", side_effect=KeyboardInterrupt) as run_agent,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Interrupted.", output)
        self.assertNotIn("Error:", output)
        self.assertEqual(run_agent.call_count, 1)


if __name__ == "__main__":
    unittest.main()
