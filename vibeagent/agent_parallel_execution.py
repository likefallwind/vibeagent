from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Callable
from dataclasses import dataclass

from .actions import ActionParseError, execute_action, parse_tool_action
from .agent_action_logging import log_action
from .agent_parallel_safety import is_parallel_safe_action
from .agent_runtime_utils import (
    append_session_event,
    build_repeated_list_observation,
    find_repeated_list_observation,
    list_files_action_path,
)
from .agent_steps import complete_task_step, start_task_step
from .agent_tool_results import record_tool_result_observation
from .agent_tool_registry import prepare_action_for_policy
from .types import ApprovalPolicy, AgentLogger, ContentBlock, ListFilesObservation, Observation, TaskStep, ToolErrorObservation
from .workspace_core import RunWorkspace


@dataclass(frozen=True)
class PreparedParallelToolCall:
    tool_id: str
    tool_name: str
    action: object
    step: TaskStep
    repeated_observation: ListFilesObservation | None = None
    duplicate_list_source_index: int | None = None


@dataclass(frozen=True)
class ParallelToolCallBatchResult:
    tool_results: list[ContentBlock]
    handled_count: int


def execute_parallel_tool_call_batch(
    workspace: RunWorkspace,
    tool_calls: list[ContentBlock],
    observations: list[Observation],
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    execute: Callable[[RunWorkspace, object, int], Observation] = execute_action,
    approval_policy: ApprovalPolicy = "ask",
) -> ParallelToolCallBatchResult | None:
    if len(tool_calls) < 2:
        return None

    parsed: list[tuple[str, str, object, object]] = []
    for block in tool_calls:
        tool_id = str(block.get("id") or "")
        tool_name = str(block.get("name") or "")
        tool_input = block.get("input") or {}
        try:
            action = prepare_action_for_policy(parse_tool_action(tool_name, tool_input), approval_policy)
        except ActionParseError:
            break
        if not is_parallel_safe_action(action):
            break
        parsed.append((tool_id, tool_name, tool_input, action))
    if len(parsed) < 2:
        return None

    prepared: list[PreparedParallelToolCall] = []
    list_files_source_indexes: dict[str, int] = {}
    for tool_id, tool_name, tool_input, action in parsed:
        append_session_event(
            workspace.session_dir,
            "tool_call",
            {"iteration": iteration, "id": tool_id, "name": tool_name, "input": tool_input},
        )
        step = start_task_step(workspace, steps, iteration, action, logger)
        log_action(logger, action)
        repeated_observation = find_repeated_list_observation(action, observations)
        list_path = list_files_action_path(action)
        duplicate_list_source_index = None
        if repeated_observation is None and list_path is not None:
            duplicate_list_source_index = list_files_source_indexes.get(list_path)
            list_files_source_indexes.setdefault(list_path, len(prepared))
        prepared.append(
            PreparedParallelToolCall(
                tool_id=tool_id,
                tool_name=tool_name,
                action=action,
                step=step,
                repeated_observation=repeated_observation,
                duplicate_list_source_index=duplicate_list_source_index,
            )
        )

    batch_observations: list[Observation | None] = [None] * len(prepared)
    with ThreadPoolExecutor(max_workers=min(len(prepared), 8)) as executor:
        futures = {}
        for index, item in enumerate(prepared):
            if item.repeated_observation is not None:
                batch_observations[index] = build_repeated_list_observation(item.repeated_observation)
                continue
            if item.duplicate_list_source_index is not None:
                continue
            futures[executor.submit(execute, workspace, item.action, command_timeout_ms)] = index

        for future in as_completed(futures):
            index = futures[future]
            item = prepared[index]
            try:
                batch_observations[index] = future.result()
            except Exception as error:  # pragma: no cover - defensive guard for unexpected tool bugs.
                batch_observations[index] = ToolErrorObservation(
                    kind="tool_error",
                    tool=item.tool_name or "unknown",
                    message=f"Tool execution failed: {error}",
                )

    for index, item in enumerate(prepared):
        if batch_observations[index] is not None or item.duplicate_list_source_index is None:
            continue
        source = batch_observations[item.duplicate_list_source_index]
        if isinstance(source, ListFilesObservation):
            batch_observations[index] = build_repeated_list_observation(source)

    tool_results: list[ContentBlock] = []
    for item, observation in zip(prepared, batch_observations):
        if observation is None:
            observation = ToolErrorObservation(kind="tool_error", tool=item.tool_name or "unknown", message="Tool execution failed.")
        complete_task_step(workspace, item.step, observation, iteration, logger)
        observations.append(observation)
        tool_results.append(record_tool_result_observation(
            workspace,
            tool_id=item.tool_id,
            tool_name=item.tool_name,
            observation=observation,
            iteration=iteration,
        ))
    return ParallelToolCallBatchResult(tool_results=tool_results, handled_count=len(prepared))
