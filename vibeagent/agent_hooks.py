from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from .agent_action_targets import build_action_target
from .agent_hook_execution import run_project_hook
from .agent_hook_results import (
    HookBatchResult,
    HookRunResult,
    HookWrappedToolResult,
    hook_command_with_context as _hook_command_with_context,
    hook_failure_observation as _hook_failure_observation,
    hook_result_from_observation as _hook_result_from_observation,
)
from .agent_hook_prompt import HookModelRuntime
from .agent_permissions import authorize_tool_action
from .agent_pre_tool_hook_output import (
    PreToolHookOutputError,
    merge_pre_tool_decision,
    parse_pre_tool_hook_output,
)
from .agent_observation_utils import observation_failed
from .agent_runtime_utils import to_jsonable
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    ApprovalRequest,
    Observation,
    ToolErrorObservation,
)
from .workspace_core import RunWorkspace
from .workspace_hooks import (
    HookEvent,
    ProjectHook,
    ProjectHooks,
    matching_project_hooks,
)
from .workspace_permissions import ProjectPermissions


ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]
ExecuteTool = Callable[[object], Observation]
ApplyUpdatedInput = Callable[[dict[str, object]], object]

__all__ = [
    "HookBatchResult",
    "HookRunResult",
    "HookWrappedToolResult",
    "_hook_command_with_context",
    "_hook_failure_observation",
    "_hook_result_from_observation",
    "run_hooks_around_tool",
    "run_tool_hooks",
]


def run_hooks_around_tool(
    workspace: RunWorkspace,
    config: ProjectHooks,
    tool_name: str,
    action: object,
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    execute_action_safely_func: ExecuteActionSafely,
    execute_tool: ExecuteTool,
    permissions: ProjectPermissions = ProjectPermissions(),
    build_default_approval_request: Callable[[object], ApprovalRequest | None] | None = None,
    tool_input: dict[str, object] | None = None,
    apply_updated_input: ApplyUpdatedInput | None = None,
    finalize_action: Callable[[object], object] | None = None,
    defer_tool_calls: bool = False,
    tool_use_id: str | None = None,
    hook_model_runtime: HookModelRuntime | None = None,
) -> HookWrappedToolResult:
    pre_hooks = run_tool_hooks(
        workspace,
        config,
        "PreToolUse",
        tool_name,
        action,
        iteration,
        command_timeout_ms,
        logger,
        approval_handler,
        approval_policy,
        execute_action_safely_func,
        permissions,
        tool_input=tool_input,
        apply_updated_input=apply_updated_input,
        tool_use_id=tool_use_id,
        hook_model_runtime=hook_model_runtime,
    )
    if pre_hooks.blocking_message is not None:
        return HookWrappedToolResult(
            observation=pre_hooks.failures[-1],
            hook_results=pre_hooks.results,
            deferred=(
                defer_tool_calls and pre_hooks.permission_decision == "defer"
            ),
            halt_turn_message=pre_hooks.halt_turn_message,
        )
    effective_action = pre_hooks.effective_action or action
    if finalize_action is not None:
        effective_action = finalize_action(effective_action)
    authorization = authorize_tool_action(
        workspace,
        permissions,
        tool_name,
        effective_action,
        iteration,
        approval_handler,
        approval_policy,
        logger,
        default_request=(
            build_default_approval_request(effective_action)
            if build_default_approval_request is not None
            else None
        ),
        hook_permission_decision=pre_hooks.permission_decision,
        hook_permission_reason=pre_hooks.permission_reason,
    )
    if not authorization.allowed:
        assert authorization.denial is not None
        return HookWrappedToolResult(
            observation=authorization.denial,
            hook_results=pre_hooks.results,
        )

    observation = execute_tool(effective_action)
    post_event: HookEvent = (
        "PostToolUseFailure" if observation_failed(observation) else "PostToolUse"
    )
    post_hooks = run_tool_hooks(
        workspace,
        config,
        post_event,
        tool_name,
        effective_action,
        iteration,
        command_timeout_ms,
        logger,
        approval_handler,
        approval_policy,
        execute_action_safely_func,
        permissions,
        tool_input=pre_hooks.effective_input,
        tool_use_id=tool_use_id,
        hook_model_runtime=hook_model_runtime,
    )
    return HookWrappedToolResult(
        observation=observation,
        hook_results=pre_hooks.results + post_hooks.results,
        additional_observations=post_hooks.failures,
        halt_turn_message=post_hooks.halt_turn_message,
    )


def run_tool_hooks(
    workspace: RunWorkspace,
    config: ProjectHooks,
    event: HookEvent,
    tool_name: str,
    action: object,
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    execute_action_safely_func: ExecuteActionSafely,
    permissions: ProjectPermissions = ProjectPermissions(),
    *,
    tool_input: dict[str, object] | None = None,
    apply_updated_input: ApplyUpdatedInput | None = None,
    tool_use_id: str | None = None,
    hook_model_runtime: HookModelRuntime | None = None,
) -> HookBatchResult:
    if config.error is not None:
        message = f"Workspace hook configuration is invalid: {config.error}"
        failure = _hook_failure_observation(event, tool_name, message)
        return HookBatchResult(
            blocking_message=message if event == "PreToolUse" else None,
            failures=(failure,),
        )

    hooks = matching_project_hooks(config, event, tool_name, action)
    if not hooks:
        return HookBatchResult(
            effective_action=action if event == "PreToolUse" else None,
            effective_input=tool_input if event == "PreToolUse" else None,
        )
    results: list[HookRunResult] = []
    failures: list[ToolErrorObservation] = []
    current_action = action
    current_input = tool_input if tool_input is not None else _action_input(action)
    permission_decision = None
    permission_reason: str | None = None
    halt_turn_message: str | None = None
    for index, hook in enumerate(hooks, start=1):
        result = _run_one_hook(
            workspace,
            hook,
            tool_name,
            current_action,
            current_input,
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
        )
        if result.ok and event == "PreToolUse":
            try:
                output = parse_pre_tool_hook_output(result)
                updated = False
                if output.updated_input is not None:
                    if apply_updated_input is None:
                        raise PreToolHookOutputError(
                            "PreToolUse updatedInput is unsupported for this tool call."
                        )
                    current_action = apply_updated_input(output.updated_input)
                    current_input = output.updated_input
                    updated = True
                merged = merge_pre_tool_decision(
                    permission_decision, output.permission_decision
                )
                if merged != permission_decision:
                    permission_reason = output.permission_reason
                permission_decision = merged
                result = replace(
                    result,
                    permission_decision=output.permission_decision,
                    permission_reason=output.permission_reason,
                    updated_input_applied=updated,
                    additional_context=output.additional_context,
                )
            except (PreToolHookOutputError, ValueError, TypeError) as error:
                result = replace(
                    result,
                    status="failed",
                    ok=False,
                    message=f"PreToolUse hook output was rejected: {error}",
                )
        results.append(result)
        if not result.ok and not result.non_blocking_error:
            failure = _hook_failure_observation(event, tool_name, result.message)
            failures.append(failure)
            if (
                result.handler_type in {"prompt", "agent"}
                and result.status == "blocked"
                and not hook.continue_on_block
                and event in {"PreToolUse", "PostToolUse"}
            ):
                halt_turn_message = result.message
            if event == "PreToolUse":
                return HookBatchResult(
                    results=tuple(results),
                    blocking_message=result.message,
                    failures=tuple(failures),
                    effective_action=current_action,
                    effective_input=current_input,
                    permission_decision=permission_decision,
                    permission_reason=permission_reason,
                    halt_turn_message=halt_turn_message,
                )
    blocking_message: str | None = None
    if event == "PreToolUse" and permission_decision == "defer":
        blocking_message = (
            permission_reason
            or "PreToolUse hook deferred this tool call; deferred execution is not available in this session."
        )
        failures.append(_hook_failure_observation(event, tool_name, blocking_message))
    return HookBatchResult(
        results=tuple(results),
        blocking_message=blocking_message,
        failures=tuple(failures),
        effective_action=current_action if event == "PreToolUse" else None,
        effective_input=current_input if event == "PreToolUse" else None,
        permission_decision=permission_decision,
        permission_reason=permission_reason,
        halt_turn_message=halt_turn_message,
    )


def _run_one_hook(
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
    return run_project_hook(
        workspace,
        hook,
        target=tool_name,
        hook_input={
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
            "tool_use_id": tool_use_id,
        },
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


def _action_input(action: object) -> dict[str, object]:
    payload = to_jsonable(action)
    return payload if isinstance(payload, dict) else {}
