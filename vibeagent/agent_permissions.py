from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from .agent_action_targets import build_action_target
from .agent_approval import (
    request_approval,
    summarize_approval_decision,
    summarize_approval_request,
)
from .agent_hook_results import HookRunResult
from .agent_permission_request_hooks import PermissionRequestHookOutcome
from .agent_runtime_utils import append_session_event
from .command_sandbox import sandbox_auto_approval_reason
from .redaction import redact_sensitive_text
from .types import (
    AgentLogger,
    ApprovalDecision,
    ApprovalDeniedObservation,
    ApprovalHandler,
    ApprovalPolicy,
    ApprovalRequest,
    Observation,
)
from .workspace_core import RunWorkspace
from .workspace_permissions import (
    PermissionRuleMatch,
    ProjectPermissions,
    match_project_permission,
    safe_permission_rule_text,
)


@dataclass(frozen=True)
class ToolAuthorization:
    allowed: bool
    denial: Observation | None = None
    rule_match: PermissionRuleMatch | None = None
    decision: ApprovalDecision | None = None
    hook_results: tuple[HookRunResult, ...] = ()


PermissionRequestHandler = Callable[[], PermissionRequestHookOutcome]


def authorize_tool_action(
    workspace: RunWorkspace,
    permissions: ProjectPermissions,
    tool_name: str,
    action: object,
    iteration: int,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    logger: AgentLogger | None,
    default_request: ApprovalRequest | None = None,
    step: object | None = None,
    hook_permission_decision: Literal["allow", "deny", "ask", "defer"] | None = None,
    hook_permission_reason: str | None = None,
    permission_request_handler: PermissionRequestHandler | None = None,
) -> ToolAuthorization:
    if permissions.error is not None:
        message = f"Permission configuration is invalid: {redact_sensitive_text(permissions.error)}"
        append_session_event(
            workspace.session_dir,
            "permission_rule_evaluated",
            {
                "iteration": iteration,
                "tool": tool_name,
                "effect": "deny",
                "error": permissions.error,
            },
        )
        return ToolAuthorization(False, _denial(tool_name, action, message))

    if hook_permission_decision is not None:
        append_session_event(
            workspace.session_dir,
            "hook_permission_decision",
            {
                "iteration": iteration,
                "tool": tool_name,
                "decision": hook_permission_decision,
                "reason": hook_permission_reason,
            },
        )

    rule_match = match_project_permission(permissions, tool_name, action)
    if rule_match is not None:
        visible_rule = safe_permission_rule_text(rule_match.rule)
        append_session_event(
            workspace.session_dir,
            "permission_rule_evaluated",
            {
                "iteration": iteration,
                "tool": tool_name,
                "effect": rule_match.effect,
                "rule": rule_match.rule.raw,
                "source": rule_match.rule.source,
                "subjects": list(rule_match.subjects),
            },
        )
        if rule_match.effect == "deny":
            message = f"Denied by permission rule {visible_rule} from {rule_match.rule.source}."
            return ToolAuthorization(False, _denial(tool_name, action, message), rule_match=rule_match)
        if hook_permission_decision in {"deny", "defer"}:
            message = hook_permission_reason or (
                "PreToolUse hook denied this tool call."
                if hook_permission_decision == "deny"
                else "PreToolUse hook deferred this tool call."
            )
            return ToolAuthorization(False, _denial(tool_name, action, message), rule_match=rule_match)
        allow_can_skip_approval = (
            default_request is None
            or permissions.allow_rules_trusted
            or rule_match.rule.source in permissions.trusted_allow_sources
        ) and not _approval_must_repeat(action)
        if (
            rule_match.effect == "allow"
            and hook_permission_decision != "ask"
            and allow_can_skip_approval
            and not (
                default_request is not None and approval_policy in {"deny", "plan"}
            )
        ):
            decision = ApprovalDecision(
                approved=True,
                message=f"Approved by permission rule {visible_rule}.",
            )
            return ToolAuthorization(True, rule_match=rule_match, decision=decision)

    if hook_permission_decision in {"deny", "defer"}:
        message = hook_permission_reason or (
            "PreToolUse hook denied this tool call."
            if hook_permission_decision == "deny"
            else "PreToolUse hook deferred this tool call."
        )
        return ToolAuthorization(False, _denial(tool_name, action, message))

    if (
        hook_permission_decision == "allow"
        and (rule_match is None or rule_match.effect != "ask")
        and approval_policy not in {"deny", "dontAsk", "plan"}
        and not _approval_must_repeat(action)
    ):
        decision = ApprovalDecision(
            approved=True,
            message=hook_permission_reason or "Approved by PreToolUse hook.",
        )
        return ToolAuthorization(True, rule_match=rule_match, decision=decision)

    request = default_request
    if hook_permission_decision == "ask" and request is None:
        request = ApprovalRequest(
            action_type=tool_name,
            target=build_action_target(action),
            risk=hook_permission_reason or "A PreToolUse hook requires confirmation for this tool call.",
        )
    if rule_match is not None and rule_match.effect == "ask" and request is None:
        request = ApprovalRequest(
            action_type=tool_name,
            target=build_action_target(action),
            risk="A permission rule requires confirmation for this tool call.",
        )
    auto_approval_reason = sandbox_auto_approval_reason(workspace, action) if request is not None else None
    if (
        request is not None
        and auto_approval_reason is not None
        and approval_policy not in {"deny", "dontAsk", "plan"}
        and (rule_match is None or rule_match.effect != "ask")
        and hook_permission_decision != "ask"
    ):
        decision = ApprovalDecision(approved=True, message=auto_approval_reason)
        append_session_event(
            workspace.session_dir,
            "sandbox_auto_approved",
            {
                "iteration": iteration,
                "step": step,
                "tool": tool_name,
                "request": request,
                "decision": decision,
            },
        )
        if logger:
            logger("sandbox auto-approved", summarize_approval_decision(request, decision))
        return ToolAuthorization(True, rule_match=rule_match, decision=decision)
    permission_hook_results: tuple[HookRunResult, ...] = ()
    if (
        request is not None
        and approval_policy == "ask"
        and permission_request_handler is not None
    ):
        try:
            hook_outcome = permission_request_handler()
        except Exception as error:
            append_session_event(
                workspace.session_dir,
                "permission_request_hook_error",
                {
                    "iteration": iteration,
                    "tool": tool_name,
                    "message": redact_sensitive_text(str(error)),
                },
            )
        else:
            permission_hook_results = hook_outcome.results
            if hook_outcome.behavior is not None:
                append_session_event(
                    workspace.session_dir,
                    "permission_request_hook_decision",
                    {
                        "iteration": iteration,
                        "tool": tool_name,
                        "behavior": hook_outcome.behavior,
                        "message": hook_outcome.message,
                    },
                )
            if hook_outcome.behavior == "deny":
                message = hook_outcome.message or "Denied by PermissionRequest hook."
                decision = ApprovalDecision(approved=False, message=message)
                return ToolAuthorization(
                    False,
                    _denial(tool_name, action, message),
                    rule_match=rule_match,
                    decision=decision,
                    hook_results=permission_hook_results,
                )
            if (
                hook_outcome.behavior == "allow"
                and (rule_match is None or rule_match.effect != "ask")
                and not _approval_must_repeat(action)
            ):
                decision = ApprovalDecision(
                    approved=True,
                    message=hook_outcome.message or "Approved by PermissionRequest hook.",
                )
                return ToolAuthorization(
                    True,
                    rule_match=rule_match,
                    decision=decision,
                    hook_results=permission_hook_results,
                )
    if request is None:
        return ToolAuthorization(
            True,
            rule_match=rule_match,
            hook_results=permission_hook_results,
        )

    if approval_policy != "dontAsk":
        append_session_event(
            workspace.session_dir,
            "approval_requested",
            {"iteration": iteration, "step": step, "request": request, "permission_rule": _rule_payload(rule_match)},
        )
        if logger:
            logger("approval required", summarize_approval_request(request))
    if approval_policy == "plan" and request.action_type != "exit_plan_mode":
        decision = ApprovalDecision(
            approved=False,
            message=f"Denied because Plan mode is read-only: {request.action_type}.",
        )
    elif approval_policy == "deny":
        decision = ApprovalDecision(
            approved=False,
            message=f"Denied by session policy for {request.action_type}.",
        )
    elif approval_policy == "dontAsk":
        decision = ApprovalDecision(
            approved=False,
            message=f"Denied because dontAsk mode does not prompt for {request.action_type}.",
        )
    else:
        decision = request_approval(approval_handler, request)
    append_session_event(
        workspace.session_dir,
        "approval_decision",
        {"iteration": iteration, "step": step, "decision": decision, "permission_rule": _rule_payload(rule_match)},
    )
    if logger:
        status = "approval approved" if decision.approved else "approval denied"
        logger(status, summarize_approval_decision(request, decision))
    if decision.approved:
        return ToolAuthorization(
            True,
            rule_match=rule_match,
            decision=decision,
            hook_results=permission_hook_results,
        )
    return ToolAuthorization(
        False,
        ApprovalDeniedObservation(
            kind="approval_denied",
            action_type=request.action_type,
            target=request.target,
            message=decision.message or "Action was denied by approval policy.",
        ),
        rule_match=rule_match,
        decision=decision,
        hook_results=permission_hook_results,
    )


def _denial(tool_name: str, action: object, message: str) -> ApprovalDeniedObservation:
    return ApprovalDeniedObservation(
        kind="approval_denied",
        action_type=tool_name,
        target=build_action_target(action),
        message=message,
    )


def _approval_must_repeat(action: object) -> bool:
    return (
        getattr(action, "type", None) == "monitor"
        and getattr(action, "ws", None) is not None
    )


def _rule_payload(rule_match: PermissionRuleMatch | None) -> dict[str, str] | None:
    if rule_match is None:
        return None
    return {
        "effect": rule_match.effect,
        "rule": rule_match.rule.raw,
        "source": rule_match.rule.source,
    }
