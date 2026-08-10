from __future__ import annotations

from collections.abc import Callable

from .agent_action_targets import build_action_target
from .agent_hook_execution import run_project_hook_command
from .agent_hook_results import (
    HookBatchResult,
    HookRunResult,
    HookWrappedToolResult,
    hook_command_with_context as _hook_command_with_context,
    hook_failure_observation as _hook_failure_observation,
    hook_result_from_observation as _hook_result_from_observation,
)
from .agent_permissions import authorize_tool_action
from .agent_observation_utils import observation_failed
from .agent_runtime_utils import to_jsonable
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
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
ExecuteTool = Callable[[], Observation]

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
) -> HookWrappedToolResult:
    authorization = authorize_tool_action(
        workspace,
        permissions,
        tool_name,
        action,
        iteration,
        approval_handler,
        approval_policy,
        logger,
    )
    if not authorization.allowed:
        assert authorization.denial is not None
        return HookWrappedToolResult(observation=authorization.denial)

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
    )
    if pre_hooks.blocking_message is not None:
        return HookWrappedToolResult(
            observation=pre_hooks.failures[-1],
            hook_results=pre_hooks.results,
        )

    observation = execute_tool()
    post_event: HookEvent = (
        "PostToolUseFailure" if observation_failed(observation) else "PostToolUse"
    )
    post_hooks = run_tool_hooks(
        workspace,
        config,
        post_event,
        tool_name,
        action,
        iteration,
        command_timeout_ms,
        logger,
        approval_handler,
        approval_policy,
        execute_action_safely_func,
        permissions,
    )
    return HookWrappedToolResult(
        observation=observation,
        hook_results=pre_hooks.results + post_hooks.results,
        additional_observations=post_hooks.failures,
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
) -> HookBatchResult:
    if config.error is not None:
        message = f"Project hook configuration is invalid: {config.error}"
        failure = _hook_failure_observation(event, tool_name, message)
        return HookBatchResult(
            blocking_message=message if event == "PreToolUse" else None,
            failures=(failure,),
        )

    hooks = matching_project_hooks(config, event, tool_name, action)
    if not hooks:
        return HookBatchResult()
    results: list[HookRunResult] = []
    failures: list[ToolErrorObservation] = []
    for index, hook in enumerate(hooks, start=1):
        result = _run_one_hook(
            workspace,
            hook,
            tool_name,
            action,
            iteration,
            index,
            command_timeout_ms,
            logger,
            approval_handler,
            approval_policy,
            execute_action_safely_func,
            permissions,
        )
        results.append(result)
        if not result.ok:
            failure = _hook_failure_observation(event, tool_name, result.message)
            failures.append(failure)
            if event == "PreToolUse":
                return HookBatchResult(
                    results=tuple(results),
                    blocking_message=result.message,
                    failures=tuple(failures),
                )
    return HookBatchResult(results=tuple(results), failures=tuple(failures))


def _run_one_hook(
    workspace: RunWorkspace,
    hook: ProjectHook,
    tool_name: str,
    action: object,
    iteration: int,
    hook_index: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    execute_action_safely_func: ExecuteActionSafely,
    permissions: ProjectPermissions,
) -> HookRunResult:
    return run_project_hook_command(
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
                "plan": "plan",
            }[approval_policy],
            "hook_event_name": hook.event,
            "tool_name": tool_name,
            "tool_input": to_jsonable(action),
        },
        environment={
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
    )
