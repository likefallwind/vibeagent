from __future__ import annotations

from dataclasses import dataclass

from .actions import ActionParseError, parse_tool_action
from .agent_execution_support import (
    create_auto_checkpoint_before_action,
    execute_action_safely,
    should_auto_checkpoint_before_action,
)
from .agent_hooks import HookRunResult
from .agent_delegate_policy import (
    CODE_DELEGATE_EXCLUDED_TOOL_NAMES,
    DELEGATE_TOOL_NAMES,
    READ_ONLY_CLAUDE_DELEGATE_TOOL_NAMES,
)
from .agent_parallel_safety import is_parallel_safe_action
from .agent_runtime_utils import tool_error_observation
from .agent_tool_execution import execute_parsed_tool_action
from .agent_tool_registry import (
    ToolVisibilityPolicy,
    activate_agent_tool_names,
    agent_tool_definitions,
    initial_agent_tool_names,
    mcp_tools_activation_names,
    prepare_action_for_policy,
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


@dataclass(frozen=True)
class DelegateToolCallExecution:
    observation: Observation | None
    finish_action: FinishAction | None
    auto_checkpoint_attempted: bool
    hook_results: tuple[HookRunResult, ...] = ()


def code_delegate_initial_tool_names(
    approval_policy: ApprovalPolicy,
    allowed_tool_names: frozenset[str] | None = None,
    disallowed_tool_names: frozenset[str] = frozenset(),
) -> set[str]:
    policy = ToolVisibilityPolicy(
        approval_policy=approval_policy,
        excluded_names=CODE_DELEGATE_EXCLUDED_TOOL_NAMES | disallowed_tool_names,
    )
    source_names = allowed_tool_names if allowed_tool_names is not None else initial_agent_tool_names()
    return {name for name in source_names if not name.startswith("mcp__") and policy.allows(name)}


def delegate_tool_definitions(
    mode: str,
    active_tool_names: set[str],
    approval_policy: ApprovalPolicy,
    allowed_tool_names: frozenset[str] | None = None,
    disallowed_tool_names: frozenset[str] = frozenset(),
) -> list[dict[str, object]]:
    if mode == "explore":
        return [
            tool
            for tool in DELEGATE_TOOL_DEFINITIONS
            if str(tool["name"]) not in disallowed_tool_names
            and (allowed_tool_names is None or str(tool["name"]) in allowed_tool_names)
        ]
    definitions = agent_tool_definitions(
        active_tool_names,
        approval_policy,
        CODE_DELEGATE_EXCLUDED_TOOL_NAMES | disallowed_tool_names,
    )
    if allowed_tool_names is None:
        return definitions
    return [tool for tool in definitions if str(tool["name"]) in allowed_tool_names]


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
) -> DelegateToolCallExecution:
    try:
        parsed = prepare_action_for_policy(parse_tool_action(tool_name, tool_input), approval_policy)
        if not _profile_allows_tool_call(
            tool_name,
            parsed,
            allowed_tool_names,
            disallowed_tool_names,
        ):
            observation = ToolErrorObservation(
                kind="tool_error",
                tool=tool_name or "unknown",
                message="Subagent tool is blocked by the selected project agent profile.",
            )
            observations.append(observation)
            return DelegateToolCallExecution(observation, None, auto_checkpoint_attempted)
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
        observation, checkpoint_attempted, hook_results = execute_delegate_action(
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
    return DelegateToolCallExecution(observation, None, checkpoint_attempted, hook_results)


def _profile_allows_tool_call(
    tool_name: str,
    parsed: object,
    allowed_tool_names: frozenset[str] | None,
    disallowed_tool_names: frozenset[str],
) -> bool:
    action_type = getattr(parsed, "type", None)
    if tool_name in disallowed_tool_names or (
        isinstance(action_type, str) and action_type in disallowed_tool_names
    ):
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
        if name not in disallowed_tool_names
        and (allowed_tool_names is None or name in allowed_tool_names)
    ]


def _activation_names_for_observation(observation: Observation) -> list[str]:
    return tool_search_activation_names(observation) + mcp_tools_activation_names(observation)


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
) -> tuple[Observation, bool, tuple[HookRunResult, ...]]:
    action_type = getattr(parsed, "type", None)
    if mode == "explore":
        allowed_read_only_tool = (
            tool_name in DELEGATE_TOOL_NAMES
            or tool_name in READ_ONLY_CLAUDE_DELEGATE_TOOL_NAMES
            or action_type in DELEGATE_TOOL_NAMES
        )
        if not allowed_read_only_tool or not is_parallel_safe_action(parsed):
            return (
                ToolErrorObservation(
                    kind="tool_error",
                    tool=tool_name or "unknown",
                    message="Subagent tool is not allowed in read-only delegation mode.",
                ),
                auto_checkpoint_attempted,
                (),
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
        )
    if tool_name in CODE_DELEGATE_EXCLUDED_TOOL_NAMES or action_type in CODE_DELEGATE_EXCLUDED_TOOL_NAMES:
        return (
            ToolErrorObservation(
                kind="tool_error",
                tool=tool_name or "unknown",
                message="Subagent tool is not allowed because coding subagents cannot ask the user, update the parent plan, or delegate again; they also cannot switch the parent workspace.",
            ),
            auto_checkpoint_attempted,
            (),
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
) -> tuple[Observation, bool, tuple[HookRunResult, ...]]:
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
    )
    if execution.auto_checkpoint is not None:
        observations.append(execution.auto_checkpoint)
    observations.extend(execution.additional_observations)
    return execution.observation, execution.auto_checkpoint_attempted, execution.hook_results
