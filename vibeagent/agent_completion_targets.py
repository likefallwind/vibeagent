from __future__ import annotations

from .agent_completion_kinds import PROJECT_CHANGE_OBSERVATION_KINDS
from .agent_completion_target_tokens import (
    BASIC_TARGET_FIELDS,
    add_basic_target_tokens,
    add_command_target_tokens,
    add_json_pointer_target_tokens,
    add_line_target_tokens,
    add_mcp_target_tokens,
    add_path_list_target_tokens,
    add_transfer_list_target_tokens,
    batch_path_target,
    batch_transfer_target,
    command_result_target_tokens,
    exact_message_target_tokens,
    mcp_call_target_token,
    normalized_approval_target_tokens,
    observation_summary_target_token,
    observation_symbol_target_tokens,
    observation_target_tokens,
    path_target,
    should_preserve_approval_target,
    string_attr,
    transfer_target_tokens,
)
from .agent_observation_utils import observation_failed
from .types import Observation

EXACT_MESSAGE_TARGET_ACTION_TYPES = {"git_commit", "git_stash"}


def denied_approval_resolved(denied: Observation, later_observations: list[Observation]) -> bool:
    action_type = str(getattr(denied, "action_type", "") or "")
    if not action_type:
        return False
    denied_target = str(getattr(denied, "target", "") or "")
    for observation in later_observations:
        if observation_failed(observation):
            continue
        if action_type not in PROJECT_CHANGE_OBSERVATION_KINDS:
            if observation.kind != action_type:
                continue
            if not denied_target or denied_approval_target_matches_observation(action_type, denied_target, observation):
                return True
            continue
        if observation.kind not in PROJECT_CHANGE_OBSERVATION_KINDS:
            continue
        if denied_approval_target_matches_observation(action_type, denied_target, observation):
            return True
    return False


def denied_approval_target_matches_observation(action_type: str, denied_target: str, observation: Observation) -> bool:
    if action_type in EXACT_MESSAGE_TARGET_ACTION_TYPES:
        return denied_target in exact_message_target_tokens(observation)
    denied_targets = normalized_approval_target_tokens(denied_target)
    if not denied_targets:
        return False
    observation_targets = observation_target_tokens(observation)
    return bool(denied_targets & observation_targets)
