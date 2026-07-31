from __future__ import annotations

import shlex

from .cli_parse_core import parse_interactive_nonnegative_option, parse_interactive_positive_option


def _duplicate_option_error(kwargs: dict[str, int], keyword: str, flag: str, usage: str) -> str | None:
    if keyword in kwargs:
        return f"{usage}\n  error: provide {flag} at most once."
    return None


def parse_interactive_test_paths_argument(
    argument: str | None,
    usage: str,
    include_max_commands: bool = False,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    if not argument:
        return None, {}, None, False
    option_specs = {
        "--max-paths": "max_paths",
        "--max-candidates": "max_candidates",
    }
    if include_max_commands:
        option_specs["--max-commands"] = "max_commands"
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in option_specs:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int] = {}
    path_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            path_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            keyword = option_specs[flag]
            duplicate_error = _duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        path_parts.append(part)
        index += 1

    path_argument = shlex.join(path_parts) if path_parts else None
    return path_argument, kwargs, None, True


def parse_interactive_python_symbol_argument(
    argument: str | None,
    *,
    command_name: str,
    include_max_lines: bool = False,
    include_context: bool = False,
) -> tuple[str | None, str | None, dict[str, int], str | None, bool]:
    options = "[--path PATH] [--max-matches N]"
    if include_max_lines:
        options += " [--max-lines N]"
    if include_context:
        options += " [--context-lines N] [--max-bytes N]"
    usage = f"Usage: /{command_name} {options} -- <symbol> [path]"
    if not argument:
        return None, None, {}, None, False

    value_options: dict[str, tuple[str, str]] = {
        "--path": ("path", "string"),
        "--max-matches": ("max_matches", "positive"),
    }
    if include_max_lines:
        value_options["--max-lines"] = ("max_lines", "positive")
    if include_context:
        value_options["--context-lines"] = ("context_lines", "nonnegative")
        value_options["--max-bytes"] = ("max_bytes_per_context", "positive")

    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in value_options):
            return None, None, {}, f"{usage}\n  error: {error}", True
        return None, None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in value_options:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, None, {}, None, False

    symbol_parts: list[str] = []
    kwargs: dict[str, int] = {}
    path: str | None = None
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            symbol_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in value_options:
            keyword, value_type = value_options[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if value_type == "positive":
                value, error = parse_interactive_positive_option(flag, raw_value)
            elif value_type == "nonnegative":
                value, error = parse_interactive_nonnegative_option(flag, raw_value)
            else:
                if raw_value is None:
                    value, error = None, f"{flag} requires a value."
                elif raw_value == "":
                    value, error = None, f"{flag} must be a non-empty string."
                else:
                    value, error = raw_value, None
            if error:
                return None, None, {}, f"{usage}\n  error: {error}", True
            if keyword == "path":
                if path is not None:
                    return None, None, {}, f"{usage}\n  error: provide {flag} at most once.", True
                path = str(value)
            else:
                duplicate_error = _duplicate_option_error(kwargs, keyword, flag, usage)
                if duplicate_error:
                    return None, None, {}, duplicate_error, True
                kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, None, {}, f"{usage}\n  error: Unknown option: {part}", True
        symbol_parts.append(part)
        index += 1

    if not symbol_parts:
        return None, path, kwargs, f"{usage}\n  error: symbol is required.", True
    if len(symbol_parts) > 2:
        return None, None, {}, usage, True
    if len(symbol_parts) == 2:
        if path is not None:
            return None, None, {}, f"{usage}\n  error: path can only be provided once.", True
        path = symbol_parts[1]
    return symbol_parts[0], path, kwargs, None, True


def _parse_interactive_path_options_argument(
    argument: str | None,
    *,
    usage: str,
    option_specs: dict[str, str],
) -> tuple[str | None, dict[str, int], str | None, bool]:
    if not argument:
        return None, {}, None, False

    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in option_specs:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    path_parts: list[str] = []
    kwargs: dict[str, int] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            path_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            keyword = option_specs[flag]
            duplicate_error = _duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        path_parts.append(part)
        index += 1

    if len(path_parts) > 1:
        return None, {}, usage, True
    return (path_parts[0] if path_parts else None), kwargs, None, True


def parse_interactive_python_deps_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    return _parse_interactive_path_options_argument(
        argument,
        usage="Usage: /python-deps [--max-files N] [--max-imports N] -- [path]",
        option_specs={
            "--max-files": "max_files",
            "--max-imports": "max_imports",
        },
    )


def parse_interactive_python_call_graph_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    return _parse_interactive_path_options_argument(
        argument,
        usage="Usage: /python-call-graph [--max-files N] [--max-edges N] -- [path]",
        option_specs={
            "--max-files": "max_files",
            "--max-edges": "max_edges",
        },
    )
