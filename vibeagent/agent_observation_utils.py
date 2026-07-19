from __future__ import annotations

from .agent_observation_failure_kinds import (
    DIRECT_FAILURE_KINDS,
    ITEM_OK_FAILURE_COLLECTIONS,
    MESSAGE_PREFIX_SUCCESS_KINDS,
    NON_FAILURE_KINDS,
    OK_FLAG_FAILURE_KINDS,
)
from .types import Observation


def summarize(value: str, max_length: int = 500) -> str:
    compact = " ".join(value.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length]}..."


def observation_failed(observation: Observation) -> bool:
    if observation.kind in DIRECT_FAILURE_KINDS:
        return True
    if observation.kind == "ask_user":
        return observation.cancelled
    if observation.kind == "run_command":
        return observation.result.exit_code != 0 or observation.result.timed_out
    if observation.kind in NON_FAILURE_KINDS:
        return False
    if observation.kind in OK_FLAG_FAILURE_KINDS:
        return not observation.ok
    if observation.kind in ITEM_OK_FAILURE_COLLECTIONS:
        return any(not item.ok for item in getattr(observation, ITEM_OK_FAILURE_COLLECTIONS[observation.kind]))
    prefixes = MESSAGE_PREFIX_SUCCESS_KINDS.get(observation.kind)
    if prefixes is not None:
        return not observation.message.startswith(prefixes)
    return False
