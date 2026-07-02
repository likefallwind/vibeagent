from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Callable
from dataclasses import dataclass
import json

from .actions import ActionParseError, execute_action, parse_tool_action
from .agent_action_descriptions import log_action
from .agent_parallel_safety import is_parallel_safe_action
from .agent_runtime_utils import append_session_event, find_repeated_list_observation, to_jsonable
from .agent_steps import complete_task_step, start_task_step
from .redaction import redact_jsonable_payload
from .types import AgentLogger, ContentBlock, ListFilesObservation, Observation, TaskStep, ToolErrorObservation
from .workspace_core import RunWorkspace


@dataclass(frozen=True)
class PreparedParallelToolCall:
    tool_id: str
    tool_name: str
    action: object
    step: TaskStep
    repeated_observation: Observation | None = None


def execute_parallel_tool_call_batch(
    workspace: RunWorkspace,
    tool_calls: list[ContentBlock],
    observations: list[Observation],
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    execute: Callable[[RunWorkspace, object, int], Observation] = execute_action,
) -> list[ContentBlock] | None:
    if len(tool_calls) < 2:
        return None

    parsed: list[tuple[str, str, object, object]] = []
    for block in tool_calls:
        tool_id = str(block.get("id") or "")
        tool_name = str(block.get("name") or "")
        tool_input = block.get("input") or {}
        try:
            action = parse_tool_action(tool_name, tool_input)
        except ActionParseError:
            return None
        if not is_parallel_safe_action(action):
            return None
        parsed.append((tool_id, tool_name, tool_input, action))

    prepared: list[PreparedParallelToolCall] = []
    for tool_id, tool_name, tool_input, action in parsed:
        append_session_event(
            workspace.session_dir,
            "tool_call",
            {"iteration": iteration, "id": tool_id, "name": tool_name, "input": tool_input},
        )
        step = start_task_step(workspace, steps, iteration, action, logger)
        log_action(logger, action)
        prepared.append(
            PreparedParallelToolCall(
                tool_id=tool_id,
                tool_name=tool_name,
                action=action,
                step=step,
                repeated_observation=find_repeated_list_observation(action, observations),
            )
        )

    batch_observations: list[Observation | None] = [None] * len(prepared)
    with ThreadPoolExecutor(max_workers=min(len(prepared), 8)) as executor:
        futures = {}
        for index, item in enumerate(prepared):
            if item.repeated_observation is not None:
                repeated = item.repeated_observation
                batch_observations[index] = ListFilesObservation(
                    kind="list_files",
                    path=repeated.path,
                    files=repeated.files,
                    total=repeated.total,
                    truncated=repeated.truncated,
                    message=(
                        f"Already listed {repeated.path}: {repeated.message} "
                        "Do not call list_files for this path again. Choose a useful tool call or answer directly."
                    ),
                )
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

    tool_results: list[ContentBlock] = []
    for item, observation in zip(prepared, batch_observations):
        if observation is None:
            observation = ToolErrorObservation(kind="tool_error", tool=item.tool_name or "unknown", message="Tool execution failed.")
        complete_task_step(workspace, item.step, observation, iteration, logger)
        observations.append(observation)
        result_payload = redact_jsonable_payload(to_jsonable(observation))
        append_session_event(
            workspace.session_dir,
            "tool_result",
            {"iteration": iteration, "id": item.tool_id, "name": item.tool_name, "result": result_payload},
        )
        tool_results.append(
            {
                "type": "tool_result",
                "tool_call_id": item.tool_id,
                "content": json.dumps(result_payload, ensure_ascii=False),
            }
        )
    return tool_results
