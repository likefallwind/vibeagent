from __future__ import annotations

import json
import shlex
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.agent_hook_results import HookRunResult
from vibeagent.agent_hooks import run_hooks_around_tool, run_permission_request_hooks
from vibeagent.agent_permission_request_hooks import (
    PermissionRequestHookOutcome,
    PermissionRequestHookOutputError,
    merge_permission_request_behavior,
    parse_permission_request_hook_output,
)
from vibeagent.agent_permissions import authorize_tool_action
from vibeagent.agent import run_agent
from vibeagent.types import (
    ApprovalDecision,
    ApprovalRequest,
    AssistantResponse,
    ChatMessage,
    ContentBlock,
    RunCommandAction,
)
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hook_types import ProjectHook, ProjectHooks
from vibeagent.workspace_permissions import (
    ProjectPermissionRule,
    ProjectPermissions,
)


def _result(
    *,
    status: str = "passed",
    ok: bool = True,
    stdout: str = "",
    stderr: str = "",
    exit_code: int | None = 0,
    message: str = "passed",
    handler_type: str = "command",
) -> HookRunResult:
    return HookRunResult(
        event="PermissionRequest",
        command="hook",
        source="test",
        status=status,
        ok=ok,
        exit_code=exit_code,
        timed_out=False,
        stdout=stdout,
        stderr=stderr,
        message=message,
        handler_type=handler_type,
    )


def _payload(behavior: str, **decision_fields: object) -> str:
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": behavior, **decision_fields},
            }
        }
    )


def _hook(handler_type: str = "command") -> ProjectHook:
    return ProjectHook(
        event="PermissionRequest",
        matcher="Bash",
        command="hook",
        timeout_ms=10_000,
        source="test",
        handler_type=handler_type,
        prompt="Review this request" if handler_type in {"prompt", "agent"} else "",
    )


def _request() -> ApprovalRequest:
    return ApprovalRequest(
        action_type="run_command",
        target="npm test",
        risk="Run a command.",
    )


def _action() -> RunCommandAction:
    return RunCommandAction(type="run_command", command="npm test")


class HookClient:
    def __init__(self, path: str) -> None:
        self.path = path
        self.messages: list[list[ChatMessage]] = []

    def complete(
        self,
        messages,
        tools=None,
        max_tokens=4096,
        temperature=0.2,
        timeout_ms=120_000,
    ):
        self.messages.append(list(messages))
        content: list[ContentBlock]
        if len(self.messages) == 1:
            content = [
                {
                    "type": "tool_call",
                    "id": "write-1",
                    "name": "write_file",
                    "input": {"path": self.path, "content": "ok = True\n"},
                }
            ]
        else:
            content = [{"type": "text", "text": "Tool call handled."}]
        return AssistantResponse(content=content, raw={"content": content})


class PermissionRequestHookOutputTests(unittest.TestCase):
    def test_parses_allow_and_deny_and_merges_deny_first(self) -> None:
        allow = parse_permission_request_hook_output(
            _result(stdout=_payload("allow"))
        )
        deny = parse_permission_request_hook_output(
            _result(stdout=_payload("deny", message="blocked by policy"))
        )

        self.assertEqual(allow.behavior, "allow")
        self.assertEqual(deny.behavior, "deny")
        self.assertEqual(deny.message, "blocked by policy")
        self.assertEqual(merge_permission_request_behavior(None, "allow"), "allow")
        self.assertEqual(merge_permission_request_behavior("allow", "deny"), "deny")
        self.assertEqual(merge_permission_request_behavior("deny", "allow"), "deny")

    def test_rejects_invalid_or_unsupported_decisions(self) -> None:
        invalid_outputs = (
            '{"hookSpecificOutput":',
            json.dumps({"hookSpecificOutput": []}),
            _payload("review"),
            _payload("deny"),
            json.dumps(
                {"hookSpecificOutput": {"decision": {"behavior": "allow"}}}
            ),
            _payload("allow", message="not valid for allow"),
            _payload("allow", updatedInput={"command": "true"}),
            _payload("allow", updatedPermissions=[]),
            _payload("deny", message="blocked", interrupt=True),
        )

        for stdout in invalid_outputs:
            with self.subTest(stdout=stdout), self.assertRaises(
                PermissionRequestHookOutputError
            ):
                parse_permission_request_hook_output(_result(stdout=stdout))


class PermissionRequestHookRunnerTests(unittest.TestCase):
    def test_maps_all_handler_results_and_omits_tool_use_id(self) -> None:
        hooks = ProjectHooks(
            hooks=(
                _hook("command"),
                _hook("http"),
                _hook("mcp_tool"),
                _hook("prompt"),
                _hook("agent"),
            )
        )
        results = (
            _result(stdout=_payload("allow")),
            _result(stdout=_payload("allow"), handler_type="http"),
            _result(
                ok=False,
                status="failed",
                exit_code=2,
                stderr="denied by service",
                message="failed",
                handler_type="mcp_tool",
            ),
            _result(handler_type="prompt"),
            _result(
                ok=False,
                status="blocked",
                exit_code=None,
                message="agent rejected request",
                handler_type="agent",
            ),
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-hook-") as base:
            workspace = create_run_workspace(base)
            with patch(
                "vibeagent.agent_tool_hook_runtime.run_project_hook", side_effect=results
            ) as run_hook:
                outcome = run_permission_request_hooks(
                    workspace,
                    hooks,
                    "Bash",
                    _action(),
                    {"command": "npm test"},
                    1,
                    10_000,
                    None,
                    None,
                    "ask",
                    Mock(),
                    ProjectPermissions(),
                )

        self.assertEqual(outcome.behavior, "deny")
        self.assertEqual(outcome.message, "denied by service")
        self.assertEqual(len(outcome.results), 5)
        for call in run_hook.call_args_list:
            hook_input = call.kwargs["hook_input"]
            self.assertEqual(hook_input["hook_event_name"], "PermissionRequest")
            self.assertNotIn("tool_use_id", hook_input)

    def test_rejected_structured_output_is_non_blocking(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-hook-") as base:
            workspace = create_run_workspace(base)
            with patch(
                "vibeagent.agent_tool_hook_runtime.run_project_hook",
                return_value=_result(stdout=_payload("allow", updatedInput={})),
            ):
                outcome = run_permission_request_hooks(
                    workspace,
                    ProjectHooks(hooks=(_hook(),)),
                    "Bash",
                    _action(),
                    {"command": "npm test"},
                    1,
                    10_000,
                    None,
                    None,
                    "ask",
                    Mock(),
                    ProjectPermissions(),
                )
            events = [
                json.loads(line)
                for line in workspace.session_dir.joinpath("events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        self.assertIsNone(outcome.behavior)
        self.assertFalse(outcome.results[0].ok)
        self.assertTrue(outcome.results[0].non_blocking_error)
        self.assertIn("output was rejected", outcome.results[0].message)
        self.assertEqual(
            [event["type"] for event in events],
            ["permission_request_hook_output_rejected"],
        )

    def test_shared_special_tool_wrapper_applies_permission_request_denial(self) -> None:
        execute_tool = Mock()
        approval = Mock()
        blocked = _result(
            ok=False,
            status="blocked",
            exit_code=None,
            message="agent rejected special tool",
            handler_type="agent",
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-hook-") as base:
            workspace = create_run_workspace(base)
            with (
                patch(
                    "vibeagent.agent_tool_hook_runtime.run_project_hook",
                    return_value=blocked,
                ),
                patch(
                    "vibeagent.agent_permissions.sandbox_auto_approval_reason",
                    return_value=None,
                ),
            ):
                wrapped = run_hooks_around_tool(
                    workspace,
                    ProjectHooks(hooks=(_hook("agent"),)),
                    "Bash",
                    _action(),
                    1,
                    10_000,
                    None,
                    approval,
                    "ask",
                    Mock(),
                    execute_tool,
                    build_default_approval_request=lambda _action: _request(),
                )

        self.assertEqual(wrapped.observation.kind, "approval_denied")
        self.assertEqual(wrapped.observation.message, "agent rejected special tool")
        self.assertEqual(wrapped.hook_results, (blocked,))
        execute_tool.assert_not_called()
        approval.assert_not_called()


class PermissionRequestHookIntegrationTests(unittest.TestCase):
    def _run(self, root: Path, behavior: str, *, message: str | None = None):
        output = _payload(behavior, **({"message": message} if message else {}))
        command = (
            "python3 -c "
            + shlex.quote(f"import json; print({output!r})")
        )
        hook_path = root / ".vibeagent" / "hooks.json"
        hook_path.parent.mkdir(parents=True, exist_ok=True)
        hook_path.write_text(
            json.dumps(
                {
                    "PermissionRequest": [
                        {
                            "matcher": "write_file",
                            "hooks": [{"type": "command", "command": command}],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        approvals: list[str] = []

        def approve(request):
            approvals.append(request.action_type)
            return ApprovalDecision(approved=True, message="approved")

        client = HookClient(f"{behavior}.py")
        with patch(
            "vibeagent.agent_permissions.sandbox_auto_approval_reason",
            return_value=None,
        ):
            result = run_agent(
                f"Write {behavior}.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=approve,
            )
        return result, approvals, client

    def test_structured_allow_and_deny_replace_target_approval(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-hook-") as base:
            root = Path(base)
            allowed, allow_approvals, allow_client = self._run(root, "allow")
            denied, deny_approvals, deny_client = self._run(
                root, "deny", message="blocked by policy"
            )

            self.assertTrue(root.joinpath("allow.py").exists())
            self.assertFalse(root.joinpath("deny.py").exists())

        self.assertTrue(allowed.success)
        self.assertEqual(allow_approvals, ["run_command"])
        self.assertEqual(deny_approvals, ["run_command"])
        self.assertEqual(denied.observations[0].kind, "approval_denied")
        self.assertEqual(denied.observations[0].message, "blocked by policy")
        allow_payload = json.loads(allow_client.messages[1][-1].content[0]["content"])
        deny_payload = json.loads(deny_client.messages[1][-1].content[0]["content"])
        self.assertEqual(allow_payload["hooks"][0]["event"], "PermissionRequest")
        self.assertEqual(deny_payload["hooks"][0]["event"], "PermissionRequest")


class PermissionRequestAuthorizationTests(unittest.TestCase):
    def _authorize(
        self,
        workspace,
        *,
        request: ApprovalRequest | None = None,
        handler=None,
        approval_handler=None,
        policy: str = "ask",
        permissions: ProjectPermissions = ProjectPermissions(),
    ):
        with patch(
            "vibeagent.agent_permissions.sandbox_auto_approval_reason",
            return_value=None,
        ):
            return authorize_tool_action(
                workspace,
                permissions,
                "Bash",
                _action(),
                1,
                approval_handler,
                policy,
                None,
                default_request=request,
                permission_request_handler=handler,
            )

    def test_runs_only_at_an_interactive_approval_boundary(self) -> None:
        hook = Mock(return_value=PermissionRequestHookOutcome(behavior="deny"))
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-hook-") as base:
            workspace = create_run_workspace(base)
            without_request = self._authorize(workspace, handler=hook)
            with patch(
                "vibeagent.agent_permissions.sandbox_auto_approval_reason",
                return_value="sandboxed",
            ):
                sandboxed = authorize_tool_action(
                    workspace,
                    ProjectPermissions(),
                    "Bash",
                    _action(),
                    1,
                    None,
                    "ask",
                    None,
                    default_request=_request(),
                    permission_request_handler=hook,
                )
            noninteractive = self._authorize(
                workspace,
                request=_request(),
                handler=hook,
                policy="deny",
            )

        self.assertTrue(without_request.allowed)
        self.assertTrue(sandboxed.allowed)
        self.assertFalse(noninteractive.allowed)
        hook.assert_not_called()

    def test_allow_and_deny_replace_the_user_prompt(self) -> None:
        approval = Mock(
            return_value=ApprovalDecision(approved=True, message="user approved")
        )
        hook_result = _result(handler_type="prompt")
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-hook-") as base:
            workspace = create_run_workspace(base)
            allowed = self._authorize(
                workspace,
                request=_request(),
                handler=lambda: PermissionRequestHookOutcome(
                    behavior="allow", results=(hook_result,)
                ),
                approval_handler=approval,
            )
            denied = self._authorize(
                workspace,
                request=_request(),
                handler=lambda: PermissionRequestHookOutcome(
                    behavior="deny",
                    message="blocked by policy",
                    results=(hook_result,),
                ),
                approval_handler=approval,
            )

        self.assertTrue(allowed.allowed)
        self.assertFalse(denied.allowed)
        self.assertEqual(denied.denial.message, "blocked by policy")
        self.assertEqual(allowed.hook_results, (hook_result,))
        self.assertEqual(denied.hook_results, (hook_result,))
        approval.assert_not_called()

    def test_project_deny_and_ask_rules_keep_priority(self) -> None:
        deny_hook = Mock(
            return_value=PermissionRequestHookOutcome(behavior="allow")
        )
        allow_hook = Mock(
            return_value=PermissionRequestHookOutcome(behavior="allow")
        )
        approval = Mock(
            return_value=ApprovalDecision(approved=True, message="user approved")
        )
        deny_rule = ProjectPermissionRule(
            effect="deny",
            tool="Bash",
            specifier=None,
            raw="Bash",
            source="test",
        )
        ask_rule = ProjectPermissionRule(
            effect="ask",
            tool="Bash",
            specifier=None,
            raw="Bash",
            source="test",
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-hook-") as base:
            workspace = create_run_workspace(base)
            denied = self._authorize(
                workspace,
                request=_request(),
                handler=deny_hook,
                approval_handler=approval,
                permissions=ProjectPermissions(rules=(deny_rule,)),
            )
            asked = self._authorize(
                workspace,
                request=_request(),
                handler=allow_hook,
                approval_handler=approval,
                permissions=ProjectPermissions(rules=(ask_rule,)),
            )

        self.assertFalse(denied.allowed)
        self.assertTrue(asked.allowed)
        deny_hook.assert_not_called()
        allow_hook.assert_called_once_with()
        approval.assert_called_once_with(_request())

    def test_hook_failure_falls_back_to_user_approval_and_is_audited(self) -> None:
        approval = Mock(
            return_value=ApprovalDecision(approved=True, message="user approved")
        )

        def fail_hook() -> PermissionRequestHookOutcome:
            raise RuntimeError("service unavailable")

        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-hook-") as base:
            workspace = create_run_workspace(base)
            authorization = self._authorize(
                workspace,
                request=_request(),
                handler=fail_hook,
                approval_handler=approval,
            )
            events = [
                json.loads(line)
                for line in Path(workspace.session_dir, "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        self.assertTrue(authorization.allowed)
        approval.assert_called_once_with(_request())
        self.assertIn("permission_request_hook_error", [event["type"] for event in events])


if __name__ == "__main__":
    unittest.main()
