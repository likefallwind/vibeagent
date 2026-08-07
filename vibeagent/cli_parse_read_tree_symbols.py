from __future__ import annotations

import shlex

from .cli_parse_core import duplicate_option_error, parse_interactive_nonnegative_option, parse_interactive_positive_option


def parse_interactive_tree_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    usage = "Usage: /tree [path] [--max-depth N] [--max-entries N]"
    if not argument:
        return None, {}, None, False
    option_specs = {
        "--max-depth": ("max_depth", "nonnegative"),
        "--max-entries": ("max_entries", "positive"),
    }
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
            keyword, value_type = option_specs[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            parser = parse_interactive_nonnegative_option if value_type == "nonnegative" else parse_interactive_positive_option
            value, error = parser(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            duplicate_error = duplicate_option_error(kwargs, keyword, flag, usage)
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
    path = path_parts[0].strip() if path_parts else None
    if path == "":
        path = None
    return path, kwargs, None, True


def parse_interactive_symbols_argument(
    argument: str | None,
) -> tuple[list[str] | None, dict[str, int], str | None, bool]:
    usage = "Usage: /symbols [--max-symbols N] -- <path...>"
    if not argument:
        return None, {}, None, False
    option_specs = {"--max-symbols": "max_symbols"}
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
    paths: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            paths.extend(parts[index + 1 :])
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
            duplicate_error = duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        paths.append(part)
        index += 1

    if not paths:
        return None, {}, f"{usage}\n  error: at least one path is required.", True
    return paths, kwargs, None, True
