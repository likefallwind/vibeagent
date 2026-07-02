from __future__ import annotations

import shlex

from .cli_parse_core import parse_interactive_nonnegative_option, parse_interactive_positive_option


def parse_interactive_search_argument(
    argument: str | None,
    *,
    include_max_bytes: bool,
) -> tuple[str | None, dict[str, int | str | bool], str | None, bool]:
    usage = (
        "Usage: /search-contexts [--path PATH] [--max-matches N] [--regex] [--ignore-case] "
        "[--context-lines N] [--max-bytes N] -- <query>"
        if include_max_bytes
        else "Usage: /search [--path PATH] [--max-matches N] [--regex] [--ignore-case] [--context-lines N] -- <query>"
    )
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--path": ("path", "string"),
        "--max-matches": ("max_matches", "positive"),
        "--context-lines": ("context_lines", "nonnegative"),
    }
    if include_max_bytes:
        value_options["--max-bytes"] = ("max_bytes_per_context", "positive")
    bool_options = {
        "--regex": ("regex", True),
        "--ignore-case": ("case_sensitive", False),
        "--case-insensitive": ("case_sensitive", False),
        "--case-sensitive": ("case_sensitive", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in recognized_flags:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int | str | bool] = {}
    query_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            query_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            keyword, value = bool_options[flag]
            kwargs[keyword] = value
            index += 1
            continue
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
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = value
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        query_parts.append(part)
        index += 1

    query = " ".join(query_parts).strip()
    if not query:
        return None, {}, f"{usage}\n  error: query is required.", True
    return query, kwargs, None, True


def parse_interactive_find_files_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | str | bool], str | None, bool]:
    usage = "Usage: /find-files [--path PATH] [--max-matches N] [--regex] [--case-sensitive] [--include-dirs] -- <query>"
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--path": ("path", "string"),
        "--max-matches": ("max_matches", "positive"),
    }
    bool_options = {
        "--regex": ("regex", True),
        "--case-sensitive": ("case_sensitive", True),
        "--case-insensitive": ("case_sensitive", False),
        "--include-dirs": ("include_dirs", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in recognized_flags:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int | str | bool] = {}
    query_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            query_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            keyword, value = bool_options[flag]
            kwargs[keyword] = value
            index += 1
            continue
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
            else:
                if raw_value is None:
                    value, error = None, f"{flag} requires a value."
                elif raw_value == "":
                    value, error = None, f"{flag} must be a non-empty string."
                else:
                    value, error = raw_value, None
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = value
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        query_parts.append(part)
        index += 1

    query = " ".join(query_parts).strip()
    if not query:
        return None, {}, f"{usage}\n  error: query is required.", True
    return query, kwargs, None, True


def parse_interactive_overview_argument(
    argument: str | None,
) -> tuple[dict[str, int], str | None, bool]:
    usage = "Usage: /overview [--max-files N] [--max-commands N] [--max-checks N]"
    if not argument:
        return {}, None, False
    option_specs = {
        "--max-files": "max_files",
        "--max-commands": "max_commands",
        "--max-checks": "max_checks",
    }
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return {}, f"{usage}\n  error: {error}", True
        return {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in option_specs:
                uses_named_options = True
                break
    if not uses_named_options:
        return {}, None, False

    kwargs: dict[str, int] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            if parts[index + 1 :]:
                return {}, usage, True
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
                return {}, f"{usage}\n  error: {error}", True
            kwargs[option_specs[flag]] = int(value)
            continue
        if part.startswith("--"):
            return {}, f"{usage}\n  error: Unknown option: {part}", True
        return {}, usage, True
    return kwargs, None, True


def parse_interactive_repo_map_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    usage = "Usage: /repo-map [path] [--max-depth N] [--max-files N] [--max-symbols N]"
    if not argument:
        return None, {}, None, False
    option_specs = {
        "--max-depth": ("max_depth", "nonnegative"),
        "--max-files": ("max_files", "positive"),
        "--max-symbols": ("max_symbols", "positive"),
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


def parse_interactive_glob_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | bool], str | None, bool]:
    usage = "Usage: /glob [--max-matches N] [--include-dirs] -- <pattern>"
    if not argument:
        return None, {}, None, False
    option_specs = {"--max-matches": "max_matches"}
    boolean_options = {"--include-dirs": "include_dirs"}
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs | boolean_options):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in option_specs or flag in boolean_options:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int | bool] = {}
    pattern_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            pattern_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in boolean_options:
            if "=" in part:
                raw_value = part.split("=", 1)[1].strip().lower()
                if raw_value not in {"1", "true", "yes", "on", "0", "false", "no", "off"}:
                    return None, {}, f"{usage}\n  error: {flag} must be a boolean.", True
                kwargs[boolean_options[flag]] = raw_value in {"1", "true", "yes", "on"}
            else:
                kwargs[boolean_options[flag]] = True
            index += 1
            continue
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
            kwargs[option_specs[flag]] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        pattern_parts.append(part)
        index += 1

    pattern = " ".join(pattern_parts).strip()
    if not pattern:
        return None, {}, f"{usage}\n  error: pattern is required.", True
    return pattern, kwargs, None, True


def parse_interactive_todos_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    usage = "Usage: /todos [--max-items N] [--max-files N] -- [path]"
    if not argument:
        return None, {}, None, False
    option_specs = {
        "--max-items": "max_items",
        "--max-files": "max_files",
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
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[option_specs[flag]] = int(value)
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


def parse_interactive_option_limit_argument(
    argument: str | None,
    usage: str,
    option_specs: dict[str, str],
) -> tuple[dict[str, int], str | None, bool]:
    if not argument:
        return {}, None, False
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return {}, f"{usage}\n  error: {error}", True
        return {}, None, False

    uses_named_options = False
    for part in parts:
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if part.startswith("--") or flag in option_specs:
            uses_named_options = True
            break
    if not uses_named_options:
        return {}, usage, True

    kwargs: dict[str, int] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
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
                return {}, f"{usage}\n  error: {error}", True
            kwargs[option_specs[flag]] = int(value)
            continue
        return {}, f"{usage}\n  error: Unknown option: {part}", True

    return kwargs, None, True


def parse_interactive_commands_argument(
    argument: str | None,
) -> tuple[dict[str, int], str | None, bool]:
    return parse_interactive_option_limit_argument(
        argument,
        "Usage: /commands [--max-commands N] [--max-files N]",
        {"--max-commands": "max_commands", "--max-files": "max_files"},
    )


def parse_interactive_manifests_argument(
    argument: str | None,
) -> tuple[dict[str, int], str | None, bool]:
    return parse_interactive_option_limit_argument(
        argument,
        "Usage: /manifests [--max-files N] [--max-items N]",
        {"--max-files": "max_files", "--max-items": "max_items"},
    )


def parse_interactive_instructions_argument(
    argument: str | None,
) -> tuple[dict[str, int], str | None, bool]:
    return parse_interactive_option_limit_argument(
        argument,
        "Usage: /instructions [--max-files N] [--max-bytes N]",
        {"--max-files": "max_files", "--max-bytes": "max_bytes"},
    )
