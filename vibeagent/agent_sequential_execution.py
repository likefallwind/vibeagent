from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

from .actions import ActionParseError, parse_tool_action
from .agent_runtime_utils import append_session_event, tool_error_observation
from .agent_hook_updated_input import apply_hook_supplied_answers
from .agent_hook_prompt import HookModelRuntime
from .permission_update_runtime import PermissionUpdateApplication
from .agent_lifecycle_hooks import run_instruction_loaded_hooks
from .agent_special_tools import execute_special_tool_action
from .session_working_directory import prepare_action_shell_cwd
from .agent_tool_execution import (
    CreateAutoCheckpoint,
    ExecuteActionSafely,
    ShouldAutoCheckpoint,
    execute_parsed_tool_action,
)
from .agent_tool_results import ToolObservationContext, record_tool_observation
from .agent_tool_registry import prepare_action_for_policy, prepare_action_for_visibility
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    AskUserAction,
    ChatClient,
    ContentBlock,
    DelegateTaskAction,
    Observation,
    PlanItem,
    SendMessageAction,
    TaskStep,
    UserInputHandler,
)
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks
from .workspace_permissions import ProjectPermissions


@dataclass(frozen=True)
class SequentialToolCallResult:
    tool_result: ContentBlock | None
    observation: Observation
    plan: list[PlanItem]
    auto_checkpoint_attempted: bool
    deferred_tool_use: dict[str, object] | None = None
    halt_turn_message: str | None = None
    permission_application: PermissionUpdateApplication | None = None


def execute_sequential_tool_call(
    workspace: RunWorkspace,
    block: ContentBlock,
    client: ChatClient,
    *,
    observations: list[Observation],
    steps: list[TaskStep],
    plan: list[PlanItem],
    active_tool_names: set[str],
    iteration: int,
    max_output_tokens: int,
    model_retries: int,
    model_retry_delay_ms: int,
    model_timeout_ms: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    user_input_handler: UserInputHandler | None,
    hooks: ProjectHooks,
    permissions: ProjectPermissions,
    auto_checkpoint_attempted: bool,
    execute_action_safely_func: ExecuteActionSafely,
    should_auto_checkpoint_before_action_func: ShouldAutoCheckpoint,
    create_auto_checkpoint_before_action_func: CreateAutoCheckpoint,
    tool_call_allowed: Callable[[str, object], bool] | None = None,
    excluded_tool_names: frozenset[str] = frozenset(),
    allowed_tool_names: frozenset[str] | None = None,
    tool_ceiling_names: frozenset[str] | None = None,
    defer_tool_calls: bool = False,
    hook_model_runtime: HookModelRuntime | None = None,
) -> SequentialToolCallResult:
    tool_id = str(block.get("id") or "")
    tool_name = str(block.get("name") or "")
    tool_input = block.get("input") or {}
    append_session_event(
        workspace.session_dir,
        "tool_call",
        {"iteration": iteration, "id": tool_id, "name": tool_name, "input": tool_input},
    )
    hook_results: tuple[object, ...] = ()
    additional_observations: tuple[Observation, ...] = ()
    checkpoint_attempted = auto_checkpoint_attempted
    halt_turn_message: str | None = None
    permission_application: PermissionUpdateApplication | None = None

    try:
        def prepare_tool_input(candidate_input: dict[str, object]) -> object:
            candidate = prepare_action_for_policy(
                parse_tool_action(tool_name, candidate_input), approval_policy
            )
            candidate = prepare_action_for_visibility(
                candidate,
                excluded_tool_names,
                allowed_tool_names,
            )
            candidate = prepare_action_shell_cwd(workspace, candidate)
            if tool_call_allowed is not None and not tool_call_allowed(
                tool_name, candidate
            ):
                raise ActionParseError(
                    "Tool call is blocked by the selected main agent profile or active tool restrictions.",
                    str(candidate_input),
                )
            return candidate

        def prepare_hook_input(candidate_input: dict[str, object]) -> object:
            parsed_input = dict(candidate_input)
            has_supplied_answers = "answers" in parsed_input
            supplied_answers = parsed_input.pop("answers", None)
            candidate = prepare_tool_input(parsed_input)
            if not has_supplied_answers:
                return candidate
            return apply_hook_supplied_answers(
                candidate,
                supplied_answers,
                str(candidate_input),
            )

        raw_tool_input = tool_input if isinstance(tool_input, dict) else {}
        action = prepare_tool_input(raw_tool_input)
        if isinstance(action, (AskUserAction, DelegateTaskAction, SendMessageAction)):
            wrapped = execute_special_tool_action(
                workspace,
                action,
                client,
                steps=steps,
                observations=observations,
                iteration=iteration,
                tool_name=tool_name,
                max_output_tokens=max_output_tokens,
                model_retries=model_retries,
                model_retry_delay_ms=model_retry_delay_ms,
                model_timeout_ms=model_timeout_ms,
                command_timeout_ms=command_timeout_ms,
                logger=logger,
                approval_handler=approval_handler,
                approval_policy=approval_policy,
                user_input_handler=user_input_handler,
                hooks=hooks,
                permissions=permissions,
                execute_action_safely_func=execute_action_safely_func,
                tool_ceiling_names=tool_ceiling_names,
                tool_input=raw_tool_input,
                apply_updated_input=prepare_hook_input,
                defer_tool_calls=defer_tool_calls,
                tool_use_id=tool_id,
                hook_model_runtime=hook_model_runtime,
            )
            observation = wrapped.observation
            hook_results = wrapped.hook_results
            additional_observations = wrapped.additional_observations
            deferred = wrapped.deferred
            halt_turn_message = wrapped.halt_turn_message
            permission_application = wrapped.permission_application
        else:
            execution = execute_parsed_tool_action(
                workspace,
                action,
                observations,
                steps,
                iteration,
                command_timeout_ms,
                logger,
                approval_handler,
                tool_name,
                checkpoint_attempted,
                execute_action_safely_func,
                should_auto_checkpoint_before_action_func,
                create_auto_checkpoint_before_action_func,
                approval_policy,
                hooks,
                permissions,
                raw_tool_input,
                prepare_hook_input,
                defer_tool_calls,
                tool_id,
                hook_model_runtime,
            )
            observation = execution.observation
            hook_results = execution.hook_results
            additional_observations = execution.additional_observations
            checkpoint_attempted = execution.auto_checkpoint_attempted
            deferred = execution.deferred
            halt_turn_message = execution.halt_turn_message
            permission_application = execution.permission_application
            if execution.auto_checkpoint is not None:
                observations.append(execution.auto_checkpoint)
        if deferred:
            return SequentialToolCallResult(
                tool_result=None,
                observation=observation,
                plan=plan,
                auto_checkpoint_attempted=checkpoint_attempted,
                deferred_tool_use={
                    "id": tool_id,
                    "name": tool_name,
                    "input": raw_tool_input,
                },
                halt_turn_message=halt_turn_message,
                permission_application=permission_application,
            )
        if observation.kind in {
            "update_plan",
            "exit_plan_mode",
            "plan_mode_feedback",
        } or observation.kind in {
            "task_create",
            "task_get",
            "task_list",
            "task_update",
        }:
            plan = list(observation.plan)
    except ActionParseError as error:
        observation = tool_error_observation(tool_name, error)

    tool_result = record_tool_observation(
        workspace,
        tool_id=tool_id,
        tool_name=tool_name,
        observation=observation,
        additional_observations=additional_observations,
        hook_results=hook_results,
        context=ToolObservationContext(
            observations=observations,
            active_tool_names=active_tool_names,
            iteration=iteration,
            approval_policy=approval_policy,
            logger=logger,
            excluded_tool_names=excluded_tool_names,
            allowed_tool_names=allowed_tool_names,
            instruction_hook_runner=lambda context: run_instruction_loaded_hooks(
                workspace,
                hooks,
                context,
                iteration=iteration,
                command_timeout_ms=command_timeout_ms,
                logger=logger,
                approval_handler=approval_handler,
                approval_policy=approval_policy,
                execute_action_safely_func=execute_action_safely_func,
                permissions=permissions,
                hook_model_runtime=hook_model_runtime,
            ),
        ),
    )
    return SequentialToolCallResult(
        tool_result=tool_result,
        observation=observation,
        plan=plan,
        auto_checkpoint_attempted=checkpoint_attempted,
        halt_turn_message=halt_turn_message,
        permission_application=permission_application,
    )
