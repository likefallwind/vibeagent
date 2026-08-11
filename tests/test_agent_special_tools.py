from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.agent_special_tools import execute_special_tool_action
from vibeagent.types import (
    AssistantResponse,
    AskUserAction,
    ChatMessage,
    ContentBlock,
    DeepReviewAction,
    DeepReviewObservation,
    DeepReviewResult,
    DelegateTaskAction,
    Observation,
)
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import ProjectHooks
from vibeagent.workspace_permissions import ProjectPermissions


class SpecialToolClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


class AgentSpecialToolTests(unittest.TestCase):
    def test_executes_deep_review_through_special_tool_wrapper(self) -> None:
        expected = DeepReviewObservation(
            kind="deep_review",
            ok=True,
            results=[
                DeepReviewResult(
                    perspective="correctness",
                    ok=True,
                    summary="No findings.",
                    iterations=1,
                )
            ],
            verification_ok=True,
            summary="No findings.",
            base_ref=None,
            instructions_path=None,
            message="Deep review completed: 1/1 reviewer(s) succeeded.",
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-special-") as base:
            workspace = create_run_workspace(Path(base))
            steps = []
            with patch("vibeagent.agent_special_tools.execute_deep_review_action", return_value=expected) as execute:
                wrapped = execute_special_tool_action(
                    workspace,
                    DeepReviewAction(type="deep_review", perspectives=["correctness"]),
                    SpecialToolClient([]),
                    steps=steps,
                    observations=[],
                    iteration=1,
                    tool_name="deep_review",
                    max_output_tokens=2048,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                    approval_handler=None,
                    approval_policy="ask",
                    user_input_handler=None,
                    hooks=ProjectHooks(),
                    permissions=ProjectPermissions(),
                    execute_action_safely_func=_unexpected_execute_action_safely,
                )

        self.assertIs(wrapped.observation, expected)
        self.assertEqual(steps[0].status, "completed")
        execute.assert_called_once()

    def test_executes_ask_user_action_through_special_tool_wrapper(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-special-") as base:
            workspace = create_run_workspace(Path(base))
            steps = []
            wrapped = execute_special_tool_action(
                workspace,
                AskUserAction(type="ask_user", question="Continue?", options=["yes", "no"], allow_free_text=False),
                SpecialToolClient([]),
                steps=steps,
                observations=[],
                iteration=1,
                tool_name="ask_user",
                max_output_tokens=2048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=None,
                approval_policy="ask",
                user_input_handler=lambda _request: "yes",
                hooks=ProjectHooks(),
                permissions=ProjectPermissions(),
                execute_action_safely_func=_unexpected_execute_action_safely,
            )

        self.assertEqual(wrapped.observation.kind, "ask_user")
        self.assertEqual(wrapped.observation.answer, "yes")
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].status, "completed")

    def test_executes_delegate_action_through_special_tool_wrapper(self) -> None:
        client = SpecialToolClient([[{"type": "text", "text": "Found auth in app.py:1"}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-special-") as base:
            workspace = create_run_workspace(Path(base))
            steps = []
            wrapped = execute_special_tool_action(
                workspace,
                DelegateTaskAction(type="delegate_task", task="Find auth", max_iterations=2),
                client,
                steps=steps,
                observations=[],
                iteration=2,
                tool_name="delegate_task",
                max_output_tokens=2048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=None,
                approval_policy="ask",
                user_input_handler=None,
                hooks=ProjectHooks(),
                permissions=ProjectPermissions(),
                execute_action_safely_func=_unexpected_execute_action_safely,
            )

        self.assertEqual(wrapped.observation.kind, "delegate_task")
        self.assertTrue(wrapped.observation.ok)
        self.assertEqual(wrapped.observation.summary, "Found auth in app.py:1")
        self.assertEqual(len(client.messages), 1)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].status, "completed")

    def test_isolated_delegate_requires_worktree_approval_before_execution(self) -> None:
        client = SpecialToolClient([[{"type": "text", "text": "must not run"}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-special-") as base:
            workspace = create_run_workspace(Path(base))
            wrapped = execute_special_tool_action(
                workspace,
                DelegateTaskAction(
                    type="delegate_task",
                    task="Implement in isolation",
                    mode="code",
                    isolation="worktree",
                ),
                client,
                steps=[],
                observations=[],
                iteration=1,
                tool_name="Agent",
                max_output_tokens=2048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=None,
                approval_policy="ask",
                user_input_handler=None,
                hooks=ProjectHooks(),
                permissions=ProjectPermissions(),
                execute_action_safely_func=_unexpected_execute_action_safely,
            )

        self.assertEqual(wrapped.observation.kind, "approval_denied")
        self.assertEqual(wrapped.observation.action_type, "delegate_task_worktree")
        self.assertEqual(client.messages, [])

    def test_profile_required_isolation_is_resolved_before_approval(self) -> None:
        client = SpecialToolClient([[{"type": "text", "text": "must not run"}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-special-") as base:
            root = Path(base)
            profile = root / ".claude" / "agents" / "isolated.md"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                "---\nname: isolated\ndescription: isolated writer\nmode: code\n"
                "isolation: worktree\n---\n\nWrite only in isolation.\n",
                encoding="utf-8",
            )
            workspace = create_run_workspace(root)
            wrapped = execute_special_tool_action(
                workspace,
                DelegateTaskAction(type="delegate_task", task="Implement", agent="isolated"),
                client,
                steps=[],
                observations=[],
                iteration=1,
                tool_name="Agent",
                max_output_tokens=2048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=None,
                approval_policy="ask",
                user_input_handler=None,
                hooks=ProjectHooks(),
                permissions=ProjectPermissions(),
                execute_action_safely_func=_unexpected_execute_action_safely,
            )

        self.assertEqual(wrapped.observation.kind, "approval_denied")
        self.assertEqual(wrapped.observation.action_type, "delegate_task_worktree")
        self.assertEqual(client.messages, [])


def _unexpected_execute_action_safely(
    _workspace: object,
    _action: object,
    _command_timeout_ms: int,
    _tool_name: str,
) -> Observation:
    raise AssertionError("special tool tests should not execute generic actions")


if __name__ == "__main__":
    unittest.main()
