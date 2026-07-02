from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_optional_nonnegative_int, parse_optional_positive_int
from .types import (
    CheckCheckpointDeleteAction,
    CheckCheckpointPruneAction,
    CheckCheckpointRestoreAction,
    CheckpointCreateAction,
    CheckpointDeleteAction,
    CheckpointDiffAction,
    CheckpointListAction,
    CheckpointPruneAction,
    CheckpointRestoreAction,
    CheckpointShowAction,
    CheckpointStatusAction,
)


CHECKPOINT_ACTION_TYPES = {
    "checkpoint_create",
    "checkpoint_list",
    "checkpoint_show",
    "checkpoint_diff",
    "checkpoint_status",
    "check_checkpoint_restore",
    "checkpoint_restore",
    "check_checkpoint_delete",
    "checkpoint_delete",
    "check_checkpoint_prune",
    "checkpoint_prune",
}


def _parse_checkpoint_id(value: Any, raw: str, action_type: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty checkpoint_id.", raw)
    return value.strip()


def _parse_keep_last(value: Any, raw: str, action_type: str) -> int:
    keep_last = parse_optional_nonnegative_int(value, "keep_last", raw, maximum=1000)
    if keep_last is None:
        raise ActionParseError(f"{action_type} action requires keep_last.", raw)
    return keep_last


def parse_checkpoint_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in CHECKPOINT_ACTION_TYPES:
        return None

    if action_type == "checkpoint_create":
        label = value.get("label")
        if label is not None and not isinstance(label, str):
            raise ActionParseError("checkpoint_create action label must be a string when provided.", raw)
        return CheckpointCreateAction(type="checkpoint_create", label=label)

    if action_type == "checkpoint_list":
        max_entries = parse_optional_positive_int(value.get("max_entries", 20), "max_entries", raw, maximum=100) or 20
        return CheckpointListAction(type="checkpoint_list", max_entries=max_entries)

    if action_type == "checkpoint_show":
        return CheckpointShowAction(
            type="checkpoint_show",
            checkpoint_id=_parse_checkpoint_id(value.get("checkpoint_id"), raw, "checkpoint_show"),
        )

    if action_type == "checkpoint_diff":
        checkpoint_id = _parse_checkpoint_id(value.get("checkpoint_id"), raw, "checkpoint_diff")
        max_chars = parse_optional_positive_int(value.get("max_chars", 40_000), "max_chars", raw, maximum=200_000) or 40_000
        if max_chars < 100:
            raise ActionParseError("max_chars must be at least 100.", raw)
        return CheckpointDiffAction(type="checkpoint_diff", checkpoint_id=checkpoint_id, max_chars=max_chars)

    if action_type == "checkpoint_status":
        return CheckpointStatusAction(
            type="checkpoint_status",
            checkpoint_id=_parse_checkpoint_id(value.get("checkpoint_id"), raw, "checkpoint_status"),
        )

    if action_type == "check_checkpoint_restore":
        return CheckCheckpointRestoreAction(
            type="check_checkpoint_restore",
            checkpoint_id=_parse_checkpoint_id(value.get("checkpoint_id"), raw, "check_checkpoint_restore"),
        )

    if action_type == "checkpoint_restore":
        return CheckpointRestoreAction(
            type="checkpoint_restore",
            checkpoint_id=_parse_checkpoint_id(value.get("checkpoint_id"), raw, "checkpoint_restore"),
        )

    if action_type == "check_checkpoint_delete":
        return CheckCheckpointDeleteAction(
            type="check_checkpoint_delete",
            checkpoint_id=_parse_checkpoint_id(value.get("checkpoint_id"), raw, "check_checkpoint_delete"),
        )

    if action_type == "checkpoint_delete":
        return CheckpointDeleteAction(
            type="checkpoint_delete",
            checkpoint_id=_parse_checkpoint_id(value.get("checkpoint_id"), raw, "checkpoint_delete"),
        )

    if action_type == "check_checkpoint_prune":
        return CheckCheckpointPruneAction(
            type="check_checkpoint_prune",
            keep_last=_parse_keep_last(value.get("keep_last"), raw, "check_checkpoint_prune"),
        )

    if action_type == "checkpoint_prune":
        return CheckpointPruneAction(
            type="checkpoint_prune",
            keep_last=_parse_keep_last(value.get("keep_last"), raw, "checkpoint_prune"),
        )

    raise AssertionError(f"Unhandled checkpoint action type: {action_type!r}")
