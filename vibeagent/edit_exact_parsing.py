from __future__ import annotations

import shlex

from .process_commands import decode_stdin_escapes
from .types import EditOperation


def parse_edit_file_argument(
    argument: str | None,
    *,
    path: str | None = None,
    old: str | None = None,
    new: str | None = None,
    usage: str,
) -> tuple[str, str, str]:
    if path is not None or old is not None or new is not None:
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        if old is None or old == "":
            raise ValueError(f"{usage} requires non-empty old text.")
        if new is None:
            raise ValueError(f"{usage} requires new text.")
        return path.strip(), decode_stdin_escapes(old), decode_stdin_escapes(new)

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path, old text, and new text.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 3:
        raise ValueError("expected path, old text, and new text.")
    parsed_path, raw_old, raw_new = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    if raw_old == "":
        raise ValueError(f"{usage} requires non-empty old text.")
    return parsed_path.strip(), decode_stdin_escapes(raw_old), decode_stdin_escapes(raw_new)


def parse_multi_edit_file_argument(
    argument: str | None,
    *,
    path: str | None = None,
    edits: list[EditOperation] | list[str] | None = None,
    usage: str,
) -> tuple[str, list[EditOperation]]:
    if edits is not None:
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        if edits and all(isinstance(edit, EditOperation) for edit in edits):
            return path.strip(), list(edits)
        parts = [str(part) for part in edits]
        parsed_path = path.strip()
    else:
        if not argument or not argument.strip():
            raise ValueError(f"{usage} requires path and old/new pairs.")
        try:
            split_parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if not split_parts:
            raise ValueError(f"{usage} requires path and old/new pairs.")
        parsed_path, parts = split_parts[0].strip(), list(split_parts[1:])
        if not parsed_path:
            raise ValueError(f"{usage} requires a non-empty path.")

    if not parts:
        raise ValueError(f"{usage} requires at least one old/new pair.")
    if len(parts) % 2 != 0:
        raise ValueError("expected old/new pairs.")

    parsed_edits: list[EditOperation] = []
    for index in range(0, len(parts), 2):
        old, new = parts[index], parts[index + 1]
        if old == "":
            raise ValueError(f"{usage} requires non-empty old text.")
        parsed_edits.append(EditOperation(old=decode_stdin_escapes(old), new=decode_stdin_escapes(new)))
    return parsed_path, parsed_edits
