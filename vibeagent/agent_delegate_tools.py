from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .auto_mode import AutoModeRuntime
from .actions import ActionParseError, parse_tool_action
from .action_tool_aliases import tool_name_is_restricted
from .agent_execution_support import (
    create_auto_checkpoint_before_action,
    execute_action_safely,
    should_auto_checkpoint_before_action,
)
from .agent_hooks import HookRunResult
from .agent_hook_prompt import HookModelRuntime
from .agent_delegate_policy import (
    CODE_DELEGATE_EXCLUDED_TOOL_NAMES,
    DELEGATE_TOOL_NAMES,
    NESTED_DELEGATE_TOOL_NAMES,
    READ_ONLY_CLAUDE_DELEGATE_TOOL_NAMES,
)
from .agent_parallel_safety import is_parallel_safe_action
from .agent_team_runtime import TEAM_COORDINATION_TOOL_NAMES
from .agent_runtime_utils import tool_error_observation
from .agent_tool_execution import execute_parsed_tool_action
from .agent_task_lifecycle_hooks import run_task_lifecycle_hooks
from .agent_tool_registry import (
    ToolVisibilityPolicy,
    activate_agent_tool_names,
    agent_tool_definitions,
    background_task_activation_names,
    initial_agent_tool_names,
    mcp_tools_activation_names,
    prepare_action_for_policy,
    prepare_action_for_visibility,
    tool_search_activation_names,
)
from .tool_definitions import AGENT_TOOL_DEFINITIONS
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    FinishAction,
    Observation,
    TaskStep,
    ToolErrorObservation,
)
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks
from .workspace_permissions import ProjectPermissions


DELEGATE_TOOL_DEFINITIONS = [
    tool
    for tool in AGENT_TOOL_DEFINITIONS
    if (
        tool["name"] in DELEGATE_TOOL_NAMES
        or tool["name"] in READ_ONLY_CLAUDE_DELEGATE_TOOL_NAMES
        or tool["name"] == "finish"
    )
]
DELEGATE_TOOL_DEFINITION_NAMES = frozenset(
    str(tool["name"]) for tool in DELEGATE_TOOL_DEFINITIONS
)


@dataclass(frozen=True)
class DelegateToolCallExecution:
    observation: Observation | None
    finish_action: FinishAction | None
    auto_checkpoint_attempted: bool
    hook_results: tuple[HookRunResult, ...] = ()
    halt_turn_message: str | None = None


def code_delegate_initial_tool_names(
    approval_policy: ApprovalPolicy,
    allowed_tool_names: frozenset[str] | None = None,
    disallowed_tool_names: frozenset[str] = frozenset(),
    enabled_tool_names: frozenset[str] = frozenset(),
) -> set[str]:
    policy = ToolVisibilityPolicy(
        approval_policy=approval_policy,
        excluded_names=CODE_DELEGATE_EXCLUDED_TOOL_NAMES | disallowed_tool_names,
    )
    source_names = (
        allowed_tool_names
        if allowed_tool_names is not None
        else initial_agent_tool_names() | set(enabled_tool_names)
    )
    return {name for name in source_names if not name.startswith("mcp__") and policy.allows(name)}


def delegate_tool_definitions(
    mode: str,
    active_tool_names: set[str],
    approval_policy: ApprovalPolicy,
    allowed_tool_names: frozenset[str] | None = None,
    disallowed_tool_names: frozenset[str] = frozenset(),
    nested_delegation_allowed: bool = False,
    team_member: bool = False,
) -> list[dict[str, object]]:
    nested_names = NESTED_DELEGATE_TOOL_NAMES if nested_delegation_allowed else frozenset()
    coordination_names = TEAM_COORDINATION_TOOL_NAMES if team_member else frozenset()
    if mode in {"explore", "plan"}:
        return [
            tool
            for tool in AGENT_TOOL_DEFINITIONS
            if str(tool["name"]) in (
                DELEGATE_TOOL_DEFINITION_NAMES | nested_names | coordination_names
            )
            and not tool_name_is_restricted(disallowed_tool_names, str(tool["name"]))
            and (
                str(tool["name"]) in coordination_names
                or allowed_tool_names is None
                or str(tool["name"]) in allowed_tool_names
            )
        ]
    definitions = agent_tool_definitions(
        active_tool_names,
        approval_policy,
        CODE_DELEGATE_EXCLUDED_TOOL_NAMES
        | disallowed_tool_names
        | (frozenset() if nested_delegation_allowed else NESTED_DELEGATE_TOOL_NAMES),
    )
    if team_member:
        existing = {str(tool["name"]) for tool in definitions}
        definitions.extend(
            tool
            for tool in AGENT_TOOL_DEFINITIONS
            if str(tool["name"]) in coordination_names
            and str(tool["name"]) not in existing
            and not tool_name_is_restricted(disallowed_tool_names, str(tool["name"]))
        )
    if allowed_tool_names is None:
        return definitions
    return [
        tool
        for tool in definitions
        if str(tool["name"]) in coordination_names or str(tool["name"]) in allowed_tool_names
    ]


def execute_delegate_tool_call(
    workspace: RunWorkspace,
    *,
    mode: str,
    tool_name: str,
    tool_input: object,
    active_tool_names: set[str],
    observations: list[Observation],
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    auto_checkpoint_attempted: bool,
    allowed_tool_names: frozenset[str] | None = None,
    disallowed_tool_names: frozenset[str] = frozenset(),
    hooks: ProjectHooks = ProjectHooks(),
    permissions: ProjectPermissions = ProjectPermissions(),
    special_action_handler: Callable[[object], Observation | None] | None = None,
    coordination_tool_names: frozenset[str] = frozenset(),
    tool_id: str | None = None,
    hook_model_runtime: HookModelRuntime | None = None,
    auto_mode_runtime: AutoModeRuntime | None = None,
    teammate_name: str | None = None,
) -> DelegateToolCallExecution:
    halt_turn_message: str | None = None
    try:
        def prepare_tool_input(candidate_input: dict[str, object]) -> object:
            candidate = prepare_action_for_policy(
                parse_tool_action(tool_name, candidate_input), approval_policy
            )
            candidate = prepare_action_for_visibility(
                candidate,
                CODE_DELEGATE_EXCLUDED_TOOL_NAMES | disallowed_tool_names,
                allowed_tool_names,
            )
            coordination_allowed = (
                tool_name in coordination_tool_names
                and _profile_allows_tool_call(
                    tool_name,
                    candidate,
                    None,
                    disallowed_tool_names,
                )
            )
            if not coordination_allowed and not _profile_allows_tool_call(
                tool_name, candidate, allowed_tool_names, disallowed_tool_names
            ):
                raise ActionParseError(
                    "Subagent tool is blocked by the selected project agent profile or active tool restrictions.",
                    str(candidate_input),
                )
            return candidate

        raw_tool_input = tool_input if isinstance(tool_input, dict) else {}
        parsed = prepare_tool_input(raw_tool_input)
        if mode == "code":
            activate_agent_tool_names(
                active_tool_names,
                _allowed_requested_names(
                    [str(getattr(parsed, "type", tool_name))],
                    allowed_tool_names,
                    disallowed_tool_names,
                ),
                approval_policy,
                CODE_DELEGATE_EXCLUDED_TOOL_NAMES | disallowed_tool_names,
            )
        if isinstance(parsed, FinishAction):
            return DelegateToolCallExecution(None, parsed, auto_checkpoint_attempted)
        task_hook_results: tuple[HookRunResult, ...] = ()
        if special_action_handler is not None and teammate_name is not None:
            task_lifecycle = run_task_lifecycle_hooks(
                workspace,
                parsed,
                teammate_name=teammate_name,
                iteration=iteration,
                command_timeout_ms=command_timeout_ms,
                logger=logger,
                approval_handler=approval_handler,
                approval_policy=approval_policy,
                execute_action_safely_func=execute_action_safely,
                hooks=hooks,
                permissions=permissions,
                hook_model_runtime=hook_model_runtime,
            )
            if task_lifecycle.blocking_message is not None:
                observation = ToolErrorObservation(
                    kind="tool_error",
                    tool=f"hook:{task_lifecycle.results[-1].event}:{tool_name}",
                    message=task_lifecycle.blocking_message,
                )
                observations.append(observation)
                return DelegateToolCallExecution(
                    observation,
                    None,
                    auto_checkpoint_attempted,
                    task_lifecycle.results,
                    task_lifecycle.halt_turn_message,
                )
            task_hook_results = task_lifecycle.results
        if special_action_handler is not None:
            special_observation = special_action_handler(parsed)
            if special_observation is not None:
                observations.append(special_observation)
                if mode == "code":
                    activate_agent_tool_names(
                        active_tool_names,
                        _activation_names_for_observation(special_observation),
                        approval_policy,
                        CODE_DELEGATE_EXCLUDED_TOOL_NAMES | disallowed_tool_names,
                    )
                return DelegateToolCallExecution(
                    special_observation,
                    None,
                    auto_checkpoint_attempted,
                    task_hook_results,
                )
        (
            observation,
            checkpoint_attempted,
            hook_results,
            halt_turn_message,
        ) = execute_delegate_action(
            workspace,
            mode=mode,
            tool_name=tool_name,
            parsed=parsed,
            observations=observations,
            steps=steps,
            iteration=iteration,
            command_timeout_ms=command_timeout_ms,
            logger=logger,
            approval_handler=approval_handler,
            approval_policy=approval_policy,
            auto_checkpoint_attempted=auto_checkpoint_attempted,
            hooks=hooks,
            permissions=permissions,
            tool_input=raw_tool_input,
            apply_updated_input=prepare_tool_input,
            tool_use_id=tool_id,
            hook_model_runtime=hook_model_runtime,
            auto_mode_runtime=auto_mode_runtime,
        )
    except ActionParseError as error:
        observation = tool_error_observation(tool_name, error)
        checkpoint_attempted = auto_checkpoint_attempted
        hook_results = ()
    except Exception as error:
        observation = ToolErrorObservation(
            kind="tool_error",
            tool=tool_name or "unknown",
            message=f"Subagent tool execution failed: {error}",
        )
        checkpoint_attempted = auto_checkpoint_attempted
        hook_results = ()

    observations.append(observation)
    if mode == "code":
        activate_agent_tool_names(
            active_tool_names,
            _allowed_requested_names(
                _activation_names_for_observation(observation),
                allowed_tool_names,
                disallowed_tool_names,
            ),
            approval_policy,
            CODE_DELEGATE_EXCLUDED_TOOL_NAMES | disallowed_tool_names,
        )
    return DelegateToolCallExecution(
        observation,
        None,
        checkpoint_attempted,
        hook_results,
        halt_turn_message,
    )


def _profile_allows_tool_call(
    tool_name: str,
    parsed: object,
    allowed_tool_names: frozenset[str] | None,
    disallowed_tool_names: frozenset[str],
) -> bool:
    action_type = getattr(parsed, "type", None)
    candidates = [tool_name]
    if isinstance(action_type, str):
        candidates.append(action_type)
    if any(tool_name_is_restricted(disallowed_tool_names, candidate) for candidate in candidates):
        return False
    if allowed_tool_names is None:
        return True
    return tool_name in allowed_tool_names or (isinstance(action_type, str) and action_type in allowed_tool_names)


def _allowed_requested_names(
    requested_names: list[str],
    allowed_tool_names: frozenset[str] | None,
    disallowed_tool_names: frozenset[str] = frozenset(),
) -> list[str]:
    return [
        name
        for name in requested_names
        if not tool_name_is_restricted(disallowed_tool_names, name)
        and (allowed_tool_names is None or name in allowed_tool_names)
    ]


def _activation_names_for_observation(observation: Observation) -> list[str]:
    return (
        tool_search_activation_names(observation)
        + mcp_tools_activation_names(observation)
        + background_task_activation_names(observation)
    )


def execute_delegate_action(
    workspace: RunWorkspace,
    *,
    mode: str,
    tool_name: str,
    parsed: object,
    observations: list[Observation],
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    auto_checkpoint_attempted: bool,
    hooks: ProjectHooks,
    permissions: ProjectPermissions,
    tool_input: dict[str, object] | None = None,
    apply_updated_input: Callable[[dict[str, object]], object] | None = None,
    tool_use_id: str | None = None,
    hook_model_runtime: HookModelRuntime | None = None,
    auto_mode_runtime: AutoModeRuntime | None = None,
) -> tuple[Observation, bool, tuple[HookRunResult, ...], str | None]:
    action_type = getattr(parsed, "type", None)
    if mode in {"explore", "plan"}:
        coordination_tool = tool_name in TEAM_COORDINATION_TOOL_NAMES
        allowed_read_only_tool = (
            tool_name in DELEGATE_TOOL_NAMES
            or tool_name in READ_ONLY_CLAUDE_DELEGATE_TOOL_NAMES
            or action_type in DELEGATE_TOOL_NAMES
            or coordination_tool
        )
        if not allowed_read_only_tool or (
            not coordination_tool and not is_parallel_safe_action(parsed)
        ):
            return (
                ToolErrorObservation(
                    kind="tool_error",
                    tool=tool_name or "unknown",
                    message="Subagent tool is not allowed in read-only delegation mode.",
                ),
                auto_checkpoint_attempted,
                (),
                None,
            )
        return _execute_delegate_with_tool_layer(
            workspace,
            parsed,
            observations=observations,
            steps=steps,
            iteration=iteration,
            command_timeout_ms=command_timeout_ms,
            logger=logger,
            approval_handler=approval_handler,
            tool_name=tool_name,
            auto_checkpoint_attempted=auto_checkpoint_attempted,
            approval_policy=approval_policy,
            hooks=hooks,
            permissions=permissions,
            tool_input=tool_input,
            apply_updated_input=apply_updated_input,
            tool_use_id=tool_use_id,
            hook_model_runtime=hook_model_runtime,
            auto_mode_runtime=auto_mode_runtime,
        )
    if tool_name in CODE_DELEGATE_EXCLUDED_TOOL_NAMES or action_type in CODE_DELEGATE_EXCLUDED_TOOL_NAMES:
        return (
            ToolErrorObservation(
                kind="tool_error",
                tool=tool_name or "unknown",
                message="Subagent tool is not allowed because subagents cannot ask the user, update the parent plan, or switch the parent workspace.",
            ),
            auto_checkpoint_attempted,
            (),
            None,
        )

    return _execute_delegate_with_tool_layer(
        workspace,
        parsed,
        observations=observations,
        steps=steps,
        iteration=iteration,
        command_timeout_ms=command_timeout_ms,
        logger=logger,
        approval_handler=approval_handler,
        tool_name=tool_name,
        auto_checkpoint_attempted=auto_checkpoint_attempted,
        approval_policy=approval_policy,
        hooks=hooks,
        permissions=permissions,
        tool_input=tool_input,
        apply_updated_input=apply_updated_input,
        tool_use_id=tool_use_id,
        hook_model_runtime=hook_model_runtime,
        auto_mode_runtime=auto_mode_runtime,
    )


def _execute_delegate_with_tool_layer(
    workspace: RunWorkspace,
    parsed: object,
    *,
    observations: list[Observation],
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    tool_name: str,
    auto_checkpoint_attempted: bool,
    approval_policy: ApprovalPolicy,
    hooks: ProjectHooks,
    permissions: ProjectPermissions,
    tool_input: dict[str, object] | None = None,
    apply_updated_input: Callable[[dict[str, object]], object] | None = None,
    tool_use_id: str | None = None,
    hook_model_runtime: HookModelRuntime | None = None,
    auto_mode_runtime: AutoModeRuntime | None = None,
) -> tuple[Observation, bool, tuple[HookRunResult, ...], str | None]:
    execution = execute_parsed_tool_action(
        workspace,
        parsed,
        observations,
        steps,
        iteration,
        command_timeout_ms,
        logger,
        approval_handler,
        tool_name,
        auto_checkpoint_attempted,
        execute_action_safely,
        should_auto_checkpoint_before_action,
        create_auto_checkpoint_before_action,
        approval_policy,
        hooks,
        permissions,
        tool_input,
        apply_updated_input,
        False,
        tool_use_id,
        hook_model_runtime,
        auto_mode_runtime,
    )
    if execution.auto_checkpoint is not None:
        observations.append(execution.auto_checkpoint)
    observations.extend(execution.additional_observations)
    return (
        execution.observation,
        execution.auto_checkpoint_attempted,
        execution.hook_results,
        execution.halt_turn_message,
    )
