from __future__ import annotations

import json
from pathlib import Path

from .workspace_code_intel import build_simple_diff
from .workspace_core import RunWorkspace
from .workspace_file_read import read_utf8_text_file
from .workspace_resolve import resolve_mutation_path


def json_set_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    pointer: str,
    value: object,
    create_missing: bool = False,
) -> tuple[Path, str]:
    target, updated, diff = build_json_set(workspace, relative_path, pointer, value, create_missing=create_missing)
    target.write_text(updated, encoding="utf-8")
    return target, diff


def preview_json_set_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    pointer: str,
    value: object,
    create_missing: bool = False,
) -> tuple[Path, str]:
    target, _updated, diff = build_json_set(workspace, relative_path, pointer, value, create_missing=create_missing)
    return target, diff


def json_remove_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    pointer: str,
) -> tuple[Path, str]:
    target, updated, diff = build_json_remove(workspace, relative_path, pointer)
    target.write_text(updated, encoding="utf-8")
    return target, diff


def preview_json_remove_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    pointer: str,
) -> tuple[Path, str]:
    target, _updated, diff = build_json_remove(workspace, relative_path, pointer)
    return target, diff


def json_patch_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    operations: list[dict[str, object]],
) -> tuple[Path, str]:
    target, updated, diff = build_json_patch(workspace, relative_path, operations)
    target.write_text(updated, encoding="utf-8")
    return target, diff


def preview_json_patch_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    operations: list[dict[str, object]],
) -> tuple[Path, str]:
    target, _updated, diff = build_json_patch(workspace, relative_path, operations)
    return target, diff


def build_json_set(
    workspace: RunWorkspace,
    relative_path: str,
    pointer: str,
    value: object,
    create_missing: bool = False,
) -> tuple[Path, str, str]:
    target = resolve_mutation_path(workspace, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    try:
        document = json.loads(before)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {relative_path}: {error.msg} at line {error.lineno} column {error.colno}") from error

    set_json_pointer_value(document, pointer, value, create_missing=create_missing)
    after = format_json_document(document)
    if after == before:
        raise ValueError(f"JSON set made no changes to {relative_path}")
    return target, after, build_simple_diff(relative_path, before, after)


def build_json_remove(
    workspace: RunWorkspace,
    relative_path: str,
    pointer: str,
) -> tuple[Path, str, str]:
    target = resolve_mutation_path(workspace, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    try:
        document = json.loads(before)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {relative_path}: {error.msg} at line {error.lineno} column {error.colno}") from error

    remove_json_pointer_value(document, pointer)
    after = format_json_document(document)
    if after == before:
        raise ValueError(f"JSON remove made no changes to {relative_path}")
    return target, after, build_simple_diff(relative_path, before, after)


def build_json_patch(
    workspace: RunWorkspace,
    relative_path: str,
    operations: list[dict[str, object]],
) -> tuple[Path, str, str]:
    if not operations:
        raise ValueError("At least one JSON patch operation is required.")
    if len(operations) > 50:
        raise ValueError("json_patch supports at most 50 operations.")

    target = resolve_mutation_path(workspace, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    try:
        document = json.loads(before)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {relative_path}: {error.msg} at line {error.lineno} column {error.colno}") from error

    for index, operation in enumerate(operations, start=1):
        apply_json_patch_operation(document, operation, index)

    after = format_json_document(document)
    if after == before:
        raise ValueError(f"JSON patch made no changes to {relative_path}")
    return target, after, build_simple_diff(relative_path, before, after)


def apply_json_patch_operation(document: object, operation: dict[str, object], index: int) -> None:
    op = operation.get("op")
    pointer = operation.get("path")
    if not isinstance(op, str) or op not in {"add", "replace", "remove"}:
        raise ValueError(f"JSON patch operation {index} has unsupported op: {op}")
    if not isinstance(pointer, str) or not pointer.strip():
        raise ValueError(f"JSON patch operation {index} requires a non-empty path.")

    if op == "remove":
        remove_json_pointer_value(document, pointer)
        return
    if "value" not in operation:
        raise ValueError(f"JSON patch operation {index} requires value.")
    if op == "add":
        add_json_pointer_value(document, pointer, operation["value"])
        return
    set_json_pointer_value(document, pointer, operation["value"], create_missing=False)


def add_json_pointer_value(document: object, pointer: str, value: object) -> None:
    parts = parse_json_pointer(pointer)
    if not parts:
        raise ValueError("JSON pointer must target a key or array item, not the document root.")

    current = document
    for index, part in enumerate(parts[:-1]):
        if isinstance(current, dict):
            if part not in current:
                raise ValueError(f"JSON pointer parent does not exist: /{'/'.join(parts[: index + 1])}")
            current = current[part]
            continue
        if isinstance(current, list):
            item_index = parse_json_array_index(part, len(current), allow_append=False)
            current = current[item_index]
            continue
        raise ValueError(f"JSON pointer parent is not a container: /{'/'.join(parts[: index + 1])}")

    final = parts[-1]
    if isinstance(current, dict):
        current[final] = value
        return
    if isinstance(current, list):
        item_index = parse_json_array_index(final, len(current), allow_append=True)
        current.insert(item_index, value)
        return
    raise ValueError("JSON pointer target parent is not an object or array.")


def set_json_pointer_value(document: object, pointer: str, value: object, create_missing: bool = False) -> None:
    parts = parse_json_pointer(pointer)
    if not parts:
        raise ValueError("JSON pointer must target a key or array item, not the document root.")

    current = document
    for index, part in enumerate(parts[:-1]):
        next_part = parts[index + 1]
        if isinstance(current, dict):
            if part not in current:
                if not create_missing:
                    raise ValueError(f"JSON pointer parent does not exist: /{'/'.join(parts[: index + 1])}")
                if next_part.isdigit() or next_part == "-":
                    raise ValueError("create_missing can only create object parents, not array parents.")
                current[part] = {}
            current = current[part]
            continue
        if isinstance(current, list):
            item_index = parse_json_array_index(part, len(current), allow_append=False)
            current = current[item_index]
            continue
        raise ValueError(f"JSON pointer parent is not a container: /{'/'.join(parts[: index + 1])}")

    final = parts[-1]
    if isinstance(current, dict):
        if final not in current and not create_missing:
            raise ValueError(f"JSON object key does not exist: {final}")
        if final in current and current[final] == value:
            raise ValueError("JSON set made no changes.")
        current[final] = value
        return
    if isinstance(current, list):
        if final == "-":
            current.append(value)
            return
        item_index = parse_json_array_index(final, len(current), allow_append=False)
        if current[item_index] == value:
            raise ValueError("JSON set made no changes.")
        current[item_index] = value
        return
    raise ValueError("JSON pointer target parent is not an object or array.")


def remove_json_pointer_value(document: object, pointer: str) -> None:
    parts = parse_json_pointer(pointer)
    if not parts:
        raise ValueError("JSON pointer must target a key or array item, not the document root.")

    current = document
    for index, part in enumerate(parts[:-1]):
        if isinstance(current, dict):
            if part not in current:
                raise ValueError(f"JSON pointer parent does not exist: /{'/'.join(parts[: index + 1])}")
            current = current[part]
            continue
        if isinstance(current, list):
            item_index = parse_json_array_index(part, len(current), allow_append=False)
            current = current[item_index]
            continue
        raise ValueError(f"JSON pointer parent is not a container: /{'/'.join(parts[: index + 1])}")

    final = parts[-1]
    if isinstance(current, dict):
        if final not in current:
            raise ValueError(f"JSON object key does not exist: {final}")
        del current[final]
        return
    if isinstance(current, list):
        if final == "-":
            raise ValueError("JSON array removal requires an explicit index.")
        item_index = parse_json_array_index(final, len(current), allow_append=False)
        del current[item_index]
        return
    raise ValueError("JSON pointer target parent is not an object or array.")


def parse_json_pointer(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer must start with '/'.")
    parts = pointer.split("/")[1:]
    return [part.replace("~1", "/").replace("~0", "~") for part in parts]


def parse_json_array_index(raw: str, length: int, allow_append: bool) -> int:
    if raw == "-" and allow_append:
        return length
    if not raw.isdigit():
        raise ValueError(f"JSON array index must be a non-negative integer: {raw}")
    index = int(raw)
    if index >= length:
        raise ValueError(f"JSON array index out of range: {raw}")
    return index


def format_json_document(document: object) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"
