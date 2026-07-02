from __future__ import annotations

import shlex

from .process_commands import decode_stdin_escapes


def parse_symbol_path_argument(
    argument: str | None,
    *,
    symbol: str | None = None,
    path: str | None = None,
    usage: str,
) -> tuple[str, str | None]:
    if symbol is not None:
        parsed_symbol = symbol.strip()
        if not parsed_symbol:
            raise ValueError(f"{usage} requires a non-empty symbol.")
        if "\n" in parsed_symbol or "\r" in parsed_symbol:
            raise ValueError("symbol must be a single-line string.")
        return parsed_symbol, path.strip() if path and path.strip() else None

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires a symbol.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if not parts:
        raise ValueError(f"{usage} requires a symbol.")
    if len(parts) > 2:
        raise ValueError("expected a symbol and optional path.")
    parsed_symbol = parts[0].strip()
    if not parsed_symbol:
        raise ValueError(f"{usage} requires a non-empty symbol.")
    if "\n" in parsed_symbol or "\r" in parsed_symbol:
        raise ValueError("symbol must be a single-line string.")
    return parsed_symbol, parts[1] if len(parts) == 2 else None


def parse_rename_argument(
    argument: str | None,
    *,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    usage: str,
) -> tuple[str, str, str | None]:
    if symbol is not None or new_name is not None:
        if symbol is None or new_name is None:
            raise ValueError(f"{usage} requires both symbol and new_name.")
        parsed_symbol = symbol.strip()
        parsed_new_name = new_name.strip()
        if not parsed_symbol:
            raise ValueError(f"{usage} requires a non-empty symbol.")
        if not parsed_new_name:
            raise ValueError(f"{usage} requires a non-empty new_name.")
        if "\n" in parsed_symbol or "\r" in parsed_symbol or "\n" in parsed_new_name or "\r" in parsed_new_name:
            raise ValueError("symbol and new_name must be single-line strings.")
        return parsed_symbol, parsed_new_name, path.strip() if path and path.strip() else None

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires symbol and new_name.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) < 2:
        raise ValueError(f"{usage} requires symbol and new_name.")
    if len(parts) > 3:
        raise ValueError("expected symbol, new_name, and optional path.")
    parsed_symbol = parts[0].strip()
    parsed_new_name = parts[1].strip()
    if not parsed_symbol:
        raise ValueError(f"{usage} requires a non-empty symbol.")
    if not parsed_new_name:
        raise ValueError(f"{usage} requires a non-empty new_name.")
    if "\n" in parsed_symbol or "\r" in parsed_symbol or "\n" in parsed_new_name or "\r" in parsed_new_name:
        raise ValueError("symbol and new_name must be single-line strings.")
    return parsed_symbol, parsed_new_name, parts[2] if len(parts) == 3 else None


def parse_replace_python_definition_argument(
    argument: str | None,
    *,
    symbol: str | None = None,
    content: str | None = None,
    path: str | None = None,
    usage: str,
) -> tuple[str, str, str | None]:
    if symbol is not None or content is not None:
        if symbol is None or content is None:
            raise ValueError(f"{usage} requires both symbol and content.")
        parsed_symbol = symbol.strip()
        if not parsed_symbol:
            raise ValueError(f"{usage} requires a non-empty symbol.")
        if "\n" in parsed_symbol or "\r" in parsed_symbol:
            raise ValueError("symbol must be a single-line string.")
        parsed_content = decode_stdin_escapes(content)
        if not parsed_content.strip():
            raise ValueError(f"{usage} requires non-empty content.")
        return parsed_symbol, parsed_content, path.strip() if path and path.strip() else None

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires symbol and content.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) < 2:
        raise ValueError(f"{usage} requires symbol and content.")
    if len(parts) > 3:
        raise ValueError("expected symbol, content, and optional path.")
    parsed_symbol = parts[0].strip()
    if not parsed_symbol:
        raise ValueError(f"{usage} requires a non-empty symbol.")
    if "\n" in parsed_symbol or "\r" in parsed_symbol:
        raise ValueError("symbol must be a single-line string.")
    parsed_content = decode_stdin_escapes(parts[1])
    if not parsed_content.strip():
        raise ValueError(f"{usage} requires non-empty content.")
    return parsed_symbol, parsed_content, parts[2] if len(parts) == 3 else None
