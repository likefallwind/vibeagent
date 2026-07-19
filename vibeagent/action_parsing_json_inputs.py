from __future__ import annotations

from typing import Any

from .action_parsing_scalars import ActionParseError
from .types import JsonPatchOperation


def parse_json_set_input(value: dict[str, Any], raw: str, action_type: str) -> tuple[str, str, Any, bool]:
    path, pointer = parse_json_pointer_action_input(value, raw, action_type)
    create_missing = value.get("create_missing", False)
    if "value" not in value:
        raise ActionParseError(f"{action_type} action requires value.", raw)
    if not isinstance(create_missing, bool):
        raise ActionParseError(f"{action_type} action create_missing must be a boolean.", raw)
    return path, pointer, value["value"], create_missing


def parse_json_pointer_action_input(value: dict[str, Any], raw: str, action_type: str) -> tuple[str, str]:
    path = value.get("path")
    pointer = value.get("pointer")
    if not isinstance(path, str) or not path.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty string path.", raw)
    if not isinstance(pointer, str) or not pointer.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty string pointer.", raw)
    return path.strip(), pointer.strip()


def parse_json_patch_input(value: dict[str, Any], raw: str, action_type: str) -> tuple[str, list[JsonPatchOperation]]:
    path = value.get("path")
    operations = value.get("operations")
    if not isinstance(path, str) or not path.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty string path.", raw)
    if not isinstance(operations, list) or not operations:
        raise ActionParseError(f"{action_type} action requires a non-empty operations list.", raw)
    if len(operations) > 50:
        raise ActionParseError(f"{action_type} action operations must contain at most 50 items.", raw)

    parsed: list[JsonPatchOperation] = []
    for index, operation in enumerate(operations, start=1):
        if not isinstance(operation, dict):
            raise ActionParseError(f"{action_type} operation {index} must be an object.", raw)
        op = operation.get("op")
        pointer = operation.get("path")
        if op not in {"add", "replace", "remove"}:
            raise ActionParseError(f"{action_type} operation {index} has an unsupported op.", raw)
        if not isinstance(pointer, str) or not pointer.strip():
            raise ActionParseError(f"{action_type} operation {index} requires a non-empty path.", raw)
        if op in {"add", "replace"} and "value" not in operation:
            raise ActionParseError(f"{action_type} operation {index} requires value.", raw)
        parsed.append(JsonPatchOperation(op=op, path=pointer.strip(), value=operation.get("value")))
    return path.strip(), parsed
