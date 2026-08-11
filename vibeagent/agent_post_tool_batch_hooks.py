from __future__ import annotations

from .agent_hook_prompt import HookModelRuntime
from .agent_lifecycle_hooks import LifecycleHookResult, run_lifecycle_hooks
from .types import AgentLogger, ApprovalHandler, ApprovalPolicy, ContentBlock
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks
from .workspace_permissions import ProjectPermissions


def run_post_tool_batch_hooks(
    workspace: RunWorkspace,
    tool_calls: list[ContentBlock],
    tool_results: list[ContentBlock],
    *,
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    execute_action_safely_func,
    hooks: ProjectHooks,
    permissions: ProjectPermissions,
    hook_model_runtime: HookModelRuntime | None,
) -> LifecycleHookResult:
    if not any(hook.event == "PostToolBatch" for hook in hooks.hooks):
        return LifecycleHookResult()
    responses = {
        str(
            result.get("tool_use_id")
            or result.get("tool_call_id")
            or result.get("id")
            or ""
        ): result.get("content", "")
        for result in tool_results
        if result.get("type") == "tool_result"
    }
    batch = []
    for call in tool_calls:
        tool_use_id = str(call.get("id") or "")
        batch.append(
            {
                "tool_name": str(call.get("name") or ""),
                "tool_input": call.get("input") if isinstance(call.get("input"), dict) else {},
                "tool_use_id": tool_use_id,
                "tool_response": responses.get(tool_use_id, ""),
            }
        )
    return run_lifecycle_hooks(
        workspace,
        hooks,
        "PostToolBatch",
        "",
        {"tool_calls": batch},
        iteration=iteration,
        command_timeout_ms=command_timeout_ms,
        logger=logger,
        approval_handler=approval_handler,
        approval_policy=approval_policy,
        execute_action_safely_func=execute_action_safely_func,
        permissions=permissions,
        hook_model_runtime=hook_model_runtime,
    )


def append_batch_context(tool_results: list[ContentBlock], result: LifecycleHookResult) -> None:
    if result.contexts:
        tool_results.append(
            {
                "type": "text",
                "text": "PostToolBatch hook context:\n" + "\n\n".join(result.contexts),
            }
        )


__all__ = ["append_batch_context", "run_post_tool_batch_hooks"]
