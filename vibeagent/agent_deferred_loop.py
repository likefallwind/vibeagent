from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .agent_result import AgentResult
from .agent_runtime_utils import append_session_event
from .agent_sequential_execution import SequentialToolCallResult
from .deferred_tool_state import (
    DeferredToolState,
    clear_deferred_tool_state,
    write_deferred_tool_state,
)
from .types import ContentBlock, Observation
from .workspace_core import RunWorkspace


@dataclass(frozen=True)
class DeferredResumeOutcome:
    result: AgentResult | None = None
    tool_results: tuple[ContentBlock, ...] = ()


def resume_deferred_tool_batch(
    workspace: RunWorkspace,
    state: DeferredToolState,
    available_tool_names: set[str],
    *,
    execute_block: Callable[[ContentBlock], SequentialToolCallResult],
    apply_result: Callable[[SequentialToolCallResult], Observation],
    on_resume: Callable[[dict[str, object], int], None],
    finish_deferred: Callable[[DeferredToolState, bool], AgentResult],
    finish_action: Callable[[Observation], AgentResult],
) -> DeferredResumeOutcome:
    pending = state.pending_tool_use
    if str(pending["name"]) not in available_tool_names:
        append_session_event(
            workspace.session_dir,
            "tool_deferred_unavailable",
            {"tool": pending},
        )
        return DeferredResumeOutcome(result=finish_deferred(state, True))

    on_resume(pending, len(state.completed_tool_results))
    tool_calls = state.tool_calls
    tool_results = list(state.completed_tool_results)
    for index in range(state.next_tool_index, len(tool_calls)):
        sequential = execute_block(tool_calls[index])
        if sequential.deferred_tool_use is not None:
            next_state = DeferredToolState(
                assistant_content=state.assistant_content,
                completed_tool_results=tuple(tool_results),
                next_tool_index=index,
            )
            persist_deferred_tool_batch(workspace, next_state, resumed=True)
            return DeferredResumeOutcome(result=finish_deferred(next_state, False))
        assert sequential.tool_result is not None
        tool_results.append(sequential.tool_result)
        observation = apply_result(sequential)
        if observation.kind == "finish":
            clear_deferred_tool_state(workspace)
            return DeferredResumeOutcome(result=finish_action(observation))

    clear_deferred_tool_state(workspace)
    return DeferredResumeOutcome(tool_results=tuple(tool_results))


def persist_deferred_tool_batch(
    workspace: RunWorkspace,
    state: DeferredToolState,
    *,
    resumed: bool,
) -> None:
    write_deferred_tool_state(workspace, state)
    append_session_event(
        workspace.session_dir,
        "tool_deferred",
        {"tool": state.pending_tool_use, "resumed": resumed},
    )


__all__ = [
    "DeferredResumeOutcome",
    "persist_deferred_tool_batch",
    "resume_deferred_tool_batch",
]
