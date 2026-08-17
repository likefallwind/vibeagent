from __future__ import annotations

import shlex

from .bounded_stdin import MAX_STDIN_INPUT_BYTES, read_bounded_stdin
from .process_commands import decode_stdin_escapes


def parse_patch_argument(
    argument: str | None,
    *,
    path: str | None = None,
    patch: str | None = None,
    usage: str,
) -> tuple[str, str]:
    if path is not None or patch is not None:
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        if patch is None:
            raise ValueError(f"{usage} requires a patch.")
        return path.strip(), read_patch_argument_value(patch)

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path and patch.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 2:
        raise ValueError("expected path and patch.")
    parsed_path = parts[0].strip()
    if not parsed_path:
        raise ValueError(f"{usage} requires a non-empty path.")
    return parsed_path, read_patch_argument_value(parts[1])


def parse_patches_argument(argument: str | None, *, patch: str | None = None, usage: str) -> str:
    if patch is not None:
        return read_patch_argument_value(patch)

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires a patch.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 1:
        raise ValueError("expected patch.")
    return read_patch_argument_value(parts[0])


def read_patch_argument_value(value: str) -> str:
    if value == "-":
        return read_bounded_stdin(max_bytes=MAX_STDIN_INPUT_BYTES)
    return decode_stdin_escapes(value)
