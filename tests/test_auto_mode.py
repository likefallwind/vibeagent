from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent.agent_hook_prompt import HookModelRuntime
from vibeagent.agent_permission_denied_hooks import parse_permission_denied_retry
from vibeagent.agent_permissions import authorize_tool_action
from vibeagent.auto_mode import (
    AutoModeRuntime,
    parse_auto_mode_decision,
    sanitized_auto_mode_context,
)
from vibeagent.auto_mode_config import AutoModeConfig
from vibeagent.agent_hook_results import HookRunResult
from vibeagent.types import (
    ApprovalDecision,
    ApprovalRequest,
    AssistantResponse,
    ChatMessage,
    RunCommandAction,
)
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_permissions import ProjectPermissions
from vibeagent.workspace_permissions import ProjectPermissionRule


class QueueClient:
    def __init__(self, payloads: list[dict[str, object]]) -> None:
        self.payloads = list(payloads)
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, **_kwargs):
        self.messages.append(messages)
        payload = self.payloads.pop(0)
        return AssistantResponse(
            content=[{"type": "text", "text": json.dumps(payload)}],
            raw={},
        )


def _runtime(client: QueueClient, messages: list[ChatMessage], *, interactive: bool) -> AutoModeRuntime:
    model = HookModelRuntime(
        client=client,
        complete_with_retries=lambda active_client, active_messages, **_kwargs: (
            active_client.complete(active_messages),
            None,
        ),
        max_output_tokens=1024,
        model_retries=0,
        model_retry_delay_ms=0,
    )
    return AutoModeRuntime(model, lambda: messages, interactive)


def _request() -> ApprovalRequest:
    return ApprovalRequest(
        action_type="run_command",
        target="git status",
        risk="Runs a command.",
    )


def _action() -> RunCommandAction:
    return RunCommandAction(type="run_command", command="git status")


class AutoModeParsingTests(unittest.TestCase):
    def test_requires_exact_typed_json_contract(self) -> None:
        self.assertEqual(
            parse_auto_mode_decision('{"allow": true, "reason": "scoped"}'),
            (True, "scoped"),
        )
        with self.assertRaises(ValueError):
            parse_auto_mode_decision('{"allow": true, "reason": "ok", "extra": 1}')
        with self.assertRaises(ValueError):
            parse_auto_mode_decision('{"allow": "yes", "reason": "ok"}')

    def test_context_excludes_tool_results_but_keeps_assistant_tool_calls(self) -> None:
        context = sanitized_auto_mode_context(
            [
                ChatMessage(role="user", content="Update the project"),
                ChatMessage(
                    role="assistant",
                    content=[
                        {"type": "tool_call", "name": "Read", "input": {"path": "a.py"}}
                    ],
                ),
                ChatMessage(
                    role="user",
                    content=[
                        {"type": "tool_result", "tool_use_id": "1", "content": "UNTRUSTED SECRET"}
                    ],
                ),
            ]
        )
        encoded = json.dumps(context)
        self.assertIn("Update the project", encoded)
        self.assertIn("tool_call", encoded)
        self.assertNotIn("UNTRUSTED SECRET", encoded)


class AutoModeRuntimeTests(unittest.TestCase):
    def test_classifier_receives_effective_tiered_policy_and_workspace(self) -> None:
        client = QueueClient([{"allow": True, "reason": "policy permits it"}])
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-") as base:
            workspace = create_run_workspace(base)
            runtime = _runtime(client, [ChatMessage(role="user", content="run tests")], interactive=False)
            runtime.config = AutoModeConfig(
                environment=("env: local",),
                allow=("tests: run local tests",),
                soft_deny=("remote: avoid remote effects",),
                hard_deny=("secret: never exfiltrate",),
                classify_all_shell=True,
                customized=True,
            )
            result = runtime.authorize(
                workspace,
                tool_name="Bash",
                tool_input={"command": "pytest"},
                request=_request(),
                iteration=1,
            )
        prompt = str(client.messages[0][0].content)
        self.assertTrue(result.decision.approved)
        self.assertIn('"hard_deny": ["secret: never exfiltrate"]', prompt)
        self.assertIn('"classify_all_shell": true', prompt)
        self.assertIn(workspace.root.as_posix(), prompt)

    def test_workspace_file_change_uses_classifier(self) -> None:
        client = QueueClient([{"allow": False, "reason": "not requested"}])
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-") as base:
            workspace = create_run_workspace(base)
            runtime = _runtime(client, [], interactive=False)
            with patch("vibeagent.agent_permissions.sandbox_auto_approval_reason", return_value=None):
                result = authorize_tool_action(
                    workspace,
                    ProjectPermissions(),
                    "Write",
                    _action(),
                    1,
                    None,
                    "auto",
                    None,
                    default_request=ApprovalRequest("write_file", "note.txt", "writes a file"),
                    auto_mode_runtime=runtime,
                    tool_input={"path": "note.txt", "content": "data"},
                )
        self.assertFalse(result.allowed)
        self.assertEqual(len(client.messages), 1)

    def test_classify_all_shell_suspends_trusted_allow_rule(self) -> None:
        client = QueueClient([{"allow": False, "reason": "shell review required"}])
        allow_rule = ProjectPermissionRule(
            effect="allow",
            tool="Bash",
            specifier="git status",
            raw="Bash(git status)",
            source="CLI --allowedTools",
        )
        permissions = ProjectPermissions(
            rules=(allow_rule,),
            trusted_allow_sources=(allow_rule.source,),
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-") as base:
            workspace = create_run_workspace(base)
            runtime = _runtime(client, [], interactive=False)
            runtime.config = AutoModeConfig(classify_all_shell=True, customized=True)
            with patch("vibeagent.agent_permissions.sandbox_auto_approval_reason", return_value="sandboxed"):
                result = authorize_tool_action(
                    workspace,
                    permissions,
                    "Bash",
                    _action(),
                    1,
                    None,
                    "auto",
                    None,
                    default_request=_request(),
                    auto_mode_runtime=runtime,
                    tool_input={"command": "git status"},
                )
        self.assertFalse(result.allowed)
        self.assertEqual(len(client.messages), 1)

    def test_third_denial_falls_back_only_for_interactive_sessions(self) -> None:
        payloads = [{"allow": False, "reason": "too risky"}] * 6
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-") as base:
            workspace = create_run_workspace(base)
            interactive = _runtime(QueueClient(payloads[:3]), [], interactive=True)
            batch = [
                interactive.authorize(
                    workspace,
                    tool_name="Bash",
                    tool_input={"command": "deploy"},
                    request=_request(),
                    iteration=index,
                )
                for index in range(1, 4)
            ]
            noninteractive = _runtime(QueueClient(payloads[3:]), [], interactive=False)
            blocked = [
                noninteractive.authorize(
                    workspace,
                    tool_name="Bash",
                    tool_input={"command": "deploy"},
                    request=_request(),
                    iteration=index,
                )
                for index in range(1, 4)
            ]
        self.assertFalse(batch[1].fallback_to_prompt)
        self.assertTrue(batch[2].fallback_to_prompt)
        self.assertFalse(blocked[2].fallback_to_prompt)
        self.assertTrue(blocked[2].interrupt)

    def test_authorizer_uses_classifier_and_retry_hook_without_reversing_denial(self) -> None:
        client = QueueClient([{"allow": False, "reason": "external side effect"}])
        hook = Mock(return_value=((), True))
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-") as base:
            workspace = create_run_workspace(base)
            runtime = _runtime(client, [ChatMessage(role="user", content="inspect")], interactive=True)
            with patch("vibeagent.agent_permissions.sandbox_auto_approval_reason", return_value=None):
                result = authorize_tool_action(
                    workspace,
                    ProjectPermissions(),
                    "Bash",
                    _action(),
                    1,
                    lambda _request: ApprovalDecision(True, "prompted"),
                    "auto",
                    None,
                    default_request=_request(),
                    auto_mode_runtime=runtime,
                    tool_input={"command": "git status"},
                    permission_denied_handler=hook,
                )
        self.assertFalse(result.allowed)
        self.assertIn("allows the model to retry", result.denial.message)
        hook.assert_called_once_with("external side effect")

    def test_non_classifier_allow_resets_consecutive_denials(self) -> None:
        runtime = _runtime(QueueClient([]), [], interactive=True)
        runtime.consecutive_denials = 2
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-") as base:
            workspace = create_run_workspace(base)
            with patch(
                "vibeagent.agent_permissions.sandbox_auto_approval_reason",
                return_value="sandboxed",
            ):
                result = authorize_tool_action(
                    workspace,
                    ProjectPermissions(),
                    "Bash",
                    _action(),
                    1,
                    None,
                    "auto",
                    None,
                    default_request=_request(),
                    auto_mode_runtime=runtime,
                )
        self.assertTrue(result.allowed)
        self.assertEqual(runtime.consecutive_denials, 0)


class PermissionDeniedHookParsingTests(unittest.TestCase):
    def test_parses_retry_output(self) -> None:
        result = HookRunResult(
            event="PermissionDenied",
            command="hook",
            source="test",
            status="passed",
            ok=True,
            exit_code=0,
            timed_out=False,
            stdout=json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PermissionDenied",
                        "retry": True,
                    }
                }
            ),
            stderr="",
            message="passed",
        )
        self.assertTrue(parse_permission_denied_retry(result))


if __name__ == "__main__":
    unittest.main()
