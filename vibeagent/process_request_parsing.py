from __future__ import annotations

import shlex


def split_process_argument(argument: str | None, *, max_parts: int, too_many_message: str) -> list[str]:
    if not argument or not argument.strip():
        return []
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) > max_parts:
        raise ValueError(too_many_message)
    return parts


def parse_process_request(
    argument: str | None = None,
    process_id: str | None = None,
    max_output_chars: int | None = None,
) -> tuple[str, int | None]:
    selected_process_id = process_id.strip() if process_id else None
    selected_max = max_output_chars
    parts = split_process_argument(
        argument,
        max_parts=2,
        too_many_message="expected process id and optional max chars.",
    )
    if parts:
        if process_id is not None:
            raise ValueError("process argument cannot be combined with explicit process_id.")
        selected_process_id = parts[0]
        if len(parts) == 2:
            selected_max = parse_positive_decimal(parts[1], "max chars")
    if not selected_process_id:
        raise ValueError("process id is required.")
    validate_max_output_chars(selected_max)
    return selected_process_id, selected_max


def parse_positive_decimal(value: str, label: str) -> int:
    if not value.isdigit():
        raise ValueError(f"invalid {label}: {value}")
    return int(value)


def validate_max_output_chars(max_output_chars: int | None) -> None:
    if max_output_chars is None:
        return
    if max_output_chars < 1_000:
        raise ValueError("max chars must be at least 1000.")
    if max_output_chars > 50_000:
        raise ValueError("max chars must be at most 50000.")
