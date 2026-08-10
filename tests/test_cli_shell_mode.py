from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.agent_result import AgentResult
from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.commands import get_resume_context
from vibeagent.session import build_session_resume_context, list_sessions


class CliShellModeTests(unittest.TestCase):
    def test_shell_mode_is_provider_free_and_creates_resume_context(self) -> None:
        stdout = io.StringIO()
        create_client = Mock(side_effect=AssertionError("provider should not be initialized"))

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-shell-") as base:
            root = Path(base)
            with (
                patch("builtins.input", side_effect=["! printf shell-mode-ok", "/exit"]),
                patch("vibeagent.cli_interactive.Path.cwd", return_value=root),
                redirect_stdout(stdout),
            ):
                exit_code = run_interactive_loop(
                    command_namespace={},
                    create_chat_client_func=create_client,
                )
            sessions = list_sessions(root)
            context = build_session_resume_context(root, sessions[0].run_id)

        self.assertEqual(exit_code, 0)
        self.assertIn("shell-mode-ok", stdout.getvalue())
        self.assertEqual(len(sessions), 1)
        self.assertIn("printf shell-mode-ok", context)
        self.assertIn("shell-mode-ok", context)
        create_client.assert_not_called()

    def test_empty_shell_mode_prints_usage_without_provider(self) -> None:
        stdout = io.StringIO()
        create_client = Mock(side_effect=AssertionError("provider should not be initialized"))

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-shell-") as base:
            with (
                patch("builtins.input", side_effect=["!", "/exit"]),
                patch("vibeagent.cli_interactive.Path.cwd", return_value=Path(base)),
                redirect_stdout(stdout),
            ):
                exit_code = run_interactive_loop(
                    command_namespace={},
                    create_chat_client_func=create_client,
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: ! <cmd>", stdout.getvalue())
        create_client.assert_not_called()

    def test_next_coding_turn_receives_shell_resume_context(self) -> None:
        stdout = io.StringIO()
        captured: dict[str, object] = {}

        def run_agent(task: str, **kwargs: object) -> AgentResult:
            captured.update({"task": task, **kwargs})
            run_id = str(kwargs["task_source_run_id"])
            return AgentResult(True, "coding done", Path(base), run_id, 1, [], [])

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-shell-") as base:
            root = Path(base)
            with (
                patch("builtins.input", side_effect=["! printf context-evidence", "use that result", "/exit"]),
                patch("vibeagent.cli_interactive.Path.cwd", return_value=root),
                redirect_stdout(stdout),
            ):
                exit_code = run_interactive_loop(
                    command_namespace={},
                    create_chat_client_func=Mock(return_value=object()),
                    run_agent_func=run_agent,
                    get_resume_context_func=lambda run_id: get_resume_context(run_id, root),
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(captured["task"], "use that result")
        self.assertIsInstance(captured["task_source_run_id"], str)
        self.assertIn("printf context-evidence", str(captured["prior_context"]))
        self.assertIn("context-evidence", str(captured["prior_context"]))
        self.assertIn("coding done", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
