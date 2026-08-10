from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from .agent_action_logging import log_action
from .agent_approval import build_approval_request
from .agent_approval_preview import attach_approval_preview
from .agent_hooks import ApplyUpdatedInput, HookBatchResult, HookRunResult, run_tool_hooks
from .agent_lifecycle_hooks import run_lifecycle_hooks
from .agent_observation_utils import observation_failed
from .agent_permissions import authorize_tool_action
from .agent_runtime_utils import append_session_event, build_repeated_list_observation, find_repeated_list_observation
from .agent_steps import complete_task_step, start_task_step
from .lsp_runtime import automatic_lsp_diagnostics
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    ExitPlanModeAction,
    Observation,
    PlanModeObservation,
    RunCommandObservation,
    TaskStep,
)
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks
from .workspace_permissions import ProjectPermissions


ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]
ShouldAutoCheckpoint = Callable[[RunWorkspace, object], bool]
CreateAutoCheckpoint = Callable[[RunWorkspace, object, list[TaskStep], int, int, AgentLogger | None], Observation | None]


@dataclass(frozen=True)
class ToolActionExecutionResult:
    observation: Observation
    auto_checkpoint: Observation | None
    auto_checkpoint_attempted: bool
    hook_results: tuple[HookRunResult, ...] = ()
    additional_observations: tuple[Observation, ...] = ()


def execute_parsed_tool_action(
    workspace: RunWorkspace,
    action: object,
    observations: list[Observation],
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    tool_name: str,
    auto_checkpoint_attempted: bool,
    execute_action_safely_func: ExecuteActionSafely,
    should_auto_checkpoint_before_action_func: ShouldAutoCheckpoint,
    create_auto_checkpoint_before_action_func: CreateAutoCheckpoint,
    approval_policy: ApprovalPolicy = "ask",
    hooks: ProjectHooks = ProjectHooks(),
    permissions: ProjectPermissions = ProjectPermissions(),
    tool_input: dict[str, object] | None = None,
    apply_updated_input: ApplyUpdatedInput | None = None,
) -> ToolActionExecutionResult:
    pre_hooks = run_tool_hooks(
        workspace,
        hooks,
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
    )
    action = pre_hooks.effective_action or action
    step = start_task_step(workspace, steps, iteration, action, logger)
    log_action(logger, action)

    observation = (
        pre_hooks.failures[-1]
        if pre_hooks.blocking_message is not None
        else _build_repeated_list_observation(action, observations)
    )
    auto_checkpoint: Observation | None = None
    checkpoint_attempted = auto_checkpoint_attempted
    hook_results: tuple[HookRunResult, ...] = pre_hooks.results
    additional_observations: tuple[Observation, ...] = ()
    if pre_hooks.blocking_message is not None:
        pass
    elif observation is not None:
        authorization = authorize_tool_action(
            workspace,
            permissions,
            tool_name,
            action,
            iteration,
            approval_handler,
            approval_policy,
            logger,
            step=step,
            hook_permission_decision=pre_hooks.permission_decision,
            hook_permission_reason=pre_hooks.permission_reason,
        )
        if not authorization.allowed:
            assert authorization.denial is not None
            observation = authorization.denial
    else:
        (
            observation,
            auto_checkpoint,
            checkpoint_attempted,
            hook_results,
            additional_observations,
        ) = _execute_non_repeated_action(
            workspace,
            action,
            observations,
            steps,
            step,
            iteration,
            command_timeout_ms,
            logger,
            approval_handler,
            tool_name,
            auto_checkpoint_attempted,
            execute_action_safely_func,
            should_auto_checkpoint_before_action_func,
            create_auto_checkpoint_before_action_func,
            approval_policy,
            hooks,
            permissions,
            pre_hooks,
        )

    complete_task_step(workspace, step, observation, iteration, logger)
    return ToolActionExecutionResult(
        observation=observation,
        auto_checkpoint=auto_checkpoint,
        auto_checkpoint_attempted=checkpoint_attempted,
        hook_results=hook_results,
        additional_observations=additional_observations,
    )


def _build_repeated_list_observation(action: object, observations: list[Observation]) -> Observation | None:
    repeated_list = find_repeated_list_observation(action, observations)
    if not repeated_list:
        return None
    return build_repeated_list_observation(repeated_list)


def _execute_non_repeated_action(
    workspace: RunWorkspace,
    action: object,
    observations: list[Observation],
    steps: list[TaskStep],
    step: TaskStep,
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    tool_name: str,
    auto_checkpoint_attempted: bool,
    execute_action_safely_func: ExecuteActionSafely,
    should_auto_checkpoint_before_action_func: ShouldAutoCheckpoint,
    create_auto_checkpoint_before_action_func: CreateAutoCheckpoint,
    approval_policy: ApprovalPolicy,
    hooks: ProjectHooks,
    permissions: ProjectPermissions,
    pre_hooks: HookBatchResult,
) -> tuple[Observation, Observation | None, bool, tuple[HookRunResult, ...], tuple[Observation, ...]]:
    approval_request = build_approval_request(action)
    if approval_request:
        approval_request = attach_approval_preview(approval_request, action, observations)
    authorization = authorize_tool_action(
        workspace,
        permissions,
        tool_name,
        action,
        iteration,
        approval_handler,
        approval_policy,
        logger,
        default_request=approval_request,
        step=step,
        hook_permission_decision=pre_hooks.permission_decision,
        hook_permission_reason=pre_hooks.permission_reason,
    )
    if not authorization.allowed:
        assert authorization.denial is not None
        if (
            isinstance(action, ExitPlanModeAction)
            and authorization.decision is not None
            and authorization.decision.permission_mode == "plan"
        ):
            return (
                PlanModeObservation(
                    kind="plan_mode_feedback",
                    plan=action.plan,
                    message=(
                        authorization.decision.message
                        or "Plan was not approved. Continue planning with the user's feedback."
                    ),
                    next_policy="plan",
                ),
                None,
                auto_checkpoint_attempted,
                pre_hooks.results,
                (),
            )
        return authorization.denial, None, auto_checkpoint_attempted, pre_hooks.results, ()

    auto_checkpoint, checkpoint_attempted = _maybe_create_auto_checkpoint(
        workspace,
        action,
        steps,
        iteration,
        command_timeout_ms,
        logger,
        auto_checkpoint_attempted,
        should_auto_checkpoint_before_action_func,
        create_auto_checkpoint_before_action_func,
    )
    observation = execute_action_safely_func(workspace, action, command_timeout_ms, tool_name)
    if (
        isinstance(action, ExitPlanModeAction)
        and isinstance(observation, PlanModeObservation)
        and authorization.decision is not None
    ):
        observation = replace(
            observation,
            next_policy=authorization.decision.permission_mode,
        )
    post_event = "PostToolUseFailure" if observation_failed(observation) else "PostToolUse"
    post_hooks = run_tool_hooks(
        workspace,
        hooks,
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
        tool_input=pre_hooks.effective_input,
    )
    cwd_hooks: tuple[HookRunResult, ...] = ()
    if (
        isinstance(observation, RunCommandObservation)
        and observation.result.previous_cwd is not None
        and observation.result.final_cwd is not None
        and observation.result.previous_cwd != observation.result.final_cwd
    ):
        cwd_lifecycle = run_lifecycle_hooks(
            workspace,
            hooks,
            "CwdChanged",
            "",
            {
                "old_cwd": observation.result.previous_cwd,
                "new_cwd": observation.result.final_cwd,
            },
            iteration=iteration,
            command_timeout_ms=command_timeout_ms,
            logger=logger,
            approval_handler=approval_handler,
            approval_policy=approval_policy,
            execute_action_safely_func=execute_action_safely_func,
            permissions=permissions,
        )
        cwd_hooks = cwd_lifecycle.results
    diagnostics = automatic_lsp_diagnostics(workspace, observation)
    return (
        observation,
        auto_checkpoint,
        checkpoint_attempted,
        pre_hooks.results + post_hooks.results + cwd_hooks,
        tuple(post_hooks.failures) + diagnostics,
    )


def _maybe_create_auto_checkpoint(
    workspace: RunWorkspace,
    action: object,
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    auto_checkpoint_attempted: bool,
    should_auto_checkpoint_before_action_func: ShouldAutoCheckpoint,
    create_auto_checkpoint_before_action_func: CreateAutoCheckpoint,
) -> tuple[Observation | None, bool]:
    if auto_checkpoint_attempted or not should_auto_checkpoint_before_action_func(workspace, action):
        return None, auto_checkpoint_attempted
    auto_checkpoint = create_auto_checkpoint_before_action_func(
        workspace,
        action,
        steps,
        iteration,
        command_timeout_ms,
        logger,
    )
    return auto_checkpoint, True
