from __future__ import annotations

import shlex

from .process_commands import decode_stdin_escapes
from .types import WriteFileItem


def parse_write_file_argument(
    argument: str | None,
    *,
    path: str | None = None,
    content: str | None = None,
    usage: str,
) -> tuple[str, str]:
    if path is not None or content is not None:
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        if content is None:
            raise ValueError(f"{usage} requires text.")
        return path.strip(), decode_stdin_escapes(content)

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path and text.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 2:
        raise ValueError("expected path and text.")
    parsed_path, raw_content = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    return parsed_path, decode_stdin_escapes(raw_content)


def parse_write_file_list_argument(
    argument: str | None,
    *,
    files: list[WriteFileItem] | list[str] | None = None,
    usage: str,
) -> list[WriteFileItem]:
    if files is not None:
        if files and all(isinstance(file, WriteFileItem) for file in files):
            return list(files)
        parts = [str(part) for part in files]
    else:
        if not argument or not argument.strip():
            raise ValueError(f"{usage} requires path and text pairs.")
        try:
            split_parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        parts = list(split_parts)

    if not parts:
        raise ValueError(f"{usage} requires path and text pairs.")
    if len(parts) % 2 != 0:
        raise ValueError("expected path and text pairs.")

    parsed_files: list[WriteFileItem] = []
    for index in range(0, len(parts), 2):
        path, raw_content = parts[index], parts[index + 1]
        if not path:
            raise ValueError(f"{usage} requires a non-empty path.")
        parsed_files.append(WriteFileItem(path=path, content=decode_stdin_escapes(raw_content)))
    return parsed_files
