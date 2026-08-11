from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from .auto_mode import AutoModeRuntime
from .agent_action_logging import log_action
from .agent_approval import build_approval_request
from .agent_approval_preview import attach_approval_preview
from .agent_hooks import (
    ApplyUpdatedInput,
    HookBatchResult,
    HookRunResult,
    run_permission_request_hooks,
    run_tool_hooks,
)
from .agent_hook_prompt import HookModelRuntime
from .agent_lifecycle_hooks import run_lifecycle_hooks
from .agent_observation_utils import observation_failed
from .agent_permission_denied_hooks import run_permission_denied_hooks
from .agent_permissions import authorize_tool_action
from .permission_update_runtime import PermissionUpdateApplication
from .agent_runtime_utils import (
    append_session_event,
    build_repeated_list_observation,
    find_repeated_list_observation,
    to_jsonable,
)
from .agent_steps import complete_task_step, start_task_step
from .agent_task_lifecycle_hooks import run_task_lifecycle_hooks
from .lsp_runtime import automatic_lsp_diagnostics
from .types import (
    AgentLogger,
    ApprovalRequest,
    ApprovalHandler,
    ApprovalPolicy,
    ExitPlanModeAction,
    Observation,
    PlanModeObservation,
    RunCommandObservation,
    TaskStep,
    ToolErrorObservation,
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
    deferred: bool = False
    halt_turn_message: str | None = None
    permission_application: PermissionUpdateApplication | None = None


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
    defer_tool_calls: bool = False,
    tool_use_id: str | None = None,
    hook_model_runtime: HookModelRuntime | None = None,
    auto_mode_runtime: AutoModeRuntime | None = None,
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
        tool_use_id=tool_use_id,
        hook_model_runtime=hook_model_runtime,
    )
    if defer_tool_calls and pre_hooks.permission_decision == "defer":
        return ToolActionExecutionResult(
            observation=pre_hooks.failures[-1],
            auto_checkpoint=None,
            auto_checkpoint_attempted=auto_checkpoint_attempted,
            hook_results=pre_hooks.results,
            deferred=True,
            halt_turn_message=pre_hooks.halt_turn_message,
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
    halt_turn_message = pre_hooks.halt_turn_message
    permission_application: PermissionUpdateApplication | None = None
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
            permission_request_handler=lambda: run_permission_request_hooks(
                workspace,
                hooks,
                tool_name,
                action,
                _permission_request_tool_input(action, pre_hooks.effective_input),
                iteration,
                command_timeout_ms,
                logger,
                approval_handler,
                approval_policy,
                execute_action_safely_func,
                permissions,
                hook_model_runtime,
            ),
            apply_permission_updated_input=apply_updated_input,
            build_updated_approval_request=lambda candidate: _approval_request_for_action(
                candidate, observations
            ),
            auto_mode_runtime=auto_mode_runtime,
            tool_input=tool_input,
            permission_denied_handler=lambda reason: _permission_denied_outcome(
                workspace,
                hooks,
                tool_name,
                action,
                tool_input or {},
                tool_use_id,
                reason,
                iteration,
                command_timeout_ms,
                logger,
                approval_handler,
                approval_policy,
                execute_action_safely_func,
                permissions,
                hook_model_runtime,
            ),
        )
        hook_results += authorization.hook_results
        permission_application = authorization.permission_application
        if not authorization.allowed:
            assert authorization.denial is not None
            observation = authorization.denial
            if authorization.interrupt:
                halt_turn_message = authorization.denial.message
    else:
        (
            observation,
            auto_checkpoint,
            checkpoint_attempted,
            hook_results,
            additional_observations,
            halt_turn_message,
            permission_application,
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
            tool_input,
            apply_updated_input,
            tool_use_id,
            hook_model_runtime,
            auto_mode_runtime,
        )

    complete_task_step(workspace, step, observation, iteration, logger)
    return ToolActionExecutionResult(
        observation=observation,
        auto_checkpoint=auto_checkpoint,
        auto_checkpoint_attempted=checkpoint_attempted,
        hook_results=hook_results,
        additional_observations=additional_observations,
        halt_turn_message=halt_turn_message,
        permission_application=permission_application,
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
    tool_input: dict[str, object] | None,
    apply_updated_input: ApplyUpdatedInput | None,
    tool_use_id: str | None,
    hook_model_runtime: HookModelRuntime | None,
    auto_mode_runtime: AutoModeRuntime | None,
) -> tuple[
    Observation,
    Observation | None,
    bool,
    tuple[HookRunResult, ...],
    tuple[Observation, ...],
    str | None,
    PermissionUpdateApplication | None,
]:
    approval_request = _approval_request_for_action(action, observations)
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
        permission_request_handler=lambda: run_permission_request_hooks(
            workspace,
            hooks,
            tool_name,
            action,
            _permission_request_tool_input(action, pre_hooks.effective_input),
            iteration,
            command_timeout_ms,
            logger,
            approval_handler,
            approval_policy,
            execute_action_safely_func,
            permissions,
            hook_model_runtime,
        ),
        apply_permission_updated_input=apply_updated_input,
        build_updated_approval_request=lambda candidate: _approval_request_for_action(
            candidate, observations
        ),
        auto_mode_runtime=auto_mode_runtime,
        tool_input=pre_hooks.effective_input or tool_input,
        permission_denied_handler=lambda reason: _permission_denied_outcome(
            workspace,
            hooks,
            tool_name,
            action,
            pre_hooks.effective_input or tool_input or {},
            tool_use_id,
            reason,
            iteration,
            command_timeout_ms,
            logger,
            approval_handler,
            approval_policy,
            execute_action_safely_func,
            permissions,
            hook_model_runtime,
        ),
    )
    authorization_hook_results = pre_hooks.results + authorization.hook_results
    application = authorization.permission_application
    effective_workspace = application.workspace if application is not None else workspace
    effective_permissions = application.permissions if application is not None else permissions
    effective_approval_policy = (
        application.approval_policy if application is not None else approval_policy
    )
    effective_action = authorization.effective_action or action
    effective_input = (
        authorization.effective_input
        if authorization.effective_input is not None
        else pre_hooks.effective_input
    )
    if not authorization.allowed:
        assert authorization.denial is not None
        if (
            isinstance(effective_action, ExitPlanModeAction)
            and authorization.decision is not None
            and authorization.decision.permission_mode == "plan"
        ):
            return (
                PlanModeObservation(
                    kind="plan_mode_feedback",
                    plan=effective_action.plan,
                    message=(
                        authorization.decision.message
                        or "Plan was not approved. Continue planning with the user's feedback."
                    ),
                    next_policy="plan",
                ),
                None,
                auto_checkpoint_attempted,
                authorization_hook_results,
                (),
                (
                    authorization.denial.message
                    if authorization.interrupt
                    else pre_hooks.halt_turn_message
                ),
                application,
            )
        return (
            authorization.denial,
            None,
            auto_checkpoint_attempted,
            authorization_hook_results,
            (),
            (
                authorization.denial.message
                if authorization.interrupt
                else pre_hooks.halt_turn_message
            ),
            application,
        )

    auto_checkpoint, checkpoint_attempted = _maybe_create_auto_checkpoint(
        effective_workspace,
        effective_action,
        steps,
        iteration,
        command_timeout_ms,
        logger,
        auto_checkpoint_attempted,
        should_auto_checkpoint_before_action_func,
        create_auto_checkpoint_before_action_func,
    )
    task_lifecycle = run_task_lifecycle_hooks(
        effective_workspace,
        effective_action,
        teammate_name=None,
        iteration=iteration,
        command_timeout_ms=command_timeout_ms,
        logger=logger,
        approval_handler=approval_handler,
        approval_policy=effective_approval_policy,
        execute_action_safely_func=execute_action_safely_func,
        hooks=hooks,
        permissions=effective_permissions,
        hook_model_runtime=hook_model_runtime,
    )
    if task_lifecycle.blocking_message is not None:
        observation = ToolErrorObservation(
            kind="tool_error",
            tool=f"hook:{task_lifecycle.results[-1].event}:{tool_name}",
            message=task_lifecycle.blocking_message,
        )
    else:
        observation = execute_action_safely_func(
            effective_workspace,
            effective_action,
            command_timeout_ms,
            tool_name,
        )
    if (
        isinstance(effective_action, ExitPlanModeAction)
        and isinstance(observation, PlanModeObservation)
        and authorization.decision is not None
    ):
        observation = replace(
            observation,
            next_policy=authorization.decision.permission_mode,
        )
    post_event = "PostToolUseFailure" if observation_failed(observation) else "PostToolUse"
    post_hooks = run_tool_hooks(
        effective_workspace,
        hooks,
        post_event,
        tool_name,
        effective_action,
        iteration,
        command_timeout_ms,
        logger,
        approval_handler,
        effective_approval_policy,
        execute_action_safely_func,
        effective_permissions,
        tool_input=effective_input,
        tool_use_id=tool_use_id,
        hook_model_runtime=hook_model_runtime,
    )
    cwd_hooks: tuple[HookRunResult, ...] = ()
    if (
        isinstance(observation, RunCommandObservation)
        and observation.result.previous_cwd is not None
        and observation.result.final_cwd is not None
        and observation.result.previous_cwd != observation.result.final_cwd
    ):
        cwd_lifecycle = run_lifecycle_hooks(
            effective_workspace,
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
            approval_policy=effective_approval_policy,
            execute_action_safely_func=execute_action_safely_func,
            permissions=effective_permissions,
            hook_model_runtime=hook_model_runtime,
        )
        cwd_hooks = cwd_lifecycle.results
    diagnostics = automatic_lsp_diagnostics(effective_workspace, observation)
    return (
        observation,
        auto_checkpoint,
        checkpoint_attempted,
        authorization_hook_results + task_lifecycle.results + post_hooks.results + cwd_hooks,
        tuple(post_hooks.failures) + diagnostics,
        task_lifecycle.halt_turn_message or post_hooks.halt_turn_message,
        application,
    )


def _approval_request_for_action(
    action: object,
    observations: list[Observation],
) -> ApprovalRequest | None:
    request = build_approval_request(action)
    return attach_approval_preview(request, action, observations) if request else None


def _permission_request_tool_input(
    action: object,
    effective_input: dict[str, object] | None,
) -> dict[str, object]:
    if effective_input is not None:
        return effective_input
    payload = to_jsonable(action)
    return payload if isinstance(payload, dict) else {}


def _permission_denied_outcome(
    workspace: RunWorkspace,
    hooks: ProjectHooks,
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
) -> tuple[tuple[HookRunResult, ...], bool]:
    outcome = run_permission_denied_hooks(
        workspace,
        hooks,
        tool_name,
        action,
        tool_input,
        tool_use_id,
        reason,
        iteration,
        command_timeout_ms,
        logger,
        approval_handler,
        approval_policy,
        execute_action_safely_func,
        permissions,
        hook_model_runtime,
    )
    return outcome.results, outcome.retry


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
