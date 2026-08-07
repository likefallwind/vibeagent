from __future__ import annotations

import shlex

from .cli_parse_core import duplicate_option_error, parse_interactive_nonnegative_option, parse_interactive_positive_option
from .cli_parse_read_paths import parse_interactive_read_path_options
from .cli_parse_read_tree_symbols import parse_interactive_symbols_argument, parse_interactive_tree_argument


def parse_interactive_output_analysis_argument(
    argument: str | None,
    usage: str,
    include_max_diagnostics: bool = False,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    if not argument:
        return None, {}, None, False
    option_specs: dict[str, tuple[str, str]] = {
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    if include_max_diagnostics:
        option_specs["--max-diagnostics"] = ("max_diagnostics", "positive")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return None, {}, f"{usage}\n  error: {error}", True
        return argument, {}, None, False

    uses_named_options = False
    if parts:
        first_flag = parts[0].split("=", 1)[0] if parts[0].startswith("--") else parts[0]
        uses_named_options = parts[0] == "--" or parts[0].startswith("--") or first_flag in option_specs
    if not uses_named_options:
        return argument, {}, None, False

    kwargs: dict[str, int] = {}
    text_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            text_parts.extend(parts[index + 1 :])
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
        text_parts.extend(parts[index:])
        break

    text = shlex.join(text_parts).strip() if text_parts else None
    if not text:
        return None, {}, f"{usage}\n  error: text is required.", True
    return text, kwargs, None, True


def parse_interactive_max_bytes_argument(
    argument: str | None,
    usage: str,
    keyword: str,
    required_message: str,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    if not argument:
        return None, {}, None, False
    option_specs = {"--max-bytes": keyword}
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
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            positional.extend(parts[index + 1 :])
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
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: {required_message}", True
    argument_text = shlex.join(positional)
    return argument_text, kwargs, None, True


def parse_interactive_read_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | bool], str | None, bool]:
    usage = "Usage: /read [--max-bytes N] [--line-numbers] -- <path> [start[:end]]"
    paths, kwargs, error, handled = parse_interactive_read_path_options(
        argument,
        usage,
        "max_bytes",
        "path is required.",
    )
    if paths is None:
        return None, kwargs, error, handled
    return " ".join(shlex.quote(part) for part in paths), kwargs, None, True


def parse_interactive_tail_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    return parse_interactive_max_bytes_argument(
        argument,
        "Usage: /tail [--max-bytes N] -- <path> [lines]",
        "max_bytes",
        "path is required.",
    )


def parse_interactive_around_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    return parse_interactive_max_bytes_argument(
        argument,
        "Usage: /around [--max-bytes N] -- <path> <line> [context-lines]",
        "max_bytes",
        "path and line are required.",
    )


def parse_interactive_around_many_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    return parse_interactive_max_bytes_argument(
        argument,
        "Usage: /around-many [--max-bytes N] -- <path:line[:context-lines]...>",
        "max_bytes_per_context",
        "at least one context is required.",
    )


def parse_interactive_read_ranges_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    return parse_interactive_max_bytes_argument(
        argument,
        "Usage: /read-ranges [--max-bytes N] -- <path:start[:end]...>",
        "max_bytes_per_range",
        "at least one range is required.",
    )


def parse_interactive_read_files_argument(
    argument: str | None,
) -> tuple[list[str] | None, dict[str, int | bool], str | None, bool]:
    usage = "Usage: /read-files [--max-bytes N] [--line-numbers] -- <path...>"
    return parse_interactive_read_path_options(
        argument,
        usage,
        "max_bytes_per_file",
        "at least one path is required.",
    )
