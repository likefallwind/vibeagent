from __future__ import annotations

import json
import shlex

from .types import JsonPatchOperation


def parse_json_set_argument(
    argument: str | None,
    *,
    path: str | None = None,
    pointer: str | None = None,
    value: object = None,
    create_missing: bool = False,
    usage: str,
) -> tuple[str, str, object, bool]:
    if path is not None or pointer is not None:
        if not path or not path.strip() or not pointer or not pointer.strip():
            raise ValueError(f"{usage} requires path and pointer.")
        return path.strip(), pointer.strip(), value, create_missing

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path, pointer, and JSON value.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    parsed_create_missing = False
    if "--create-missing" in parts:
        parsed_create_missing = True
        parts = [part for part in parts if part != "--create-missing"]
    if len(parts) != 3:
        raise ValueError("expected path, pointer, and JSON value.")
    parsed_path, parsed_pointer, raw_value = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    if not parsed_pointer.strip():
        raise ValueError(f"{usage} requires a non-empty pointer.")
    try:
        parsed_value = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON value is invalid: {error.msg}") from error
    return parsed_path, parsed_pointer, parsed_value, parsed_create_missing


def parse_json_remove_argument(
    argument: str | None,
    *,
    path: str | None = None,
    pointer: str | None = None,
    usage: str,
) -> tuple[str, str]:
    if path is not None or pointer is not None:
        if not path or not path.strip() or not pointer or not pointer.strip():
            raise ValueError(f"{usage} requires path and pointer.")
        return path.strip(), pointer.strip()

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path and pointer.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 2:
        raise ValueError("expected path and pointer.")
    parsed_path, parsed_pointer = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    if not parsed_pointer.strip():
        raise ValueError(f"{usage} requires a non-empty pointer.")
    return parsed_path, parsed_pointer


def parse_json_patch_argument(
    argument: str | None,
    *,
    path: str | None = None,
    operations: object = None,
    usage: str,
) -> tuple[str, list[JsonPatchOperation]]:
    if path is not None or operations is not None:
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        return path.strip(), parse_json_patch_operations(operations)

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path and JSON operations array.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 2:
        raise ValueError("expected path and JSON operations array.")
    parsed_path, raw_operations = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    try:
        parsed_operations = json.loads(raw_operations)
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON operations array is invalid: {error.msg}") from error
    return parsed_path, parse_json_patch_operations(parsed_operations)


def parse_json_patch_operations(operations: object) -> list[JsonPatchOperation]:
    if not isinstance(operations, list) or not operations:
        raise ValueError("JSON operations must be a non-empty array.")
    if len(operations) > 50:
        raise ValueError("JSON operations must contain at most 50 items.")
    parsed: list[JsonPatchOperation] = []
    for index, operation in enumerate(operations, start=1):
        if not isinstance(operation, dict):
            raise ValueError(f"operation {index} must be an object.")
        op = operation.get("op")
        pointer = operation.get("path")
        if op not in {"add", "replace", "remove"}:
            raise ValueError(f"operation {index} has an unsupported op.")
        if not isinstance(pointer, str) or not pointer.strip():
            raise ValueError(f"operation {index} requires a non-empty path.")
        if op in {"add", "replace"} and "value" not in operation:
            raise ValueError(f"operation {index} requires value.")
        parsed.append(JsonPatchOperation(op=op, path=pointer.strip(), value=operation.get("value")))
    return parsed
