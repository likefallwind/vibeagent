from __future__ import annotations

from typing import Any, Callable, TypeVar

from .action_parsing_scalars import (
    ActionParseError,
    INT_STRING_PATTERN,
    coerce_int,
    parse_nonnegative_int,
    parse_optional_nonnegative_int,
    parse_optional_positive_int,
)
from .action_parsing_plan import (
    PLAN_ITEM_SCHEMA_STATUS_VALUES,
    PLAN_ITEM_STATUS_ALIASES,
    PLAN_ITEM_STATUS_VALUES,
    normalize_plan_item_status,
    parse_plan_items,
    summarize_plan_update,
)
from .action_parsing_read_items import parse_read_file_contexts, parse_read_file_ranges
from .action_parsing_run_commands import parse_run_command_items
from .types import (
    DirectoryTransfer,
    EditOperation,
    JsonPatchOperation,
    MoveFileTransfer,
    WriteFileItem,
)


TransferRecord = TypeVar("TransferRecord")


def parse_code_rename_input(
    value: dict[str, Any],
    raw: str,
    action_name: str,
    default_max_replacements: int,
) -> tuple[str, str, str | None, int, int]:
    symbol = value.get("symbol")
    new_name = value.get("new_name")
    path = value.get("path")
    max_files = value.get("max_files", 100)
    max_replacements = value.get("max_replacements", default_max_replacements)
    if not isinstance(symbol, str) or not symbol.strip():
        raise ActionParseError(f"{action_name} action requires a non-empty symbol.", raw)
    if not isinstance(new_name, str) or not new_name.strip():
        raise ActionParseError(f"{action_name} action requires a non-empty new_name.", raw)
    if "\n" in symbol or "\r" in symbol or "\n" in new_name or "\r" in new_name:
        raise ActionParseError(f"{action_name} action symbol and new_name must be single-line strings.", raw)
    if path is not None and not isinstance(path, str):
        raise ActionParseError(f"{action_name} action path must be a string when provided.", raw)
    max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 100
    max_replacements = parse_optional_positive_int(max_replacements, "max_replacements", raw, maximum=2000) or default_max_replacements
    return symbol.strip(), new_name.strip(), path, max_files, max_replacements


def parse_read_file_paths(value: Any, raw: str) -> list[str]:
    return parse_path_list(value, raw, "read_files", maximum=20)


def parse_path_list(value: Any, raw: str, action_name: str, maximum: int) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ActionParseError(f"{action_name} action requires a non-empty paths list.", raw)
    if len(value) > maximum:
        raise ActionParseError(f"{action_name} action paths must contain at most {maximum} items.", raw)
    paths: list[str] = []
    for index, path in enumerate(value, start=1):
        if not isinstance(path, str) or not path.strip():
            raise ActionParseError(f"{action_name} path {index} must be a non-empty string.", raw)
        paths.append(path.strip())
    return paths


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


def parse_move_file_transfers(value: Any, raw: str, action_type: str) -> list[MoveFileTransfer]:
    return _parse_transfer_records(
        value,
        raw,
        action_type,
        lambda source, destination: MoveFileTransfer(source=source, destination=destination),
    )


def parse_directory_transfers(value: Any, raw: str, action_type: str) -> list[DirectoryTransfer]:
    return _parse_transfer_records(
        value,
        raw,
        action_type,
        lambda source, destination: DirectoryTransfer(source=source, destination=destination),
    )


def _parse_transfer_records(
    value: Any,
    raw: str,
    action_type: str,
    factory: Callable[[str, str], TransferRecord],
) -> list[TransferRecord]:
    if not isinstance(value, list) or not value:
        raise ActionParseError(f"{action_type} action requires a non-empty transfers list.", raw)
    if len(value) > 100:
        raise ActionParseError(f"{action_type} action transfers must contain at most 100 items.", raw)

    transfers: list[TransferRecord] = []
    seen_sources: set[str] = set()
    seen_destinations: set[str] = set()
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"{action_type} transfer {index} must be an object.", raw)
        source = item.get("source")
        destination = item.get("destination")
        if not isinstance(source, str) or not source.strip():
            raise ActionParseError(f"{action_type} transfer {index} requires a non-empty source.", raw)
        if not isinstance(destination, str) or not destination.strip():
            raise ActionParseError(f"{action_type} transfer {index} requires a non-empty destination.", raw)
        normalized_source = source.strip()
        normalized_destination = destination.strip()
        if normalized_source in seen_sources:
            raise ActionParseError(f"{action_type} transfer {index} duplicates source {normalized_source}.", raw)
        if normalized_destination in seen_destinations:
            raise ActionParseError(f"{action_type} transfer {index} duplicates destination {normalized_destination}.", raw)
        seen_sources.add(normalized_source)
        seen_destinations.add(normalized_destination)
        transfers.append(factory(normalized_source, normalized_destination))
    return transfers


def directory_transfer_pairs(transfers: list[DirectoryTransfer]) -> list[tuple[str, str]]:
    return [(transfer.source, transfer.destination) for transfer in transfers]


def parse_write_file_items(value: Any, raw: str, action_type: str = "write_files") -> list[WriteFileItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError(f"{action_type} action requires a non-empty files list.", raw)
    if len(value) > 20:
        raise ActionParseError(f"{action_type} action files must contain at most 20 items.", raw)

    files: list[WriteFileItem] = []
    seen: set[str] = set()
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"{action_type} file {index} must be an object.", raw)
        path = item.get("path")
        content = item.get("content")
        if not isinstance(path, str) or not path.strip():
            raise ActionParseError(f"{action_type} file {index} requires a non-empty path.", raw)
        if not isinstance(content, str):
            raise ActionParseError(f"{action_type} file {index} requires string content.", raw)
        normalized_path = path.strip()
        if normalized_path in seen:
            raise ActionParseError(f"{action_type} file {index} duplicates path {normalized_path}.", raw)
        seen.add(normalized_path)
        files.append(WriteFileItem(path=normalized_path, content=content))
    return files


def format_file_mode(mode: int) -> str:
    return f"{mode:04o}" if mode else ""


def parse_edit_operations(value: Any, raw: str, action_type: str = "multi_edit_file") -> list[EditOperation]:
    if not isinstance(value, list) or not value:
        raise ActionParseError(f"{action_type} action requires a non-empty edits list.", raw)
    if len(value) > 20:
        raise ActionParseError(f"{action_type} action edits must contain at most 20 items.", raw)

    edits: list[EditOperation] = []
    for index, edit in enumerate(value, start=1):
        if not isinstance(edit, dict):
            raise ActionParseError(f"{action_type} edit {index} must be an object.", raw)
        old = edit.get("old")
        new = edit.get("new")
        if not isinstance(old, str) or old == "":
            raise ActionParseError(f"{action_type} edit {index} requires non-empty string old.", raw)
        if not isinstance(new, str):
            raise ActionParseError(f"{action_type} edit {index} requires string new.", raw)
        replace_all = edit.get("replace_all", False)
        if type(replace_all) is not bool:
            raise ActionParseError(f"{action_type} edit {index} requires boolean replace_all.", raw)
        edits.append(EditOperation(old=old, new=new, replace_all=replace_all))
    return edits
