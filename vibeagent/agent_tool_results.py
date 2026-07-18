from __future__ import annotations

from .agent_multimodal import build_tool_result_block
from .agent_runtime_utils import append_session_event, summarize_command, to_jsonable
from .agent_tool_registry import activate_tools_from_observations
from .redaction import redact_jsonable_payload
from .types import AgentLogger, ApprovalPolicy, ContentBlock, Observation, RunCommandObservation
from .workspace_core import RunWorkspace


def record_tool_observation(
    workspace: RunWorkspace,
    *,
    tool_id: str,
    tool_name: str,
    observation: Observation,
    additional_observations: tuple[Observation, ...],
    hook_results: tuple[object, ...],
    observations: list[Observation],
    active_tool_names: set[str],
    iteration: int,
    approval_policy: ApprovalPolicy,
    logger: AgentLogger | None,
) -> ContentBlock:
    observations.append(observation)
    observations.extend(additional_observations)
    activate_tools_from_observations(
        workspace,
        active_tool_names,
        [observation],
        iteration,
        approval_policy,
    )

    result_payload = redact_jsonable_payload(to_jsonable(observation))
    if hook_results and isinstance(result_payload, dict):
        result_payload["hooks"] = redact_jsonable_payload(to_jsonable(hook_results))
    append_session_event(
        workspace.session_dir,
        "tool_result",
        {"iteration": iteration, "id": tool_id, "name": tool_name, "result": result_payload},
    )
    if isinstance(observation, RunCommandObservation) and logger:
        ok = observation.result.exit_code == 0 and not observation.result.timed_out
        logger("observed success" if ok else "observed failure", summarize_command(observation.result))
    return build_tool_result_block(workspace, tool_id, observation, result_payload)

__all__ = ["record_tool_observation"]
