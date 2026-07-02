from __future__ import annotations

from typing import Any

from .action_parsing_helpers import (
    parse_json_patch_input,
    parse_json_pointer_action_input,
    parse_json_set_input,
)
from .types import (
    CheckJsonPatchAction,
    CheckJsonRemoveAction,
    CheckJsonSetAction,
    JsonPatchAction,
    JsonRemoveAction,
    JsonSetAction,
)


JSON_ACTION_TYPES = {
    "check_json_set",
    "json_set",
    "check_json_remove",
    "json_remove",
    "check_json_patch",
    "json_patch",
}


def parse_json_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in JSON_ACTION_TYPES:
        return None

    if action_type == "check_json_set":
        path, pointer, json_value, create_missing = parse_json_set_input(value, raw, "check_json_set")
        return CheckJsonSetAction(
            type="check_json_set",
            path=path,
            pointer=pointer,
            value=json_value,
            create_missing=create_missing,
        )

    if action_type == "json_set":
        path, pointer, json_value, create_missing = parse_json_set_input(value, raw, "json_set")
        return JsonSetAction(
            type="json_set",
            path=path,
            pointer=pointer,
            value=json_value,
            create_missing=create_missing,
        )

    if action_type == "check_json_remove":
        path, pointer = parse_json_pointer_action_input(value, raw, "check_json_remove")
        return CheckJsonRemoveAction(type="check_json_remove", path=path, pointer=pointer)

    if action_type == "json_remove":
        path, pointer = parse_json_pointer_action_input(value, raw, "json_remove")
        return JsonRemoveAction(type="json_remove", path=path, pointer=pointer)

    if action_type == "check_json_patch":
        path, operations = parse_json_patch_input(value, raw, "check_json_patch")
        return CheckJsonPatchAction(type="check_json_patch", path=path, operations=operations)

    if action_type == "json_patch":
        path, operations = parse_json_patch_input(value, raw, "json_patch")
        return JsonPatchAction(type="json_patch", path=path, operations=operations)

    raise AssertionError(f"Unhandled JSON action type: {action_type!r}")
