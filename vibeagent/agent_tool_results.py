from __future__ import annotations

from dataclasses import dataclass

from .agent_multimodal import build_tool_result_block
from .agent_observation_utils import observation_failed
from .agent_runtime_utils import append_session_event, summarize_command, to_jsonable
from .agent_tool_registry import activate_tools_from_observations
from .redaction import redact_jsonable_payload
from .types import AgentLogger, ApprovalPolicy, ContentBlock, Observation, RunCommandObservation
from .workspace_core import RunWorkspace


@dataclass
class ToolObservationContext:
    observations: list[Observation]
    active_tool_names: set[str]
    iteration: int
    approval_policy: ApprovalPolicy
    logger: AgentLogger | None


def build_tool_result_payload(observation: Observation, hook_results: tuple[object, ...] = ()) -> dict[str, object]:
    result_payload = redact_jsonable_payload(to_jsonable(observation))
    if not isinstance(result_payload, dict):
        result_payload = {"result": result_payload}
    scrub_internal_preview_fingerprint_fields(result_payload)
    if hook_results:
        result_payload["hooks"] = redact_jsonable_payload(to_jsonable(hook_results))
    return result_payload


def scrub_internal_preview_fingerprint_fields(result_payload: dict[str, object]) -> None:
    kind = result_payload.get("kind")
    if kind in {
        "write_file",
        "check_write_file",
        "replace_lines",
        "check_replace_lines",
        "insert_lines",
        "check_insert_lines",
        "append_file",
        "check_append_file",
    }:
        result_payload.pop("content", None)
    if kind in {"regex_replace", "check_regex_replace"}:
        for key in ("replacement", "case_sensitive", "multiline", "max_replacements"):
            result_payload.pop(key, None)


def record_tool_result_event(
    workspace: RunWorkspace,
    *,
    tool_id: str,
    tool_name: str,
    observation: Observation,
    iteration: int,
    hook_results: tuple[object, ...] = (),
    auto: bool = False,
    event_extra: dict[str, object] | None = None,
) -> dict[str, object]:
    result_payload = build_tool_result_payload(observation, hook_results)
    event: dict[str, object] = {
        "iteration": iteration,
        "id": tool_id,
        "name": tool_name,
        "result": result_payload,
    }
    if auto:
        event["auto"] = True
    if event_extra:
        event.update(event_extra)
    append_session_event(workspace.session_dir, "tool_result", event)
    return result_payload


def record_tool_result_observation(
    workspace: RunWorkspace,
    *,
    tool_id: str,
    tool_name: str,
    observation: Observation,
    iteration: int,
    hook_results: tuple[object, ...] = (),
    auto: bool = False,
    event_extra: dict[str, object] | None = None,
) -> ContentBlock:
    result_payload = record_tool_result_event(
        workspace,
        tool_id=tool_id,
        tool_name=tool_name,
        observation=observation,
        iteration=iteration,
        hook_results=hook_results,
        auto=auto,
        event_extra=event_extra,
    )
    return build_tool_result_block(workspace, tool_id, observation, result_payload)


def record_subagent_tool_result_event(
    workspace: RunWorkspace,
    *,
    subagent_id: str,
    parent_iteration: int,
    iteration: int,
    tool_id: str,
    tool_name: str,
    observation: Observation,
    failed: bool,
    hook_results: tuple[object, ...] = (),
) -> dict[str, object]:
    result_payload = build_tool_result_payload(observation, hook_results)
    append_session_event(
        workspace.session_dir,
        "subagent_tool_result",
        {
            "subagent_id": subagent_id,
            "parent_iteration": parent_iteration,
            "iteration": iteration,
            "id": tool_id,
            "name": tool_name,
            "failed": failed,
            "result": result_payload,
        },
    )
    return result_payload


def record_subagent_tool_observation(
    workspace: RunWorkspace,
    *,
    subagent_id: str,
    parent_iteration: int,
    iteration: int,
    tool_id: str,
    tool_name: str,
    observation: Observation,
    hook_results: tuple[object, ...] = (),
) -> ContentBlock:
    result_payload = record_subagent_tool_result_event(
        workspace,
        subagent_id=subagent_id,
        parent_iteration=parent_iteration,
        iteration=iteration,
        tool_id=tool_id,
        tool_name=tool_name,
        observation=observation,
        failed=observation_failed(observation),
        hook_results=hook_results,
    )
    return build_tool_result_block(workspace, tool_id, observation, result_payload)


def record_tool_observation(
    workspace: RunWorkspace,
    *,
    tool_id: str,
    tool_name: str,
    observation: Observation,
    additional_observations: tuple[Observation, ...],
    hook_results: tuple[object, ...],
    context: ToolObservationContext,
) -> ContentBlock:
    context.observations.append(observation)
    context.observations.extend(additional_observations)
    activate_tools_from_observations(
        workspace,
        context.active_tool_names,
        [observation],
        context.iteration,
        context.approval_policy,
    )

    result_payload = record_tool_result_event(
        workspace,
        tool_id=tool_id,
        tool_name=tool_name,
        observation=observation,
        iteration=context.iteration,
        hook_results=hook_results,
    )
    if isinstance(observation, RunCommandObservation) and context.logger:
        ok = observation.result.exit_code == 0 and not observation.result.timed_out
        context.logger("observed success" if ok else "observed failure", summarize_command(observation.result))
    return build_tool_result_block(workspace, tool_id, observation, result_payload)


__all__ = [
    "ToolObservationContext",
    "build_tool_result_payload",
    "record_subagent_tool_observation",
    "record_subagent_tool_result_event",
    "record_tool_observation",
    "record_tool_result_event",
    "record_tool_result_observation",
]
