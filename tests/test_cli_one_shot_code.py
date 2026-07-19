from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from vibeagent.agent_result import AgentResult
from vibeagent.cli_one_shot_code import run_one_shot_code
from vibeagent.cli_output_mode import CliOutputMode
from vibeagent.config import ExecutionConfig


class CliOneShotCodeTests(unittest.TestCase):
    def test_run_one_shot_code_runs_agent_and_emits_result(self) -> None:
        project_root = Path("/tmp/vibeagent-code")
        provider_env: dict[str, str | None] = {"VIBEAGENT_PROVIDER": "minimax"}
        clients: list[dict[str, str | None]] = []
        agent_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        emitted: list[tuple[AgentResult, dict[str, object]]] = []

        def create_client(env: dict[str, str | None]) -> object:
            clients.append(env)
            return "client"

        def run_agent(*args, **kwargs) -> AgentResult:
            agent_calls.append((args, kwargs))
            return AgentResult(True, "done", project_root, "run-1", 1, [], [])

        def get_resume_context(run_id, root, **kwargs):
            return "run-0", "previous context", "ok"

        def get_compact_context(run_id, root, **kwargs):
            return None, None, "not used"

        with patch("vibeagent.cli_one_shot_code.emit_one_shot_code_payload") as emit_payload:
            emit_payload.side_effect = lambda result, payload, **kwargs: emitted.append((result, payload))
            exit_code, prior_context = run_one_shot_code(
                "fix tests",
                project_root=project_root,
                execution_config=ExecutionConfig(max_iterations=3, command_timeout_ms=100),
                provider_env=provider_env,
                approval_policy="allow",
                trust_project_permissions=True,
                permission_overrides=None,
                resolved_mcp_config_paths=(project_root / ".mcp.json",),
                strict_mcp_config=True,
                output_mode=CliOutputMode(format="text", machine=False, stream_json=False),
                output_json=False,
                print_mode=False,
                elapsed_ms=42,
                stream=None,
                input_prior_context="input context",
                system_prompt="system",
                append_system_prompt="append",
                task_metadata={"source": "project_command"},
                resume_arg="run-0",
                compact_arg=None,
                auto_compact=True,
                resume_max_files=2,
                create_chat_client_func=create_client,
                run_agent_func=run_agent,
                get_resume_context_func=get_resume_context,
                get_compact_context_func=get_compact_context,
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(prior_context.context, "previous context")
        self.assertEqual(clients, [provider_env])
        self.assertEqual(agent_calls[0][0], ("fix tests",))
        self.assertEqual(agent_calls[0][1]["client"], "client")
        self.assertEqual(agent_calls[0][1]["prior_context"], "previous context\n\ninput context")
        self.assertEqual(agent_calls[0][1]["system_prompt"], "system")
        self.assertEqual(agent_calls[0][1]["append_system_prompt"], "append")
        self.assertEqual(agent_calls[0][1]["task_metadata"], {"source": "project_command"})
        self.assertEqual(agent_calls[0][1]["mcp_config_paths"], (project_root / ".mcp.json",))
        self.assertTrue(agent_calls[0][1]["strict_mcp_config"])
        self.assertEqual(emitted[0][1]["kind"], "code")
        self.assertEqual(emitted[0][1]["message"], "done")

    def test_run_one_shot_code_returns_prior_context_error_without_agent_run(self) -> None:
        calls: list[str] = []

        def get_resume_context(run_id, root, **kwargs):
            calls.append("resume")
            return "missing", None, "No matching session."

        def get_compact_context(run_id, root, **kwargs):
            calls.append("compact")
            return None, None, "not used"

        exit_code, prior_context = run_one_shot_code(
            "fix tests",
            project_root=Path("/tmp/vibeagent-code"),
            execution_config=ExecutionConfig(),
            provider_env={},
            approval_policy="allow",
            trust_project_permissions=True,
            permission_overrides=None,
            resolved_mcp_config_paths=(),
            strict_mcp_config=False,
            output_mode=CliOutputMode(format="text", machine=False, stream_json=False),
            output_json=False,
            print_mode=False,
            elapsed_ms=42,
            stream=None,
            input_prior_context=None,
            system_prompt=None,
            append_system_prompt=None,
            task_metadata=None,
            resume_arg="missing",
            compact_arg=None,
            auto_compact=True,
            create_chat_client_func=lambda env: calls.append("client"),
            run_agent_func=lambda *args, **kwargs: calls.append("agent"),
            get_resume_context_func=get_resume_context,
            get_compact_context_func=get_compact_context,
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(prior_context.error, "No matching session.")
        self.assertEqual(calls, ["resume"])


if __name__ == "__main__":
    unittest.main()
