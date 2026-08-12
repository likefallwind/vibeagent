from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .agent_multimodal import build_tool_result_block, build_updated_tool_result_block
from .agent_instruction_context import instruction_context_for_observation
from .agent_observation_utils import observation_failed
from .agent_runtime_utils import append_session_event, summarize_command, to_jsonable
from .agent_tool_registry import activate_tools_from_observations
from .redaction import redact_jsonable_payload
from .types import (
    AgentLogger,
    ApprovalPolicy,
    ContentBlock,
    Observation,
    RunCommandObservation,
)
from .workspace_core import RunWorkspace


_INSTRUCTION_CONTEXT_UNSET = object()


@dataclass
class ToolObservationContext:
    observations: list[Observation]
    active_tool_names: set[str]
    iteration: int
    approval_policy: ApprovalPolicy
    logger: AgentLogger | None
    excluded_tool_names: frozenset[str] = frozenset()
    allowed_tool_names: frozenset[str] | None = None
    instruction_hook_runner: (
        Callable[[dict[str, object]], tuple[object, ...]] | None
    ) = None


def build_tool_result_payload(
    observation: Observation,
    hook_results: tuple[object, ...] = (),
    additional_observations: tuple[Observation, ...] = (),
) -> dict[str, object]:
    result_payload = redact_jsonable_payload(to_jsonable(observation))
    if not isinstance(result_payload, dict):
        result_payload = {"result": result_payload}
    scrub_internal_preview_fingerprint_fields(result_payload)
    if hook_results:
        result_payload["hooks"] = redact_jsonable_payload(to_jsonable(hook_results))
    if additional_observations:
        result_payload["additionalResults"] = redact_jsonable_payload(
            to_jsonable(additional_observations)
        )
    return result_payload


def scrub_internal_preview_fingerprint_fields(
    result_payload: dict[str, object],
) -> None:
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
    if kind in {"patch_file", "check_patch", "patch_files", "check_patches"}:
        result_payload.pop("patch", None)
    if kind in {"write_files", "check_write_files"}:
        result_payload.pop("inputs", None)
    if kind in {"json_set", "check_json_set"}:
        for key in ("value", "create_missing"):
            result_payload.pop(key, None)
    if kind in {"json_patch", "check_json_patch"}:
        result_payload.pop("operations", None)
    if kind in {"write_process", "check_write_process"}:
        result_payload.pop("content_sha256", None)
    if kind == "check_run_commands":
        result_payload.pop("commands", None)


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
    instruction_context: object = _INSTRUCTION_CONTEXT_UNSET,
    additional_observations: tuple[Observation, ...] = (),
) -> dict[str, object]:
    result_payload = build_tool_result_payload(
        observation, hook_results, additional_observations
    )
    if instruction_context is _INSTRUCTION_CONTEXT_UNSET:
        instruction_context = instruction_context_for_observation(
            workspace, observation
        )
    if instruction_context is not None:
        assert isinstance(instruction_context, dict)
        result_payload["pathInstructions"] = redact_jsonable_payload(
            instruction_context
        )
        append_session_event(
            workspace.session_dir,
            "instructions_loaded",
            {
                "iteration": iteration,
                "tool": tool_name,
                "paths": instruction_context.get("paths", []),
                "files": instruction_context.get("files", []),
                "message": instruction_context.get("message", ""),
            },
        )
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
    instruction_context: object = _INSTRUCTION_CONTEXT_UNSET,
) -> dict[str, object]:
    result_payload = build_tool_result_payload(observation, hook_results)
    if instruction_context is _INSTRUCTION_CONTEXT_UNSET:
        instruction_context = instruction_context_for_observation(
            workspace,
            observation,
            consumer_id=subagent_instruction_consumer(subagent_id),
        )
    if instruction_context is not None:
        assert isinstance(instruction_context, dict)
        result_payload["pathInstructions"] = redact_jsonable_payload(instruction_context)
        append_session_event(
            workspace.session_dir,
            "subagent_instructions_loaded",
            {
                "subagent_id": subagent_id,
                "parent_iteration": parent_iteration,
                "iteration": iteration,
                "tool": tool_name,
                "paths": instruction_context.get("paths", []),
                "files": instruction_context.get("files", []),
                "message": instruction_context.get("message", ""),
            },
        )
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


def subagent_instruction_consumer(subagent_id: str) -> str:
    return f"subagent:{subagent_id}"


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
    updated_tool_output: object | None = None,
    updated_tool_output_set: bool = False,
    instruction_hook_runner: Callable[[dict[str, object]], tuple[object, ...]] | None = None,
) -> ContentBlock:
    instruction_context = instruction_context_for_observation(
        workspace,
        observation,
        consumer_id=subagent_instruction_consumer(subagent_id),
    )
    instruction_hook_results: tuple[object, ...] = ()
    if instruction_context is not None and instruction_hook_runner is not None:
        instruction_hook_results = tuple(instruction_hook_runner(instruction_context))
    result_payload = record_subagent_tool_result_event(
        workspace,
        subagent_id=subagent_id,
        parent_iteration=parent_iteration,
        iteration=iteration,
        tool_id=tool_id,
        tool_name=tool_name,
        observation=observation,
        failed=observation_failed(observation),
        hook_results=hook_results + instruction_hook_results,
        instruction_context=instruction_context,
    )
    if updated_tool_output_set:
        contexts = tuple(
            str(value)
            for result in hook_results
            if (value := getattr(result, "additional_context", None))
        )
        return build_updated_tool_result_block(
            tool_id,
            updated_tool_output,
            additional_contexts=contexts,
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
    updated_tool_output: object | None = None,
    updated_tool_output_set: bool = False,
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
        excluded_names=context.excluded_tool_names,
        allowed_names=context.allowed_tool_names,
    )

    instruction_context = instruction_context_for_observation(workspace, observation)
    instruction_hook_results: tuple[object, ...] = ()
    if instruction_context is not None and callable(context.instruction_hook_runner):
        instruction_hook_results = tuple(
            context.instruction_hook_runner(instruction_context)
        )
    result_payload = record_tool_result_event(
        workspace,
        tool_id=tool_id,
        tool_name=tool_name,
        observation=observation,
        iteration=context.iteration,
        hook_results=hook_results + instruction_hook_results,
        instruction_context=instruction_context,
        additional_observations=additional_observations,
    )
    if isinstance(observation, RunCommandObservation) and context.logger:
        ok = observation.result.exit_code == 0 and not observation.result.timed_out
        context.logger(
            "observed success" if ok else "observed failure",
            summarize_command(observation.result),
        )
    if updated_tool_output_set:
        contexts = tuple(
            str(value)
            for result in hook_results
            if (value := getattr(result, "additional_context", None))
        )
        return build_updated_tool_result_block(
            tool_id,
            updated_tool_output,
            additional_contexts=contexts,
            additional_results=(
                to_jsonable(additional_observations)
                if additional_observations
                else None
            ),
        )
    return build_tool_result_block(workspace, tool_id, observation, result_payload)


__all__ = [
    "ToolObservationContext",
    "build_tool_result_payload",
    "record_subagent_tool_observation",
    "record_subagent_tool_result_event",
    "record_tool_observation",
    "record_tool_result_event",
    "record_tool_result_observation",
    "subagent_instruction_consumer",
]
