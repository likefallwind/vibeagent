from __future__ import annotations


def python_found_message(
    total: int,
    shown: int,
    label: str,
    *,
    errors: list[dict[str, object]] | list[str] | None = None,
) -> str:
    message = f"Found {total} Python {label}(s)."
    if shown < total:
        message += f" Showing first {shown}."
    if errors:
        message += f" Skipped {len(errors)} file(s)."
    return message


def python_call_graph_message(
    total: int,
    shown: int,
    total_files: int,
    max_files: int,
    *,
    errors: list[dict[str, object]] | list[str] | None = None,
) -> str:
    message = f"Found {total} Python call graph edge(s) across {total_files} file(s)."
    if shown < total:
        message += f" Showing first {shown}."
    if total_files > max_files:
        message += f" Inspected first {max_files} file(s)."
    if errors:
        message += f" Skipped {len(errors)} file(s)."
    return message
