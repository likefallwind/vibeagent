import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.agent_result import AgentResult
from vibeagent.cli import main
from vibeagent.cli_config import provider_env_with_model_override
from vibeagent.cli_interactive_model import (
    MAX_INTERACTIVE_MODEL_CHARS,
    normalize_interactive_model,
    resolve_interactive_model_selection,
)
from vibeagent.types import ChatMessage
from vibeagent.workspace_core import create_run_workspace


class ModelClient:
    def __init__(self, model: str) -> None:
        self.model = model


class InteractiveModelTests(unittest.TestCase):
    def test_provider_override_uses_active_provider_specific_keys(self) -> None:
        minimax = provider_env_with_model_override(
            {"VIBEAGENT_PROVIDER": "minimax", "MINIMAX_MODEL": "old"},
            "mini-new",
        )
        anthropic = provider_env_with_model_override(
            {"VIBEAGENT_PROVIDER": "anthropic", "ANTHROPIC_MODEL": "old"},
            "claude-new",
        )
        deepseek = provider_env_with_model_override(
            {"VIBEAGENT_PROVIDER": "deepseek", "DEEPSEEK_MODEL": "old"},
            "deepseek-new",
        )

        self.assertEqual(minimax["MINIMAX_MODEL"], "mini-new")
        self.assertEqual(anthropic["ANTHROPIC_MODEL"], "claude-new")
        self.assertEqual(deepseek["DEEPSEEK_MODEL"], "deepseek-new")
        self.assertEqual(deepseek["OPENAI_COMPAT_MODEL"], "deepseek-new")

    def test_selection_reports_status_switch_and_default_reset(self) -> None:
        base_env = {
            "VIBEAGENT_PROVIDER": "anthropic",
            "ANTHROPIC_MODEL": "configured-model",
            "ANTHROPIC_API_KEY": "test-key",
        }
        with patch("vibeagent.cli_interactive_model.build_provider_env", return_value=base_env):
            status = resolve_interactive_model_selection(".", None, None)
            switched = resolve_interactive_model_selection(".", "session-model", None)
            reset = resolve_interactive_model_selection(".", "default", "session-model")

        self.assertFalse(status.changed)
        self.assertEqual(status.override, None)
        self.assertIn("model: configured-model", status.text)
        self.assertEqual(switched.override, "session-model")
        self.assertTrue(switched.changed)
        self.assertEqual(switched.provider_env["ANTHROPIC_MODEL"], "session-model")
        self.assertIn("source: session override", switched.text)
        self.assertIsNone(reset.override)
        self.assertTrue(reset.changed)
        self.assertEqual(reset.provider_env["ANTHROPIC_MODEL"], "configured-model")

    def test_model_name_validation_is_bounded_and_unambiguous(self) -> None:
        self.assertEqual(normalize_interactive_model("  model/v2  "), "model/v2")
        self.assertIsNone(normalize_interactive_model("DEFAULT"))
        with self.assertRaisesRegex(ValueError, "Usage"):
            normalize_interactive_model(" ")
        with self.assertRaisesRegex(ValueError, "whitespace"):
            normalize_interactive_model("two models")
        with self.assertRaisesRegex(ValueError, "control"):
            normalize_interactive_model("model\x00name")
        with self.assertRaisesRegex(ValueError, "at most"):
            normalize_interactive_model("x" * (MAX_INTERACTIVE_MODEL_CHARS + 1))

    def test_interactive_switch_rebuilds_client_and_preserves_conversation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-model-switch-") as base:
            root = Path(base)
            created_models: list[str] = []
            agent_calls: list[dict[str, object]] = []

            def create_client(env: dict[str, str | None]) -> ModelClient:
                model = str(env["ANTHROPIC_MODEL"])
                created_models.append(model)
                return ModelClient(model)

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

            provider_env = {
                "VIBEAGENT_PROVIDER": "anthropic",
                "ANTHROPIC_MODEL": "configured-model",
                "ANTHROPIC_API_KEY": "test-key",
            }
            stdout = io.StringIO()
            with (
                patch(
                    "builtins.input",
                    side_effect=[
                        "first task",
                        "/model session-model",
                        "/model",
                        "second task",
                        "/model default",
                        "third task",
                        "/exit",
                    ],
                ),
                patch("vibeagent.cli_interactive_model.build_provider_env", return_value=provider_env),
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
        self.assertEqual(created_models, ["configured-model", "session-model", "configured-model"])
        self.assertEqual(
            [call["client"].model for call in agent_calls],
            ["configured-model", "session-model", "configured-model"],
        )
        self.assertEqual(len(agent_calls[1]["prior_messages"]), 2)
        self.assertEqual(len(agent_calls[2]["prior_messages"]), 4)
        self.assertIn("model: session-model", stdout.getvalue())

    def test_failed_switch_keeps_previous_client_and_model(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-model-failure-") as base:
            root = Path(base)
            clients: list[ModelClient] = []
            agent_clients: list[ModelClient] = []

            def create_client(env: dict[str, str | None]) -> ModelClient:
                model = str(env["ANTHROPIC_MODEL"])
                if model == "broken-model":
                    raise RuntimeError("unsupported model")
                client = ModelClient(model)
                clients.append(client)
                return client

            def run_agent(task: str, **kwargs: object) -> AgentResult:
                agent_clients.append(kwargs["client"])  # type: ignore[arg-type]
                workspace = kwargs.get("workspace") or create_run_workspace(root)
                return AgentResult(True, "done", root, workspace.run_id, 1, [], [])

            provider_env = {
                "VIBEAGENT_PROVIDER": "anthropic",
                "ANTHROPIC_MODEL": "configured-model",
                "ANTHROPIC_API_KEY": "test-key",
            }
            stdout = io.StringIO()
            with (
                patch("builtins.input", side_effect=["first", "/model broken-model", "second", "/exit"]),
                patch("vibeagent.cli_interactive_model.build_provider_env", return_value=provider_env),
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
        self.assertEqual(len(clients), 1)
        self.assertEqual(agent_clients, [clients[0], clients[0]])
        self.assertIn("Model switch error: unsupported model", stdout.getvalue())

    def test_model_status_does_not_construct_client(self) -> None:
        provider_env = {
            "VIBEAGENT_PROVIDER": "anthropic",
            "ANTHROPIC_MODEL": "configured-model",
            "ANTHROPIC_API_KEY": "test-key",
        }
        with (
            patch("builtins.input", side_effect=["/model", "/exit"]),
            patch("vibeagent.cli_interactive_model.build_provider_env", return_value=provider_env),
            patch("vibeagent.cli.create_chat_client") as create_client,
            redirect_stdout(io.StringIO()),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        create_client.assert_not_called()

    def test_switched_client_is_shared_by_chat_and_btw(self) -> None:
        provider_env = {
            "VIBEAGENT_PROVIDER": "anthropic",
            "ANTHROPIC_MODEL": "configured-model",
            "ANTHROPIC_API_KEY": "test-key",
        }
        switched_client = ModelClient("session-model")
        with (
            patch(
                "builtins.input",
                side_effect=["/model session-model", "/chat hello", "/btw question", "/exit"],
            ),
            patch("vibeagent.cli_interactive_model.build_provider_env", return_value=provider_env),
            patch("vibeagent.cli.create_chat_client", return_value=switched_client),
            patch("vibeagent.cli.run_chat", return_value="chat answer") as run_chat,
            patch("vibeagent.cli.run_btw", return_value="btw answer") as run_btw,
            redirect_stdout(io.StringIO()),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIs(run_chat.call_args.kwargs["client"], switched_client)
        self.assertIs(run_btw.call_args.kwargs["client"], switched_client)


if __name__ == "__main__":
    unittest.main()
