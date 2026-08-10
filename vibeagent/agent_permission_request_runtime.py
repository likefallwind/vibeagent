from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from .agent_hook_prompt import HookModelRuntime
from .agent_hook_results import HookRunResult
from .agent_permission_request_hooks import (
    PermissionRequestHookOutcome,
    PermissionRequestHookOutputError,
    merge_permission_request_behavior,
    parse_permission_request_hook_output,
)
from .agent_runtime_utils import append_session_event
from .agent_tool_hook_runtime import run_tool_hook_handler
from .types import AgentLogger, ApprovalHandler, ApprovalPolicy, Observation
from .workspace_core import RunWorkspace
from .workspace_hook_types import ProjectHooks
from .workspace_hooks import matching_project_hooks
from .workspace_permissions import ProjectPermissions


ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]


def run_permission_request_hooks(
    workspace: RunWorkspace,
    config: ProjectHooks,
    tool_name: str,
    action: object,
    tool_input: dict[str, object],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    execute_action_safely_func: ExecuteActionSafely,
    permissions: ProjectPermissions,
    hook_model_runtime: HookModelRuntime | None = None,
) -> PermissionRequestHookOutcome:
    if config.error is not None:
        return PermissionRequestHookOutcome()
    hooks = matching_project_hooks(config, "PermissionRequest", tool_name, action)
    if not hooks:
        return PermissionRequestHookOutcome()
    results: list[HookRunResult] = []
    behavior = None
    message: str | None = None
    updated_input: dict[str, object] | None = None
    updated_permissions: list[dict[str, object]] = []
    interrupt = False
    for index, hook in enumerate(hooks, start=1):
        result = run_tool_hook_handler(
            workspace,
            hook,
            tool_name,
            action,
            tool_input,
            None,
            iteration,
            index,
            command_timeout_ms,
            logger,
            approval_handler,
            approval_policy,
            execute_action_safely_func,
            permissions,
            hook_model_runtime,
        )
        candidate = None
        candidate_message: str | None = None
        candidate_input: dict[str, object] | None = None
        candidate_permissions: tuple[dict[str, object], ...] = ()
        candidate_interrupt = False
        if result.handler_type in {"prompt", "agent"}:
            if result.status == "blocked":
                result = replace(
                    result,
                    non_blocking_error=True,
                    message=(
                        f"{result.message} Prompt and agent PermissionRequest "
                        "decisions do not grant or deny permission."
                    ),
                )
        elif result.exit_code == 2:
            candidate = "deny"
            candidate_message = result.stderr.strip() or result.message
        elif result.ok:
            try:
                parsed = parse_permission_request_hook_output(result)
                candidate = parsed.behavior
                candidate_message = parsed.message
                candidate_input = parsed.updated_input
                candidate_permissions = parsed.updated_permissions
                candidate_interrupt = parsed.interrupt
            except (PermissionRequestHookOutputError, ValueError, TypeError) as error:
                result = replace(
                    result,
                    status="failed",
                    ok=False,
                    message=f"PermissionRequest hook output was rejected: {error}",
                    non_blocking_error=True,
                )
                append_session_event(
                    workspace.session_dir,
                    "permission_request_hook_output_rejected",
                    {
                        "iteration": iteration,
                        "index": index,
                        "tool": tool_name,
                        "source": hook.source,
                        "message": result.message,
                    },
                )
        elif not result.non_blocking_error:
            result = replace(
                result,
                non_blocking_error=True,
                message=f"{result.message} The PermissionRequest hook error is non-blocking.",
            )
        merged = merge_permission_request_behavior(behavior, candidate)
        if merged != behavior:
            message = candidate_message
        if candidate == "allow":
            if candidate_input is not None:
                updated_input = candidate_input
            updated_permissions.extend(candidate_permissions)
        elif candidate == "deny":
            interrupt = interrupt or candidate_interrupt
        behavior = merged
        results.append(result)
    if behavior == "deny":
        updated_input = None
        updated_permissions = []
    return PermissionRequestHookOutcome(
        behavior=behavior,
        message=message,
        results=tuple(results),
        updated_input=updated_input,
        updated_permissions=tuple(updated_permissions),
        interrupt=interrupt,
    )


__all__ = ["run_permission_request_hooks"]
