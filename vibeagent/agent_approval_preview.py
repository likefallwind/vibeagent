from __future__ import annotations

from dataclasses import replace

from .agent_approval_preview_catalog import APPROVAL_WITHOUT_PREVIEW_ACTION_TYPES, PREVIEW_KIND_BY_ACTION_TYPE
from .agent_approval_preview_keys import approval_preview_key
from .agent_approval_preview_path_state import (
    approval_preview_paths,
    file_preview_invalidated_by_file_mutation,
    observation_paths,
    preview_search_invalidated,
)
from .agent_approval_preview_stale import (
    CHECKPOINT_RESTORE_MUTATION_OBSERVATION_KINDS,
    CHECKPOINT_RESTORE_PREVIEW_KINDS,
    COMMAND_MUTATION_OBSERVATION_KINDS,
    COMMAND_PREVIEW_KINDS,
    FILE_MUTATION_OBSERVATION_KINDS,
    FILE_PREVIEW_KINDS,
    GIT_MUTATION_OBSERVATION_KINDS,
    GIT_PREVIEW_KINDS,
    PROCESS_PREVIEW_KINDS,
    PROCESS_STATE_OBSERVATION_KINDS,
    WORKSPACE_MUTATION_OBSERVATION_KINDS,
    WORKSPACE_PREVIEW_KINDS,
)
from .agent_approval_preview_summary import (
    command_check_fingerprint_payload,
    file_diff_fingerprint_payload,
    preview_digest,
    preview_file_diffs,
    summarize_preview_observation,
)
from .types import ApprovalRequest, Observation


def attach_approval_preview(
    request: ApprovalRequest,
    action: object,
    observations: list[Observation],
) -> ApprovalRequest:
    preview = approval_preview_summary(action, observations)
    if not preview:
        return request
    return replace(request, preview=preview)


def approval_preview_summary(action: object, observations: list[Observation]) -> str | None:
    expected_kind = PREVIEW_KIND_BY_ACTION_TYPE.get(str(getattr(action, "type", "")))
    if not expected_kind:
        return None
    expected_key = approval_preview_key(action)
    expected_paths = approval_preview_paths(action)
    for observation in reversed(observations):
        observation_kind = getattr(observation, "kind", None)
        if observation_kind == expected_kind:
            if approval_preview_key(observation) != expected_key:
                continue
            if getattr(observation, "ok", True) is not True:
                return None
            return summarize_preview_observation(observation)
        if preview_search_invalidated(expected_kind, observation_kind, expected_paths, observation):
            return None
        if observation_kind != expected_kind:
            continue
    return None
