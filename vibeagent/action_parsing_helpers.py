from __future__ import annotations

import math
from typing import Any

from .types import (
    DirectoryTransfer,
    EditOperation,
    JsonPatchOperation,
    MoveFileTransfer,
    PlanItem,
    ReadFileContextItem,
    ReadFileRangeItem,
    RunCommandItem,
    UpdatePlanAction,
    WriteFileItem,
)


PLAN_ITEM_STATUS_ALIASES = {
    "complete": "completed",
    "completed": "completed",
    "cancelled": "completed",
    "canceled": "completed",
    "done": "completed",
    "finished": "completed",
    "skipped": "completed",
    "success": "completed",
    "succeeded": "completed",
    "active": "in_progress",
    "doing": "in_progress",
    "in-progress": "in_progress",
    "in_progress": "in_progress",
    "started": "in_progress",
    "pending": "pending",
    "todo": "pending",
    "to-do": "pending",
    "to do": "pending",
    "to_do": "pending",
    "not-started": "pending",
    "not started": "pending",
    "not_started": "pending",
    "blocked": "pending",
    "deferred": "pending",
    "open": "pending",
    "paused": "pending",
    "queued": "pending",
    "waiting": "pending",
}
PLAN_ITEM_STATUS_VALUES = set(PLAN_ITEM_STATUS_ALIASES)
PLAN_ITEM_SCHEMA_STATUS_VALUES = ("complete", "completed", "done", "in-progress", "in_progress", "pending", "todo")


class ActionParseError(ValueError):
    def __init__(self, message: str, raw: str):
        super().__init__(message)
        self.raw = raw


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


def parse_plan_items(value: Any, raw: str) -> list[PlanItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError("update_plan action requires a non-empty plan list.", raw)
    if len(value) > 20:
        raise ActionParseError("update_plan action plan must contain at most 20 items.", raw)

    items: list[PlanItem] = []
    in_progress_count = 0
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"update_plan item {index} must be an object.", raw)
        step = item.get("step")
        status = normalize_plan_item_status(item.get("status"))
        if not isinstance(step, str) or not step.strip():
            raise ActionParseError(f"update_plan item {index} requires a non-empty step.", raw)
        if status is None:
            raise ActionParseError(f"update_plan item {index} has an invalid status.", raw)
        if status == "in_progress":
            in_progress_count += 1
        items.append(PlanItem(step=step.strip(), status=status))

    if in_progress_count > 1:
        raise ActionParseError("update_plan action allows at most one in_progress item.", raw)
    return items


def normalize_plan_item_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return PLAN_ITEM_STATUS_ALIASES.get(value.strip().lower())


def parse_read_file_paths(value: Any, raw: str) -> list[str]:
    return parse_path_list(value, raw, "read_files", maximum=20)


def parse_read_file_contexts(value: Any, raw: str) -> list[ReadFileContextItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError("read_file_contexts action requires a non-empty contexts list.", raw)
    if len(value) > 20:
        raise ActionParseError("read_file_contexts action contexts must contain at most 20 items.", raw)

    contexts: list[ReadFileContextItem] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"read_file_contexts context {index} must be an object.", raw)
        path = item.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ActionParseError(f"read_file_contexts context {index} requires a non-empty path.", raw)
        line = parse_optional_positive_int(item.get("line"), f"read_file_contexts context {index} line", raw, maximum=None)
        if line is None:
            raise ActionParseError(f"read_file_contexts context {index} requires line.", raw)
        context_lines = parse_nonnegative_int(
            item.get("context_lines", 20),
            f"read_file_contexts context {index} context_lines",
            raw,
            maximum=500,
        )
        contexts.append(ReadFileContextItem(path=path.strip(), line=line, context_lines=context_lines))
    return contexts


def parse_read_file_ranges(value: Any, raw: str) -> list[ReadFileRangeItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError("read_file_ranges action requires a non-empty ranges list.", raw)
    if len(value) > 20:
        raise ActionParseError("read_file_ranges action ranges must contain at most 20 items.", raw)

    ranges: list[ReadFileRangeItem] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"read_file_ranges range {index} must be an object.", raw)
        path = item.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ActionParseError(f"read_file_ranges range {index} requires a non-empty path.", raw)
        start_line = parse_optional_positive_int(item.get("start_line"), f"read_file_ranges range {index} start_line", raw, maximum=None)
        if start_line is None:
            raise ActionParseError(f"read_file_ranges range {index} requires start_line.", raw)
        line_count = parse_optional_positive_int(item.get("line_count", 120), f"read_file_ranges range {index} line_count", raw, maximum=1000) or 120
        ranges.append(ReadFileRangeItem(path=path.strip(), start_line=start_line, line_count=line_count))
    return ranges


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


def parse_run_command_items(value: Any, raw: str, action_type: str) -> list[RunCommandItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError(f"{action_type} action requires a non-empty commands list.", raw)
    if len(value) > 10:
        raise ActionParseError(f"{action_type} action commands must contain at most 10 items.", raw)

    commands: list[RunCommandItem] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"{action_type} command {index} must be an object.", raw)
        command = item.get("command")
        if not isinstance(command, str) or not command.strip():
            raise ActionParseError(f"{action_type} command {index} requires a non-empty command.", raw)
        cwd = item.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise ActionParseError(f"{action_type} command {index} cwd must be a string when provided.", raw)
        timeout_ms = parse_optional_positive_int(item.get("timeout_ms"), f"{action_type} command {index} timeout_ms", raw, maximum=600_000)
        if timeout_ms is not None and timeout_ms < 100:
            raise ActionParseError(f"{action_type} command {index} timeout_ms must be at least 100.", raw)
        max_output_chars = parse_optional_positive_int(
            item.get("max_output_chars"),
            f"{action_type} command {index} max_output_chars",
            raw,
            maximum=50_000,
        )
        if max_output_chars is not None and max_output_chars < 1_000:
            raise ActionParseError(f"{action_type} command {index} max_output_chars must be at least 1000.", raw)
        extract_output_contexts = item.get("extract_output_contexts", False)
        if not isinstance(extract_output_contexts, bool):
            raise ActionParseError(f"{action_type} command {index} extract_output_contexts must be a boolean.", raw)
        extract_output_diagnostics = item.get("extract_output_diagnostics", False)
        if not isinstance(extract_output_diagnostics, bool):
            raise ActionParseError(f"{action_type} command {index} extract_output_diagnostics must be a boolean.", raw)
        context_lines = parse_nonnegative_int(
            item.get("context_lines", 5),
            f"{action_type} command {index} context_lines",
            raw,
            maximum=500,
        )
        max_diagnostics = parse_optional_positive_int(
            item.get("max_diagnostics", 50),
            f"{action_type} command {index} max_diagnostics",
            raw,
            maximum=200,
        ) or 50
        max_contexts = parse_optional_positive_int(
            item.get("max_contexts", 20),
            f"{action_type} command {index} max_contexts",
            raw,
            maximum=100,
        ) or 20
        max_bytes_per_context = parse_optional_positive_int(
            item.get("max_bytes_per_context", 20_000),
            f"{action_type} command {index} max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1_000:
            raise ActionParseError(f"{action_type} command {index} max_bytes_per_context must be at least 1000.", raw)
        commands.append(
            RunCommandItem(
                command=command.strip(),
                timeout_ms=timeout_ms,
                cwd=cwd,
                max_output_chars=max_output_chars,
                extract_output_contexts=extract_output_contexts,
                extract_output_diagnostics=extract_output_diagnostics,
                context_lines=context_lines,
                max_diagnostics=max_diagnostics,
                max_contexts=max_contexts,
                max_bytes_per_context=max_bytes_per_context,
            )
        )
    return commands


def parse_move_file_transfers(value: Any, raw: str, action_type: str) -> list[MoveFileTransfer]:
    if not isinstance(value, list) or not value:
        raise ActionParseError(f"{action_type} action requires a non-empty transfers list.", raw)
    if len(value) > 100:
        raise ActionParseError(f"{action_type} action transfers must contain at most 100 items.", raw)

    transfers: list[MoveFileTransfer] = []
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
        transfers.append(MoveFileTransfer(source=normalized_source, destination=normalized_destination))
    return transfers


def parse_directory_transfers(value: Any, raw: str, action_type: str) -> list[DirectoryTransfer]:
    if not isinstance(value, list) or not value:
        raise ActionParseError(f"{action_type} action requires a non-empty transfers list.", raw)
    if len(value) > 100:
        raise ActionParseError(f"{action_type} action transfers must contain at most 100 items.", raw)

    transfers: list[DirectoryTransfer] = []
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
        transfers.append(DirectoryTransfer(source=normalized_source, destination=normalized_destination))
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


def _coerce_int(value: Any) -> int | None:
    if type(value) is int:
        return value
    if type(value) is float and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        normalized = stripped.replace("_", "").replace(",", "")
        if normalized.isdigit():
            return int(normalized)
        if normalized.count(".") == 1:
            whole, fraction = normalized.split(".", 1)
            if whole.isdigit() and fraction and set(fraction) == {"0"}:
                return int(whole)
    return None


def parse_optional_positive_int(value: Any, name: str, raw: str, maximum: int | None) -> int | None:
    if value is None:
        return None
    parsed = _coerce_int(value)
    if parsed is None or parsed < 1:
        raise ActionParseError(f"{name} must be a positive integer.", raw)
    if maximum is not None and parsed > maximum:
        raise ActionParseError(f"{name} must be at most {maximum}.", raw)
    return parsed


def parse_optional_nonnegative_int(value: Any, name: str, raw: str, maximum: int | None) -> int | None:
    if value is None:
        return None
    parsed = _coerce_int(value)
    if parsed is None or parsed < 0:
        raise ActionParseError(f"{name} must be a non-negative integer.", raw)
    if maximum is not None and parsed > maximum:
        raise ActionParseError(f"{name} must be at most {maximum}.", raw)
    return parsed


def parse_nonnegative_int(value: Any, name: str, raw: str, maximum: int | None) -> int:
    parsed = _coerce_int(value)
    if parsed is None or parsed < 0:
        raise ActionParseError(f"{name} must be a non-negative integer.", raw)
    if maximum is not None and parsed > maximum:
        raise ActionParseError(f"{name} must be at most {maximum}.", raw)
    return parsed


def summarize_plan_update(action: UpdatePlanAction) -> str:
    current = next((item.step for item in action.plan if item.status == "in_progress"), None)
    if current:
        return f"Plan updated. Current: {current}"
    if action.explanation and action.explanation.strip():
        return f"Plan updated. {action.explanation.strip()}"
    return "Plan updated."
