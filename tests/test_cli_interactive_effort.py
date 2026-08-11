import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.agent_result import AgentResult
from vibeagent.cli import main
from vibeagent.cli_interactive_effort import (
    configure_interactive_effort,
    normalize_interactive_effort,
    resolve_interactive_effort_selection,
)
from vibeagent.types import ChatMessage
from vibeagent.workspace_core import create_run_workspace


class EffortClient:
    def __init__(
        self,
        model: str,
        effort: str | None = None,
        *,
        supports_effort: bool = True,
    ) -> None:
        self.model = model
        self.effort = effort
        self.supports_effort = supports_effort

    def complete(self, *_args: object, **_kwargs: object) -> str:
        return "done"

    def with_agent_profile(self, *, model: str | None, effort: str | None) -> "EffortClient":
        if effort is not None and not self.supports_effort:
            raise ValueError("provider does not support effort")
        return EffortClient(
            model or self.model,
            self.effort if effort is None else effort,
            supports_effort=self.supports_effort,
        )


class InteractiveEffortTests(unittest.TestCase):
    def test_effort_validation_and_status(self) -> None:
        self.assertEqual(normalize_interactive_effort(" HIGH "), "high")
        self.assertIsNone(normalize_interactive_effort("auto"))
        self.assertIsNone(normalize_interactive_effort("default"))
        self.assertIn(
            "effort: auto",
            resolve_interactive_effort_selection(None, None).text,
        )
        with self.assertRaisesRegex(ValueError, "Usage: /effort"):
            normalize_interactive_effort("ultracode")

    def test_configure_effort_rejects_clients_without_profile_support(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not support"):
            configure_interactive_effort(object(), "high")  # type: ignore[arg-type]

    def test_one_shot_code_and_chat_apply_cli_effort(self) -> None:
        code_clients: list[EffortClient] = []
        chat_clients: list[EffortClient] = []

        def run_agent(_task: str, **kwargs: object) -> AgentResult:
            code_clients.append(kwargs["client"])  # type: ignore[arg-type]
            return AgentResult(True, "done", Path.cwd(), "run-effort", 1, [], [])

        def run_chat(_task: str, **kwargs: object) -> str:
            chat_clients.append(kwargs["client"])  # type: ignore[arg-type]
            return "done"

        with (
            patch.dict(os.environ, {"CLAUDE_CODE_EFFORT_LEVEL": ""}),
            patch("vibeagent.cli.create_chat_client", return_value=EffortClient("model")),
            patch("vibeagent.cli.run_agent", side_effect=run_agent),
            patch("vibeagent.cli.run_chat", side_effect=run_chat),
            redirect_stdout(io.StringIO()),
        ):
            code_exit = main(["--effort", "high", "--print", "fix"])
            chat_exit = main(["--effort", "low", "--chat", "hello"])

        self.assertEqual((code_exit, chat_exit), (0, 0))
        self.assertEqual(code_clients[0].effort, "high")
        self.assertEqual(chat_clients[0].effort, "low")

    def test_environment_effort_locks_interactive_command(self) -> None:
        agent_clients: list[object] = []

        def run_agent(_task: str, **kwargs: object) -> AgentResult:
            agent_clients.append(kwargs["client"])
            return AgentResult(True, "done", Path.cwd(), "run-effort", 1, [], [])

        stdout = io.StringIO()
        with (
            patch.dict(os.environ, {"CLAUDE_CODE_EFFORT_LEVEL": "high"}),
            patch("builtins.input", side_effect=["/effort low", "/effort", "task", "/exit"]),
            patch("vibeagent.cli.create_chat_client", return_value=EffortClient("model")),
            patch("vibeagent.cli.run_agent", side_effect=run_agent),
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(agent_clients[0].effort, "high")
        self.assertIn("CLAUDE_CODE_EFFORT_LEVEL locks", stdout.getvalue())
        self.assertIn("source: CLAUDE_CODE_EFFORT_LEVEL", stdout.getvalue())

    def test_startup_effort_applies_to_btw_before_first_main_turn(self) -> None:
        with (
            patch.dict(os.environ, {"CLAUDE_CODE_EFFORT_LEVEL": ""}),
            patch("builtins.input", side_effect=["/btw question", "/exit"]),
            patch("vibeagent.cli.create_chat_client", return_value=EffortClient("model")),
            patch("vibeagent.cli.run_btw", return_value="answer") as run_btw,
            redirect_stdout(io.StringIO()),
        ):
            exit_code = main(["--effort", "high"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_btw.call_args.kwargs["client"].effort, "high")

    def test_invalid_environment_effort_fails_before_client_creation(self) -> None:
        with (
            patch.dict(os.environ, {"CLAUDE_CODE_EFFORT_LEVEL": "ultracode"}),
            patch("vibeagent.cli.create_chat_client") as create_client,
            redirect_stdout(io.StringIO()),
        ):
            exit_code = main(["--print", "task"])

        self.assertEqual(exit_code, 2)
        create_client.assert_not_called()

    def test_interactive_effort_applies_to_turns_and_auto_rebuilds_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-effort-") as base:
            root = Path(base)
            agent_clients: list[EffortClient] = []
            factory_clients: list[EffortClient] = []

            def create_client(_env: dict[str, str | None]) -> EffortClient:
                client = EffortClient("configured-model")
                factory_clients.append(client)
                return client

            def run_agent(task: str, **kwargs: object) -> AgentResult:
                agent_clients.append(kwargs["client"])  # type: ignore[arg-type]
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

            stdout = io.StringIO()
            with (
                patch(
                    "builtins.input",
                    side_effect=[
                        "/effort low",
                        "first",
                        "/status",
                        "/effort auto",
                        "second",
                        "/exit",
                    ],
                ),
                patch("vibeagent.cli.create_chat_client", side_effect=create_client),
                patch("vibeagent.cli.run_agent", side_effect=run_agent),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=lambda run_id, **kwargs: (run_id, "context", "loaded"),
                ),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(factory_clients), 2)
        self.assertEqual([client.effort for client in agent_clients], ["low", None])
        self.assertIn("effort: low", stdout.getvalue())
        self.assertIn("effort: auto", stdout.getvalue())

    def test_model_switch_preserves_effort_and_conversation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-effort-model-") as base:
            root = Path(base)
            agent_calls: list[dict[str, object]] = []

            def create_client(env: dict[str, str | None]) -> EffortClient:
                return EffortClient(str(env["ANTHROPIC_MODEL"]))

            def run_agent(task: str, **kwargs: object) -> AgentResult:
                agent_calls.append({"task": task, **kwargs})
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

            provider_env = {
                "VIBEAGENT_PROVIDER": "anthropic",
                "ANTHROPIC_MODEL": "configured-model",
                "ANTHROPIC_API_KEY": "test-key",
            }
            with (
                patch(
                    "builtins.input",
                    side_effect=["/effort high", "first", "/model session-model", "second", "/exit"],
                ),
                patch("vibeagent.cli_interactive_model.build_provider_env", return_value=provider_env),
                patch("vibeagent.cli.create_chat_client", side_effect=create_client),
                patch("vibeagent.cli.run_agent", side_effect=run_agent),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=lambda run_id, **kwargs: (run_id, "context", "loaded"),
                ),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            [(call["client"].model, call["client"].effort) for call in agent_calls],  # type: ignore[union-attr]
            [("configured-model", "high"), ("session-model", "high")],
        )
        self.assertEqual(len(agent_calls[1]["prior_messages"]), 2)  # type: ignore[arg-type]

    def test_chat_btw_and_manual_recap_share_effort_client(self) -> None:
        client = EffortClient("configured-model")
        with (
            patch(
                "builtins.input",
                side_effect=["/effort medium", "/chat", "hello", "/btw question", "/recap", "/exit"],
            ),
            patch("vibeagent.cli.create_chat_client", return_value=client),
            patch("vibeagent.cli.run_chat", return_value="chat answer") as run_chat,
            patch("vibeagent.cli.run_btw", return_value="btw answer") as run_btw,
            patch("vibeagent.cli.run_session_recap", return_value="recap answer") as run_recap,
            redirect_stdout(io.StringIO()),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        active = run_chat.call_args.kwargs["client"]
        self.assertEqual(active.effort, "medium")
        self.assertIs(run_btw.call_args.kwargs["client"], active)
        self.assertIs(run_recap.call_args.args[0], active)

    def test_unsupported_effort_keeps_previous_client_and_setting(self) -> None:
        clients: list[EffortClient] = []
        agent_clients: list[EffortClient] = []

        def create_client(_env: dict[str, str | None]) -> EffortClient:
            client = EffortClient("minimax", supports_effort=False)
            clients.append(client)
            return client

        def run_agent(_task: str, **kwargs: object) -> AgentResult:
            agent_clients.append(kwargs["client"])  # type: ignore[arg-type]
            return AgentResult(True, "done", Path.cwd(), "run-1", 1, [], [])

        stdout = io.StringIO()
        with (
            patch("builtins.input", side_effect=["/effort high", "/effort", "task", "/exit"]),
            patch("vibeagent.cli.create_chat_client", side_effect=create_client),
            patch("vibeagent.cli.run_agent", side_effect=run_agent),
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(clients), 2)
        self.assertIs(agent_clients[0], clients[1])
        self.assertIn("Effort switch error: provider does not support effort", stdout.getvalue())
        self.assertIn("effort: auto", stdout.getvalue())

    def test_effort_status_does_not_construct_client(self) -> None:
        with (
            patch("builtins.input", side_effect=["/effort", "/exit"]),
            patch("vibeagent.cli.create_chat_client") as create_client,
            redirect_stdout(io.StringIO()),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        create_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
