from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .agent_action_targets import build_action_target
from .agent_hook_results import HookRunResult
from .agent_permission_request_hooks import PermissionRequestHookOutcome
from .agent_runtime_utils import append_session_event
from .permission_update_runtime import (
    PermissionUpdateApplication,
    apply_permission_updates,
)
from .redaction import redact_sensitive_text
from .types import (
    ApprovalDecision,
    ApprovalDeniedObservation,
    ApprovalPolicy,
    ApprovalRequest,
)
from .workspace_core import RunWorkspace
from .workspace_permissions import (
    PermissionRuleMatch,
    ProjectPermissions,
    match_project_permission,
    safe_permission_rule_text,
)


PermissionRequestHandler = Callable[[], PermissionRequestHookOutcome]
ApplyPermissionUpdatedInput = Callable[[dict[str, object]], object]
BuildUpdatedApprovalRequest = Callable[[object], ApprovalRequest | None]


@dataclass(frozen=True)
class PermissionRequestResolution:
    terminal_allowed: bool | None
    workspace: RunWorkspace
    permissions: ProjectPermissions
    approval_policy: ApprovalPolicy
    action: object
    request: ApprovalRequest
    rule_match: PermissionRuleMatch | None
    decision: ApprovalDecision | None = None
    denial: ApprovalDeniedObservation | None = None
    hook_results: tuple[HookRunResult, ...] = ()
    effective_input: dict[str, object] | None = None
    application: PermissionUpdateApplication | None = None
    interrupt: bool = False


def resolve_permission_request(
    workspace: RunWorkspace,
    permissions: ProjectPermissions,
    approval_policy: ApprovalPolicy,
    tool_name: str,
    action: object,
    request: ApprovalRequest,
    rule_match: PermissionRuleMatch | None,
    iteration: int,
    handler: PermissionRequestHandler,
    apply_updated_input: ApplyPermissionUpdatedInput | None,
    build_updated_request: BuildUpdatedApprovalRequest | None,
) -> PermissionRequestResolution:
    original = _resolution(
        workspace,
        permissions,
        approval_policy,
        action,
        request,
        rule_match,
    )
    try:
        outcome = handler()
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
        return original
    if outcome.behavior is not None:
        append_session_event(
            workspace.session_dir,
            "permission_request_hook_decision",
            {
                "iteration": iteration,
                "tool": tool_name,
                "behavior": outcome.behavior,
                "message": outcome.message,
            },
        )
    if outcome.behavior == "deny":
        message = outcome.message or "Denied by PermissionRequest hook."
        decision = ApprovalDecision(approved=False, message=message)
        return PermissionRequestResolution(
            False,
            workspace,
            permissions,
            approval_policy,
            action,
            request,
            rule_match,
            decision=decision,
            denial=_denial(tool_name, action, message),
            hook_results=outcome.results,
            interrupt=outcome.interrupt,
        )
    if outcome.behavior != "allow":
        return PermissionRequestResolution(
            None,
            workspace,
            permissions,
            approval_policy,
            action,
            request,
            rule_match,
            hook_results=outcome.results,
        )
    effective_action = action
    effective_request = request
    try:
        if outcome.updated_input is not None:
            if apply_updated_input is None:
                raise ValueError(
                    "PermissionRequest updatedInput is unsupported for this tool call."
                )
            effective_action = apply_updated_input(outcome.updated_input)
            effective_request = (
                build_updated_request(effective_action)
                if build_updated_request is not None
                else request
            ) or ApprovalRequest(
                action_type=tool_name,
                target=build_action_target(effective_action),
                risk="PermissionRequest updated this tool call.",
            )
        application = apply_permission_updates(
            workspace,
            permissions,
            approval_policy,
            outcome.updated_permissions,
            bypass_available=(
                approval_policy == "allow" or workspace.bypass_permissions_available
            ),
        )
    except (OSError, TypeError, ValueError) as error:
        append_session_event(
            workspace.session_dir,
            "permission_request_update_rejected",
            {
                "iteration": iteration,
                "tool": tool_name,
                "message": redact_sensitive_text(str(error)),
            },
        )
        return PermissionRequestResolution(
            None,
            workspace,
            permissions,
            approval_policy,
            action,
            request,
            rule_match,
            hook_results=outcome.results,
        )
    effective_rule = match_project_permission(
        application.permissions,
        tool_name,
        effective_action,
    )
    _record_updates(
        workspace,
        application,
        tool_name=tool_name,
        iteration=iteration,
        updated_input=outcome.updated_input is not None,
    )
    if effective_rule is not None and effective_rule.effect == "deny":
        visible_rule = safe_permission_rule_text(effective_rule.rule)
        message = (
            "PermissionRequest updated tool input is denied by permission "
            f"rule {visible_rule} from {effective_rule.rule.source}."
        )
        decision = ApprovalDecision(False, message)
        return PermissionRequestResolution(
            False,
            application.workspace,
            application.permissions,
            application.approval_policy,
            effective_action,
            effective_request,
            effective_rule,
            decision=decision,
            denial=_denial(tool_name, effective_action, message),
            hook_results=outcome.results,
            effective_input=outcome.updated_input,
            application=application,
        )
    if effective_rule is not None and effective_rule.effect == "ask":
        if effective_request is None:
            effective_request = ApprovalRequest(
                action_type=tool_name,
                target=build_action_target(effective_action),
                risk="A permission rule requires confirmation for the PermissionRequest-updated tool call.",
            )
        return PermissionRequestResolution(
            None,
            application.workspace,
            application.permissions,
            application.approval_policy,
            effective_action,
            effective_request,
            effective_rule,
            hook_results=outcome.results,
            effective_input=outcome.updated_input,
            application=application,
        )
    if _approval_must_repeat(effective_action):
        return PermissionRequestResolution(
            None,
            application.workspace,
            application.permissions,
            application.approval_policy,
            effective_action,
            effective_request,
            effective_rule,
            hook_results=outcome.results,
            effective_input=outcome.updated_input,
            application=application,
        )
    decision = ApprovalDecision(
        approved=True,
        message="Approved by PermissionRequest hook.",
    )
    return PermissionRequestResolution(
        True,
        application.workspace,
        application.permissions,
        application.approval_policy,
        effective_action,
        effective_request,
        effective_rule,
        decision=decision,
        hook_results=outcome.results,
        effective_input=outcome.updated_input,
        application=application,
    )


def _resolution(
    workspace: RunWorkspace,
    permissions: ProjectPermissions,
    approval_policy: ApprovalPolicy,
    action: object,
    request: ApprovalRequest,
    rule_match: PermissionRuleMatch | None,
) -> PermissionRequestResolution:
    return PermissionRequestResolution(
        None,
        workspace,
        permissions,
        approval_policy,
        action,
        request,
        rule_match,
    )


def _record_updates(
    workspace: RunWorkspace,
    application: PermissionUpdateApplication,
    *,
    tool_name: str,
    iteration: int,
    updated_input: bool,
) -> None:
    append_session_event(
        workspace.session_dir,
        "permission_request_updates_applied",
        {
            "iteration": iteration,
            "tool": tool_name,
            "updated_input": updated_input,
            "updated_permissions": len(application.applied),
            "approval_policy": application.approval_policy,
            "additional_directories": [
                str(path) for path in application.workspace.additional_roots
            ],
            "warnings": list(application.warnings),
        },
    )
    if application.workspace.additional_roots != workspace.additional_roots:
        append_session_event(
            workspace.session_dir,
            "additional_directories_updated",
            {
                "additional_directories": [
                    str(path) for path in application.workspace.additional_roots
                ],
                "source": "PermissionRequest",
                "iteration": iteration,
            },
        )


def _denial(
    tool_name: str,
    action: object,
    message: str,
) -> ApprovalDeniedObservation:
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


__all__ = [
    "ApplyPermissionUpdatedInput",
    "BuildUpdatedApprovalRequest",
    "PermissionRequestHandler",
    "PermissionRequestResolution",
    "resolve_permission_request",
]
