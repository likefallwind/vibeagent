import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.agent_result import AgentResult
from vibeagent.cli import main
from vibeagent.types import ChatMessage
from vibeagent.workspace_core import create_run_workspace


class CliBtwTests(unittest.TestCase):
    def test_btw_is_ephemeral_and_does_not_change_coding_conversation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-btw-") as base:
            root = Path(base)
            calls: list[dict[str, object]] = []
            first_conversation = [
                ChatMessage(role="user", content="first task"),
                ChatMessage(role="assistant", content="first result"),
            ]

            def run_agent(task: str, **kwargs: object) -> AgentResult:
                calls.append({"task": task, **kwargs})
                workspace = kwargs.get("workspace") or create_run_workspace(root)
                conversation = first_conversation if task == "first task" else [
                    *first_conversation,
                    ChatMessage(role="user", content=task),
                    ChatMessage(role="assistant", content="second result"),
                ]
                return AgentResult(
                    True,
                    "done",
                    root,
                    workspace.run_id,
                    1,
                    [],
                    [],
                    conversation=conversation,
                )

            run_btw = Mock(return_value="ephemeral answer")
            stdout = io.StringIO()
            with (
                patch("builtins.input", side_effect=["first task", "/btw what changed?", "second task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=run_agent),
                patch("vibeagent.cli.run_btw", run_btw),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=lambda run_id, **kwargs: (run_id, "bounded context", "loaded"),
                ),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertEqual([call["task"] for call in calls], ["first task", "second task"])
        self.assertEqual(run_btw.call_args.args[0], "what changed?")
        self.assertEqual(run_btw.call_args.kwargs["history"], first_conversation)
        self.assertEqual(calls[1]["prior_messages"], first_conversation)
        self.assertNotIn("what changed?", str(calls[1]["prior_messages"]))
        self.assertIn("ephemeral answer", stdout.getvalue())

    def test_btw_usage_and_failure_return_to_prompt(self) -> None:
        run_btw = Mock(side_effect=RuntimeError("provider unavailable"))
        stdout = io.StringIO()
        with (
            patch("builtins.input", side_effect=["/btw", "/btw question", "/exit"]),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_btw", run_btw),
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_btw.call_count, 1)
        self.assertIn("Usage: /btw <question>", stdout.getvalue())
        self.assertIn("BTW error: provider unavailable", stdout.getvalue())

    def test_btw_uses_chat_history_while_chat_mode_is_active(self) -> None:
        run_chat = Mock(return_value="chat answer")
        run_btw = Mock(return_value="side answer")
        with (
            patch("builtins.input", side_effect=["/chat", "hello", "/btw summarize", "/exit"]),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_chat", run_chat),
            patch("vibeagent.cli.run_btw", run_btw),
            redirect_stdout(io.StringIO()),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            run_btw.call_args.kwargs["history"],
            [
                ChatMessage(role="user", content="hello"),
                ChatMessage(role="assistant", content="chat answer"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
