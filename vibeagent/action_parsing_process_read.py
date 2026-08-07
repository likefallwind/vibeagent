from __future__ import annotations

from typing import Any

from .action_parsing_process_fields import (
    parse_optional_command_output_chars,
    parse_optional_output_filter,
    parse_output_context_options,
    parse_process_id,
)
from .action_parsing_helpers import parse_optional_positive_int
from .types import (
    ListProcessesAction,
    ProcessOutputContextsAction,
    ProcessOutputDiagnosticsAction,
    ReadProcessAction,
)


PROCESS_READ_ACTION_TYPES = {
    "read_process",
    "process_output_contexts",
    "process_output_diagnostics",
    "list_processes",
}


def parse_process_read_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type == "read_process":
        return ReadProcessAction(
            type="read_process",
            process_id=parse_process_id(value.get("process_id"), raw, "read_process"),
            max_output_chars=parse_optional_command_output_chars(value.get("max_output_chars"), raw),
            output_filter=parse_optional_output_filter(value.get("output_filter"), raw),
        )

    if action_type == "process_output_contexts":
        context_lines, max_contexts, max_bytes_per_context = parse_output_context_options(
            value,
            raw,
            default_context_lines=5,
        )
        return ProcessOutputContextsAction(
            type="process_output_contexts",
            process_id=parse_process_id(value.get("process_id"), raw, "process_output_contexts"),
            max_output_chars=parse_optional_command_output_chars(value.get("max_output_chars"), raw),
            context_lines=context_lines,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "process_output_diagnostics":
        context_lines, max_contexts, max_bytes_per_context = parse_output_context_options(
            value,
            raw,
            default_context_lines=2,
        )
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
        return ProcessOutputDiagnosticsAction(
            type="process_output_diagnostics",
            process_id=parse_process_id(value.get("process_id"), raw, "process_output_diagnostics"),
            max_output_chars=parse_optional_command_output_chars(value.get("max_output_chars"), raw),
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "list_processes":
        return ListProcessesAction(type="list_processes")

    return None
