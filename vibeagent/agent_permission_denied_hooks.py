from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
import json

from .agent_hook_prompt import HookModelRuntime
from .agent_hook_results import HookRunResult
from .agent_runtime_utils import append_session_event
from .agent_tool_hook_runtime import run_tool_hook_handler
from .types import AgentLogger, ApprovalHandler, ApprovalPolicy, Observation
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks, matching_project_hooks
from .workspace_permissions import ProjectPermissions


ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]


@dataclass(frozen=True)
class PermissionDeniedHookOutcome:
    results: tuple[HookRunResult, ...] = ()
    retry: bool = False


def run_permission_denied_hooks(
    workspace: RunWorkspace,
    config: ProjectHooks,
    tool_name: str,
    action: object,
    tool_input: dict[str, object],
    tool_use_id: str | None,
    reason: str,
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    execute_action_safely_func: ExecuteActionSafely,
    permissions: ProjectPermissions,
    hook_model_runtime: HookModelRuntime | None,
) -> PermissionDeniedHookOutcome:
    hooks = matching_project_hooks(config, "PermissionDenied", tool_name, action)
    results: list[HookRunResult] = []
    retry = False
    for index, hook in enumerate(hooks, start=1):
        result = run_tool_hook_handler(
            workspace,
            hook,
            tool_name,
            action,
            tool_input,
            tool_use_id,
            iteration,
            index,
            command_timeout_ms,
            logger,
            approval_handler,
            approval_policy,
            execute_action_safely_func,
            permissions,
            hook_model_runtime,
            extra_input={"reason": reason},
        )
        try:
            retry = parse_permission_denied_retry(result) or retry
        except ValueError as error:
            result = replace(
                result,
                status="failed",
                ok=False,
                non_blocking_error=True,
                message=f"PermissionDenied hook output was rejected: {error}",
            )
            append_session_event(
                workspace.session_dir,
                "permission_denied_hook_output_rejected",
                {
                    "iteration": iteration,
                    "index": index,
                    "tool": tool_name,
                    "source": hook.source,
                    "message": result.message,
                },
            )
        results.append(result)
    return PermissionDeniedHookOutcome(tuple(results), retry)


def parse_permission_denied_retry(result: HookRunResult) -> bool:
    stdout = result.stdout.strip()
    if not result.ok or not stdout:
        return False
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as error:
        if stdout.startswith(("{", "[")):
            raise ValueError(f"invalid JSON: {error.msg}.") from error
        return False
    if not isinstance(payload, dict):
        raise ValueError("JSON output must be an object.")
    specific = payload.get("hookSpecificOutput")
    if specific is None:
        return False
    if not isinstance(specific, dict):
        raise ValueError("hookSpecificOutput must be an object.")
    if specific.get("hookEventName") != "PermissionDenied":
        raise ValueError("hookSpecificOutput.hookEventName must be PermissionDenied.")
    retry = specific.get("retry", False)
    if not isinstance(retry, bool):
        raise ValueError("hookSpecificOutput.retry must be a boolean.")
    return retry


__all__ = [
    "PermissionDeniedHookOutcome",
    "parse_permission_denied_retry",
    "run_permission_denied_hooks",
]
