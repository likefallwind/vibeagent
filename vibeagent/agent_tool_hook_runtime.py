from __future__ import annotations

from collections.abc import Callable

from .agent_action_targets import build_action_target
from .agent_hook_execution import run_project_hook
from .agent_hook_prompt import HookModelRuntime
from .agent_hook_results import HookRunResult
from .types import AgentLogger, ApprovalHandler, ApprovalPolicy, Observation
from .workspace_core import RunWorkspace
from .workspace_hook_types import ProjectHook
from .workspace_permissions import ProjectPermissions


ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]


def run_tool_hook_handler(
    workspace: RunWorkspace,
    hook: ProjectHook,
    tool_name: str,
    action: object,
    tool_input: dict[str, object],
    tool_use_id: str | None,
    iteration: int,
    hook_index: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    execute_action_safely_func: ExecuteActionSafely,
    permissions: ProjectPermissions,
    hook_model_runtime: HookModelRuntime | None,
) -> HookRunResult:
    hook_input: dict[str, object] = {
        "session_id": workspace.run_id,
        "transcript_path": str(workspace.session_dir / "events.jsonl"),
        "cwd": str(workspace.root),
        "permission_mode": {
            "allow": "bypassPermissions",
            "ask": "default",
            "deny": "dontAsk",
            "dontAsk": "dontAsk",
            "plan": "plan",
        }[approval_policy],
        "hook_event_name": hook.event,
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    if tool_use_id is not None:
        hook_input["tool_use_id"] = tool_use_id
    return run_project_hook(
        workspace,
        hook,
        target=tool_name,
        hook_input=hook_input,
        environment={
            **hook.environment,
            "VIBEAGENT_TOOL_NAME": tool_name,
            "VIBEAGENT_TOOL_TARGET": build_action_target(action),
        },
        iteration=iteration,
        hook_index=hook_index,
        command_timeout_ms=command_timeout_ms,
        logger=logger,
        approval_handler=approval_handler,
        approval_policy=approval_policy,
        execute_action_safely_func=execute_action_safely_func,
        permissions=permissions,
        hook_model_runtime=hook_model_runtime,
    )


__all__ = ["run_tool_hook_handler"]
