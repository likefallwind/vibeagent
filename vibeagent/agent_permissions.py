from __future__ import annotations

from dataclasses import dataclass

from .agent_action_targets import build_action_target
from .agent_approval import (
    request_approval,
    summarize_approval_decision,
    summarize_approval_request,
)
from .agent_runtime_utils import append_session_event
from .command_sandbox import sandbox_auto_approval_reason
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
from .workspace_permissions import PermissionRuleMatch, ProjectPermissions, match_project_permission


@dataclass(frozen=True)
class ToolAuthorization:
    allowed: bool
    denial: Observation | None = None
    rule_match: PermissionRuleMatch | None = None
    decision: ApprovalDecision | None = None


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
) -> ToolAuthorization:
    if permissions.error is not None:
        message = f"Project permission configuration is invalid: {permissions.error}"
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

    rule_match = match_project_permission(permissions, tool_name, action)
    if rule_match is not None:
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
            message = f"Denied by project permission rule {rule_match.rule.raw} from {rule_match.rule.source}."
            return ToolAuthorization(False, _denial(tool_name, action, message), rule_match=rule_match)
        allow_can_skip_approval = (
            default_request is None
            or permissions.allow_rules_trusted
            or rule_match.rule.source in permissions.trusted_allow_sources
        )
        if rule_match.effect == "allow" and allow_can_skip_approval and not (
            default_request is not None and approval_policy in {"deny", "plan"}
        ):
            decision = ApprovalDecision(
                approved=True,
                message=f"Approved by project permission rule {rule_match.rule.raw}.",
            )
            return ToolAuthorization(True, rule_match=rule_match, decision=decision)

    request = default_request
    if rule_match is not None and rule_match.effect == "ask" and request is None:
        request = ApprovalRequest(
            action_type=tool_name,
            target=build_action_target(action),
            risk="A project permission rule requires confirmation for this tool call.",
        )
    auto_approval_reason = sandbox_auto_approval_reason(workspace, action) if request is not None else None
    if (
        request is not None
        and auto_approval_reason is not None
        and approval_policy not in {"deny", "plan"}
        and (rule_match is None or rule_match.effect != "ask")
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
    if request is None:
        return ToolAuthorization(True, rule_match=rule_match)

    append_session_event(
        workspace.session_dir,
        "approval_requested",
        {"iteration": iteration, "step": step, "request": request, "permission_rule": _rule_payload(rule_match)},
    )
    if logger:
        logger("approval required", summarize_approval_request(request))
    if approval_policy == "plan":
        decision = ApprovalDecision(
            approved=False,
            message=f"Denied because Plan mode is read-only: {request.action_type}.",
        )
    elif approval_policy == "deny":
        decision = ApprovalDecision(
            approved=False,
            message=f"Denied by session policy for {request.action_type}.",
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
        return ToolAuthorization(True, rule_match=rule_match, decision=decision)
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
    )


def _denial(tool_name: str, action: object, message: str) -> ApprovalDeniedObservation:
    return ApprovalDeniedObservation(
        kind="approval_denied",
        action_type=tool_name,
        target=build_action_target(action),
        message=message,
    )


def _rule_payload(rule_match: PermissionRuleMatch | None) -> dict[str, str] | None:
    if rule_match is None:
        return None
    return {
        "effect": rule_match.effect,
        "rule": rule_match.rule.raw,
        "source": rule_match.rule.source,
    }
