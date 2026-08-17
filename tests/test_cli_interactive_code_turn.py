from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent.agent_result import AgentResult
from vibeagent.cli_interactive_code_turn import (
    InteractiveCodeTurnRequest,
    InteractiveCodeTurnServices,
    run_interactive_code_turn,
)
from vibeagent.debug_runtime import DebugOptions, DebugRuntime
from vibeagent.interactive_permission_mode import initial_interactive_permission_state
from vibeagent.types import ChatMessage
from vibeagent.workspace_permissions import ProjectPermissions


class InteractiveCodeTurnTests(unittest.TestCase):
    def test_returns_agent_session_conversation_and_permission_updates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-code-turn-") as base:
            root = Path(base).resolve()
            client = object()
            conversation = [ChatMessage(role="assistant", content="done")]
            result = AgentResult(
                True,
                "done",
                root,
                "run-new",
                1,
                [],
                [],
                approval_policy="allow",
                conversation=conversation,
            )
            project_runtime = Mock(peer=Mock())
            run_agent = Mock(return_value=result)
            print_result = Mock()
            collect = Mock(return_value=("directory context", ()))
            prior_messages = (ChatMessage(role="user", content="continue"),)
            request = self._request(
                root,
                project_runtime=project_runtime,
                conversation_messages=prior_messages,
            )
            services = self._services(
                client,
                run_agent=run_agent,
                print_result=print_result,
                collect=collect,
            )

            with patch(
                "vibeagent.cli_interactive_code_turn.SubagentPanel"
            ) as panel_type:
                panel_type.return_value.enabled = False
                panel_type.return_value.config_error = None
                turn = run_interactive_code_turn(request, services)

        self.assertIs(turn.agent_result, result)
        self.assertIs(turn.client, client)
        self.assertEqual(turn.resume_run_id, "run-new")
        self.assertEqual(turn.resume_context, "next context")
        self.assertEqual(turn.conversation_messages, tuple(conversation))
        self.assertEqual(turn.approval_policy, "allow")
        self.assertEqual(turn.permission_state.mode, "bypassPermissions")
        self.assertEqual(turn.pending_workspace.run_id, "run-new")
        self.assertIsNone(run_agent.call_args.kwargs["workspace"])
        self.assertIsInstance(run_agent.call_args.kwargs["prior_messages"], list)
        self.assertEqual(run_agent.call_args.kwargs["prior_messages"], list(prior_messages))
        self.assertEqual(
            run_agent.call_args.kwargs["append_system_prompt"],
            "directory context",
        )
        collect.assert_called_once()
        project_runtime.update_approval_policy.assert_called_once_with("allow")
        project_runtime.register_session.assert_called_once_with("run-new")
        print_result.assert_called_once_with(result, message_already_displayed=False)

    def test_safe_mode_skips_directory_hook_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-code-turn-") as base:
            root = Path(base).resolve()
            client = object()
            result = AgentResult(True, "done", root, "run-new", 1, [], [])
            project_runtime = Mock(peer=Mock())
            run_agent = Mock(return_value=result)
            collect = Mock()
            request = self._request(
                root,
                project_runtime=project_runtime,
                safe_mode=True,
            )

            with patch(
                "vibeagent.cli_interactive_code_turn.SubagentPanel"
            ) as panel_type:
                panel_type.return_value.enabled = False
                panel_type.return_value.config_error = None
                run_interactive_code_turn(
                    request,
                    self._services(client, run_agent=run_agent, collect=collect),
                )

        collect.assert_not_called()
        self.assertEqual(
            run_agent.call_args.kwargs["append_system_prompt"],
            "base append prompt",
        )

    @staticmethod
    def _request(
        root: Path,
        *,
        project_runtime: Mock,
        safe_mode: bool = False,
        conversation_messages: tuple[ChatMessage, ...] = (),
    ) -> InteractiveCodeTurnRequest:
        permission_state = initial_interactive_permission_state(
            permission_mode=None,
            approval_policy="ask",
            permission_overrides=ProjectPermissions(),
            allow_bypass=False,
        )
        return InteractiveCodeTurnRequest(
            project_root=root,
            task="inspect",
            task_metadata={"source": "test"},
            client=None,
            resume_run_id="run-old",
            resume_context="prior context",
            pending_workspace=None,
            pending_branch_source_run_id=None,
            conversation_messages=conversation_messages,
            approval_policy="ask",
            approval_handler=Mock(),
            permission_state=permission_state,
            permission_overrides=permission_state.permission_overrides,
            project_permissions_trusted=False,
            project_runtime=project_runtime,
            additional_directories=(),
            system_prompt=None,
            append_system_prompt="base append prompt",
            agent=None,
            dynamic_agent_profiles=(),
            teammate_mode=None,
            autocompact_tokens=None,
            safe_mode=safe_mode,
            bare_mode=False,
            brief=False,
            disable_slash_commands=False,
            verbose=False,
            screen_reader=False,
            browser_mode="auto",
            setting_sources=("user", "project", "local"),
            settings_override_json=None,
            invocation_plugin_dirs=(),
            debug_runtime=DebugRuntime(DebugOptions()),
        )

    @staticmethod
    def _services(
        client: object,
        *,
        run_agent: Mock,
        print_result: Mock | None = None,
        collect: Mock,
    ) -> InteractiveCodeTurnServices:
        return InteractiveCodeTurnServices(
            create_client=Mock(return_value=client),
            run_agent=run_agent,
            get_resume_context=Mock(
                return_value=("run-new", "next context", "loaded")
            ),
            resolve_execution_config=Mock(
                return_value=SimpleNamespace(
                    max_iterations=10,
                    command_timeout_ms=1_000,
                    max_output_tokens=1_000,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=1_000,
                )
            ),
            collect_directory_context=collect,
            print_agent_result=print_result or Mock(),
            prompt_user_input=Mock(),
        )


if __name__ == "__main__":
    unittest.main()
