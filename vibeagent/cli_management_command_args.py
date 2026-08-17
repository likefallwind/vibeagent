from __future__ import annotations

import argparse
from collections.abc import Sequence
import json


def add_management_command_local_argument(
    local: argparse._MutuallyExclusiveGroup,
    *,
    option: str,
    dest: str,
) -> None:
    local.add_argument(
        option,
        dest=dest,
        metavar="JSON",
        help=argparse.SUPPRESS,
    )


def normalize_management_command_arguments(
    argv: Sequence[str],
    *,
    command_names: frozenset[str],
    hidden_option: str,
) -> list[str]:
    values = list(argv)
    index = _management_command_index(values, command_names)
    if index is None:
        return values
    command_values, trailing_globals = _extract_trailing_global_options(values[index + 1 :])
    return [
        *values[:index],
        *trailing_globals,
        hidden_option,
        json.dumps(command_values, ensure_ascii=True, separators=(",", ":")),
    ]


def decode_management_command_arguments(value: str, *, label: str) -> list[str]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} command arguments are invalid.") from error
    if not isinstance(payload, list) or any(not isinstance(item, str) for item in payload):
        raise ValueError(f"{label} command arguments are invalid.")
    return payload


def _management_command_index(
    values: list[str],
    command_names: frozenset[str],
) -> int | None:
    if values and values[0] in command_names:
        return 0
    index = 0
    while index < len(values):
        token = values[index]
        if token in command_names:
            return index
        if token == "--json":
            index += 1
            continue
        if token in {"--cwd", "--output-format"}:
            if index + 1 >= len(values):
                return None
            index += 2
            continue
        if token.startswith("--cwd=") or token.startswith("--output-format="):
            index += 1
            continue
        return None
    return None


def _extract_trailing_global_options(values: list[str]) -> tuple[list[str], list[str]]:
    separator = values.index("--") if "--" in values else len(values)
    command_values: list[str] = []
    global_values: list[str] = []
    index = 0
    while index < separator:
        token = values[index]
        if token == "--json":
            global_values.append(token)
            index += 1
            continue
        if token in {"--cwd", "--output-format"}:
            if index + 1 >= separator:
                command_values.append(token)
                index += 1
                continue
            global_values.extend(values[index : index + 2])
            index += 2
            continue
        if token.startswith("--cwd=") or token.startswith("--output-format="):
            global_values.append(token)
            index += 1
            continue
        command_values.append(token)
        index += 1
    command_values.extend(values[separator:])
    return command_values, global_values


__all__ = [
    "add_management_command_local_argument",
    "decode_management_command_arguments",
    "normalize_management_command_arguments",
]
