from __future__ import annotations

import argparse
from collections.abc import Sequence
import json


MCP_COMMAND_OPTION = "--_mcp-command"


def add_mcp_command_local_argument(
    local: argparse._MutuallyExclusiveGroup,
) -> None:
    local.add_argument(
        MCP_COMMAND_OPTION,
        dest="mcp_command",
        metavar="JSON",
        help=argparse.SUPPRESS,
    )


def normalize_mcp_command_arguments(argv: Sequence[str]) -> list[str]:
    values = list(argv)
    index = _mcp_command_index(values)
    if index is None:
        return values
    command_values, trailing_globals = _extract_trailing_global_options(values[index + 1 :])
    return [
        *values[:index],
        *trailing_globals,
        MCP_COMMAND_OPTION,
        json.dumps(command_values, ensure_ascii=True, separators=(",", ":")),
    ]


def decode_mcp_command_arguments(value: str) -> list[str]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError("MCP command arguments are invalid.") from error
    if not isinstance(payload, list) or any(not isinstance(item, str) for item in payload):
        raise ValueError("MCP command arguments are invalid.")
    return payload


def _mcp_command_index(values: list[str]) -> int | None:
    if values and values[0] == "mcp":
        return 0
    index = 0
    while index < len(values):
        token = values[index]
        if token == "mcp":
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
    "add_mcp_command_local_argument",
    "decode_mcp_command_arguments",
    "normalize_mcp_command_arguments",
]
