import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.agent_result import AgentResult
from vibeagent.cli import main
from vibeagent.types import ChatMessage
from vibeagent.workspace_core import create_run_workspace


class RecapClient:
    pass


class InteractiveRecapTests(unittest.TestCase):
    def test_manual_recap_reads_but_does_not_mutate_code_history(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-recap-") as base:
            root = Path(base)
            agent_calls: list[dict[str, object]] = []
            recap_histories: list[list[ChatMessage]] = []

            def run_agent(task: str, **kwargs: object) -> AgentResult:
                agent_calls.append({"task": task, **kwargs})
                workspace = kwargs.get("workspace") or create_run_workspace(root)
                prior = list(kwargs.get("prior_messages") or [])
                return AgentResult(
                    True,
                    f"done: {task}",
                    root,
                    workspace.run_id,
                    1,
                    [],
                    [],
                    conversation=[
                        *prior,
                        ChatMessage(role="user", content=task),
                        ChatMessage(role="assistant", content=f"done: {task}"),
                    ],
                )

            def run_recap(client: object, **kwargs: object) -> str:
                recap_histories.append(list(kwargs["history"]))  # type: ignore[arg-type]
                return "first task completed"

            stdout = io.StringIO()
            with (
                patch("builtins.input", side_effect=["first task", "/recap", "second task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=RecapClient()),
                patch("vibeagent.cli.run_agent", side_effect=run_agent),
                patch("vibeagent.cli.run_session_recap", side_effect=run_recap),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=lambda run_id, **kwargs: (run_id, "context", "loaded"),
                ),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(recap_histories), 1)
        self.assertEqual(len(recap_histories[0]), 2)
        self.assertEqual(len(agent_calls[1]["prior_messages"]), 2)  # type: ignore[arg-type]
        self.assertNotIn("first task completed", str(agent_calls[1]["prior_messages"]))
        self.assertIn("first task completed", stdout.getvalue())

    def test_automatic_recap_uses_a_dedicated_client_after_three_turns(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-recap-") as base:
            root = Path(base)
            clients: list[RecapClient] = []
            recap_clients: list[object] = []

            def create_client(_env: dict[str, str | None]) -> RecapClient:
                client = RecapClient()
                clients.append(client)
                return client

            def run_agent(task: str, **kwargs: object) -> AgentResult:
                workspace = kwargs.get("workspace") or create_run_workspace(root)
                prior = list(kwargs.get("prior_messages") or [])
                return AgentResult(
                    True,
                    "done",
                    root,
                    workspace.run_id,
                    1,
                    [],
                    [],
                    conversation=[
                        *prior,
                        ChatMessage(role="user", content=task),
                        ChatMessage(role="assistant", content="done"),
                    ],
                )

            prompts = iter(["one", "two", "three", "/exit"])

            def idle_input(_prompt: str, callback, **_kwargs: object) -> str:
                callback()
                return next(prompts)

            def run_recap(client: object, **_kwargs: object) -> str:
                recap_clients.append(client)
                return "three turns completed"

            stdout = io.StringIO()
            with (
                patch("vibeagent.cli_interactive.input_with_idle_callback", side_effect=idle_input),
                patch("vibeagent.cli.create_chat_client", side_effect=create_client),
                patch("vibeagent.cli.run_agent", side_effect=run_agent),
                patch("vibeagent.cli.run_session_recap", side_effect=run_recap),
                patch("vibeagent.session_recap.AUTOMATIC_RECAP_DELAY_SECONDS", 0.0),
                patch("vibeagent.cli_interactive.scheduled_tasks_enabled", return_value=False),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=lambda run_id, **kwargs: (run_id, "context", "loaded"),
                ),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(clients), 2)
        self.assertIs(recap_clients[0], clients[1])
        self.assertIsNot(recap_clients[0], clients[0])
        self.assertIn("Session recap: three turns completed", stdout.getvalue())

    def test_recap_without_history_does_not_create_a_client(self) -> None:
        with (
            patch("builtins.input", side_effect=["/recap", "/exit"]),
            patch("vibeagent.cli.create_chat_client") as create_client,
            redirect_stdout(io.StringIO()) as stdout,
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        create_client.assert_not_called()
        self.assertIn("No conversation is available", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
