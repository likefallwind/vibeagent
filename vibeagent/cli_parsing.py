from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
import shlex


def build_diff_argument(diff_argument: str | None, staged: bool, task_parts: Sequence[str]) -> str | None:
    parts: list[str] = []
    if staged:
        parts.append("--staged")
    if diff_argument:
        parts.append(diff_argument)
    parts.extend(task_parts)
    return " ".join(parts) if parts else None


def parse_interactive_diff_argument(argument: str | None) -> tuple[str | None, int, str | None]:
    usage = "Usage: /diff [--staged|--cached] [--max-chars N] [path]"
    if not argument:
        return None, 12_000, None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, 12_000, f"{usage}\n  error: {error}"

    diff_parts: list[str] = []
    max_chars = 12_000
    index = 0
    while index < len(parts):
        part = parts[index]
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag == "--max-chars":
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            value, error = parse_interactive_positive_option("--max-chars", raw_value)
            if error:
                return None, 12_000, f"{usage}\n  error: {error}"
            max_chars = int(value)
            continue
        diff_parts.append(part)
        index += 1
    return " ".join(diff_parts) if diff_parts else None, max_chars, None


def parse_interactive_diff_hunks_argument(argument: str | None) -> tuple[str | None, dict[str, int], str | None]:
    usage = "Usage: /diff-hunks [--staged|--cached] [--max-hunks N] [--max-lines N] [path]"
    option_specs = {
        "--max-hunks": ("max_hunks", False),
        "--max-lines": ("max_lines_per_hunk", False),
    }
    return parse_interactive_diff_detail_argument(argument, usage, option_specs)


def parse_interactive_diff_contexts_argument(argument: str | None) -> tuple[str | None, dict[str, int], str | None]:
    usage = "Usage: /diff-contexts [--staged|--cached] [--context-lines N] [--max-hunks N] [--max-bytes N] [path]"
    option_specs = {
        "--context-lines": ("context_lines", True),
        "--max-hunks": ("max_hunks", False),
        "--max-bytes": ("max_bytes_per_context", False),
    }
    return parse_interactive_diff_detail_argument(argument, usage, option_specs)


def parse_interactive_diff_detail_argument(
    argument: str | None,
    usage: str,
    option_specs: dict[str, tuple[str, bool]],
) -> tuple[str | None, dict[str, int], str | None]:
    if not argument:
        return None, {}, None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, {}, f"{usage}\n  error: {error}"

    diff_parts: list[str] = []
    kwargs: dict[str, int] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            keyword, allow_zero = option_specs[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            parser = parse_interactive_nonnegative_option if allow_zero else parse_interactive_positive_option
            value, error = parser(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--") and part not in {"--staged", "--cached", "--"}:
            return None, {}, f"{usage}\n  error: Unknown option: {part}"
        diff_parts.append(part)
        index += 1
    return " ".join(diff_parts) if diff_parts else None, kwargs, None


def build_switch_argument(branch: str, create: bool) -> str:
    return f"--create {branch}" if create else branch


def build_stash_argument(message: str, include_untracked: bool) -> str:
    parts: list[str] = []
    if include_untracked:
        parts.append("--include-untracked")
    if message:
        parts.append(message)
    return " ".join(parts)


def parse_executable_flag_values(values: Sequence[str], flag: str) -> tuple[str, str | None]:
    if len(values) not in (1, 2):
        raise ValueError(f"{flag} expects PATH and optional true|false.")
    return values[0], values[1] if len(values) == 2 else None


def parse_multi_edit_flag_values(values: Sequence[str], flag: str) -> tuple[str, list[str]]:
    if len(values) < 3:
        raise ValueError(f"{flag} expects PATH and at least one OLD NEW pair.")
    if (len(values) - 1) % 2 != 0:
        raise ValueError(f"{flag} expects OLD NEW pairs after PATH.")
    return values[0], list(values[1:])


def parse_cli_json_value(value: str) -> object:
    try:
        return json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON value is invalid: {error.msg}") from error


def build_focused_tests_kwargs(args: argparse.Namespace) -> dict[str, int]:
    kwargs: dict[str, int] = {}
    if args.focused_tests_max_paths is not None:
        kwargs["max_paths"] = args.focused_tests_max_paths
    if args.focused_tests_max_candidates is not None:
        kwargs["max_candidates"] = args.focused_tests_max_candidates
    if args.focused_tests_max_commands is not None:
        kwargs["max_commands"] = args.focused_tests_max_commands
    return kwargs


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def nonnegative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def timeout_ms(value: str) -> int:
    parsed = positive_int(value)
    if parsed < 100:
        raise argparse.ArgumentTypeError("must be at least 100")
    return parsed


def parse_interactive_positive_option(flag: str, value: str | None) -> tuple[int | None, str | None]:
    if value is None:
        return None, f"{flag} requires a value."
    try:
        return positive_int(value), None
    except argparse.ArgumentTypeError as error:
        return None, f"{flag} {error}."


def parse_interactive_nonnegative_option(flag: str, value: str | None) -> tuple[int | None, str | None]:
    if value is None:
        return None, f"{flag} requires a value."
    try:
        return nonnegative_int(value), None
    except argparse.ArgumentTypeError as error:
        return None, f"{flag} {error}."


def parse_interactive_timeout_option(flag: str, value: str | None) -> tuple[int | None, str | None]:
    if value is None:
        return None, f"{flag} requires a value."
    try:
        return timeout_ms(value), None
    except argparse.ArgumentTypeError as error:
        return None, f"{flag} {error}."


def parse_interactive_transcript_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None]:
    usage = "Usage: /transcript [run-id] [--max-events N] [--max-text N]"
    if not argument:
        return None, {}, None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, {}, f"{usage}\n  error: {error}"
    run_id: str | None = None
    kwargs: dict[str, int] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--max-events":
            raw_value = parts[index + 1] if index + 1 < len(parts) else None
            value, error = parse_interactive_positive_option(part, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            kwargs["max_events"] = int(value)
            index += 2
            continue
        if part.startswith("--max-events="):
            value, error = parse_interactive_positive_option("--max-events", part.split("=", 1)[1])
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            kwargs["max_events"] = int(value)
            index += 1
            continue
        if part == "--max-text":
            raw_value = parts[index + 1] if index + 1 < len(parts) else None
            value, error = parse_interactive_positive_option(part, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            kwargs["max_text"] = int(value)
            index += 2
            continue
        if part.startswith("--max-text="):
            value, error = parse_interactive_positive_option("--max-text", part.split("=", 1)[1])
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            kwargs["max_text"] = int(value)
            index += 1
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}"
        if run_id is not None:
            return None, {}, usage
        run_id = part
        index += 1
    return run_id, kwargs, None


def parse_interactive_session_search_argument(
    argument: str | None,
) -> tuple[str | None, str | None, dict[str, int | bool], str | None]:
    usage = "Usage: /session-search [--run run-id] [--max-matches N] [--case-sensitive] [--max-text N] <query>"
    if not argument:
        return None, None, {}, usage
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, None, {}, f"{usage}\n  error: {error}"
    run_id: str | None = None
    query_parts: list[str] = []
    kwargs: dict[str, int | bool] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            query_parts.extend(parts[index + 1 :])
            break
        if part == "--run":
            if index + 1 >= len(parts):
                return None, None, {}, f"{usage}\n  error: --run requires a value."
            run_id = parts[index + 1]
            index += 2
            continue
        if part.startswith("--run="):
            run_id = part.split("=", 1)[1]
            index += 1
            continue
        if part == "--max-matches":
            raw_value = parts[index + 1] if index + 1 < len(parts) else None
            value, error = parse_interactive_positive_option(part, raw_value)
            if error:
                return None, None, {}, f"{usage}\n  error: {error}"
            kwargs["max_matches"] = int(value)
            index += 2
            continue
        if part.startswith("--max-matches="):
            value, error = parse_interactive_positive_option("--max-matches", part.split("=", 1)[1])
            if error:
                return None, None, {}, f"{usage}\n  error: {error}"
            kwargs["max_matches"] = int(value)
            index += 1
            continue
        if part == "--max-text":
            raw_value = parts[index + 1] if index + 1 < len(parts) else None
            value, error = parse_interactive_positive_option(part, raw_value)
            if error:
                return None, None, {}, f"{usage}\n  error: {error}"
            kwargs["max_text"] = int(value)
            index += 2
            continue
        if part.startswith("--max-text="):
            value, error = parse_interactive_positive_option("--max-text", part.split("=", 1)[1])
            if error:
                return None, None, {}, f"{usage}\n  error: {error}"
            kwargs["max_text"] = int(value)
            index += 1
            continue
        if part == "--case-sensitive":
            kwargs["case_sensitive"] = True
            index += 1
            continue
        if part.startswith("--"):
            return None, None, {}, f"{usage}\n  error: Unknown option: {part}"
        query_parts.append(part)
        index += 1
    query = " ".join(query_parts).strip()
    if not query:
        return None, run_id, kwargs, usage
    return query, run_id, kwargs, None


def parse_interactive_session_detail_argument(
    argument: str | None,
    usage: str,
    option_specs: dict[str, tuple[str, bool]],
) -> tuple[str | None, dict[str, int], str | None]:
    if not argument:
        return None, {}, None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, {}, f"{usage}\n  error: {error}"
    run_id: str | None = None
    kwargs: dict[str, int] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            keyword, allow_zero = option_specs[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            parser = parse_interactive_nonnegative_option if allow_zero else parse_interactive_positive_option
            value, error = parser(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}"
        if run_id is not None:
            return None, {}, usage
        run_id = part
        index += 1
    return run_id, kwargs, None


def parse_interactive_process_output_argument(
    argument: str | None,
    usage: str,
    option_specs: dict[str, tuple[str, bool]],
) -> tuple[str | None, dict[str, int], str | None]:
    if not argument:
        return None, {}, usage
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, {}, f"{usage}\n  error: {error}"
    process_id: str | None = None
    legacy_max_chars: int | None = None
    kwargs: dict[str, int] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            keyword, allow_zero = option_specs[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            parser = parse_interactive_nonnegative_option if allow_zero else parse_interactive_positive_option
            value, error = parser(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}"
        if process_id is None:
            process_id = part
            index += 1
            continue
        if legacy_max_chars is None:
            value, error = parse_interactive_positive_option("[chars]", part)
            if error:
                return None, {}, f"{usage}\n  error: invalid max chars: {part}"
            legacy_max_chars = int(value)
            kwargs["max_output_chars"] = legacy_max_chars
            index += 1
            continue
        return None, {}, usage
    if process_id is None:
        return None, {}, f"{usage}\n  error: process id is required."
    return process_id, kwargs, None


def parse_interactive_port_argument(
    argument: str | None,
) -> tuple[int | None, dict[str, int | str], str | None, bool]:
    usage = "Usage: /port <port> [host] [timeout-ms] [--host HOST] [--timeout-ms N]"
    if not argument:
        return None, {}, None, False
    value_options = {
        "--host": ("host", "string"),
        "--timeout-ms": ("timeout_ms", "timeout"),
    }
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in value_options):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in value_options:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int | str] = {}
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            positional.extend(parts[index + 1 :])
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
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
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
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: port is required.", True
    if len(positional) > 1:
        return None, {}, usage, True
    value, error = parse_interactive_positive_option("[port]", positional[0])
    if error:
        return None, {}, f"{usage}\n  error: invalid port: {positional[0]}", True
    return int(value), kwargs, None, True


def parse_interactive_http_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | str | bool], str | None, bool]:
    usage = "Usage: /http <url> [contains] [--timeout-ms N] [--max-body-chars N] [--contains TEXT] [--regex]"
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-body-chars": ("max_body_chars", "positive"),
        "--contains": ("contains", "string"),
    }
    bool_options = {"--regex": "regex"}
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
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            positional.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            kwargs[bool_options[flag]] = True
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
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "positive":
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
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: url is required.", True
    url = positional[0]
    positional_contains = " ".join(positional[1:]).strip() or None
    if positional_contains is not None:
        if "contains" in kwargs:
            return None, {}, f"{usage}\n  error: contains can only be provided once.", True
        kwargs["contains"] = positional_contains
    return url, kwargs, None, True


def parse_interactive_http_fetch_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    usage = "Usage: /http-fetch <url> [--timeout-ms N] [--max-body-chars N]"
    if not argument:
        return None, {}, None, False
    option_specs = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-body-chars": ("max_body_chars", "positive"),
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
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            positional.extend(parts[index + 1 :])
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
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            else:
                value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: url is required.", True
    if len(positional) > 1:
        return None, {}, usage, True
    return positional[0], kwargs, None, True


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
            kwargs[option_specs[flag]] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        path_parts.append(part)
        index += 1

    path_argument = shlex.join(path_parts) if path_parts else None
    return path_argument, kwargs, None, True


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
            kwargs[option_specs[flag]] = int(value)
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
    if not argument:
        return None, {}, None, False
    option_specs = {"--max-bytes": "max_bytes"}
    boolean_options = {"--line-numbers": "show_line_numbers"}
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
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            positional.extend(parts[index + 1 :])
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
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: path is required.", True
    return " ".join(shlex.quote(part) for part in positional), kwargs, None, True


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
    if not argument:
        return None, {}, None, False
    option_specs = {"--max-bytes": "max_bytes_per_file"}
    boolean_options = {"--line-numbers": "show_line_numbers"}
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
    paths: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            paths.extend(parts[index + 1 :])
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
        paths.append(part)
        index += 1

    if not paths:
        return None, {}, f"{usage}\n  error: at least one path is required.", True
    return paths, kwargs, None, True


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
            kwargs[option_specs[flag]] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        paths.append(part)
        index += 1

    if not paths:
        return None, {}, f"{usage}\n  error: at least one path is required.", True
    return paths, kwargs, None, True


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
                path = str(value)
            else:
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


def parse_interactive_wait_process_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | str | bool], str | None, bool]:
    usage = (
        "Usage: /wait-process <id> [timeout-ms] [chars] "
        "[--timeout-ms N] [--max-chars N] [--stdout TEXT] [--stderr TEXT] [--regex]"
    )
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--stdout": ("stdout_contains", "string"),
        "--stderr": ("stderr_contains", "string"),
    }
    bool_options = {"--regex": "regex"}
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
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            positional.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            kwargs[bool_options[flag]] = True
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
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "positive":
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
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: process id is required.", True
    if len(positional) > 3:
        return None, {}, usage, True
    process_id = positional[0]
    if len(positional) >= 2:
        value, error = parse_interactive_timeout_option("[timeout-ms]", positional[1])
        if error:
            return None, {}, f"{usage}\n  error: invalid timeout ms: {positional[1]}", True
        kwargs["timeout_ms"] = int(value)
    if len(positional) == 3:
        value, error = parse_interactive_positive_option("[chars]", positional[2])
        if error:
            return None, {}, f"{usage}\n  error: invalid max chars: {positional[2]}", True
        kwargs["max_output_chars"] = int(value)
    return process_id, kwargs, None, True


def parse_interactive_run_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | str | bool], str | None, bool]:
    usage = (
        "Usage: /run [--timeout-ms N] [--max-chars N] [--cwd PATH] "
        "[--output-contexts] [--output-diagnostics] [--context-lines N] "
        "[--max-diagnostics N] [--max-contexts N] [--max-bytes N] -- <cmd>"
    )
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--cwd": ("cwd", "string"),
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-diagnostics": ("max_diagnostics", "positive"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    bool_options = {
        "--output-contexts": "extract_output_contexts",
        "--output-diagnostics": "extract_output_diagnostics",
    }
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return argument, {}, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in recognized_flags:
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return argument, {}, None, False

    kwargs: dict[str, int | str | bool] = {}
    command_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            command_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            kwargs[bool_options[flag]] = True
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
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "nonnegative":
                value, error = parse_interactive_nonnegative_option(flag, raw_value)
            elif value_type == "positive":
                value, error = parse_interactive_positive_option(flag, raw_value)
            else:
                if raw_value is None:
                    value, error = None, f"{flag} requires a value."
                else:
                    value, error = raw_value, None
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = value
            continue
        command_parts.extend(parts[index:])
        break

    command = shlex.join(command_parts).strip()
    if not command:
        return None, {}, f"{usage}\n  error: command is required.", True
    return command, kwargs, None, True


def parse_interactive_run_sequence_argument(
    argument: str | None,
) -> tuple[list[str] | None, dict[str, int | str | bool], str | None, bool]:
    usage = (
        "Usage: /run-seq [--timeout-ms N] [--max-chars N] [--cwd PATH] "
        "[--continue-on-failure] [--output-contexts] [--output-diagnostics] "
        "[--context-lines N] [--max-diagnostics N] [--max-contexts N] "
        "[--max-bytes N] -- <cmd> ;; <cmd>"
    )
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--cwd": ("cwd", "string"),
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-diagnostics": ("max_diagnostics", "positive"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    bool_options = {
        "--output-contexts": ("extract_output_contexts", True),
        "--output-diagnostics": ("extract_output_diagnostics", True),
        "--continue-on-failure": ("stop_on_failure", False),
        "--stop-on-failure": ("stop_on_failure", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in recognized_flags:
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int | str | bool] = {}
    command_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            command_parts.extend(parts[index + 1 :])
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
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "nonnegative":
                value, error = parse_interactive_nonnegative_option(flag, raw_value)
            elif value_type == "positive":
                value, error = parse_interactive_positive_option(flag, raw_value)
            else:
                if raw_value is None:
                    value, error = None, f"{flag} requires a value."
                else:
                    value, error = raw_value, None
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = value
            continue
        command_parts.extend(parts[index:])
        break

    commands: list[str] = []
    current: list[str] = []
    for part in command_parts:
        if part == ";;":
            command = shlex.join(current).strip()
            if command:
                commands.append(command)
            current = []
            continue
        current.append(part)
    command = shlex.join(current).strip()
    if command:
        commands.append(command)
    if not commands:
        return None, {}, f"{usage}\n  error: at least one command is required.", True
    if len(commands) > 10:
        return None, {}, f"{usage}\n  error: expected at most 10 commands.", True
    return commands, kwargs, None, True


def parse_interactive_run_focused_tests_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | bool], str | None, bool]:
    usage = (
        "Usage: /run-focused-tests [--max-paths N] [--max-candidates N] [--max-commands N] "
        "[--timeout-ms N] [--max-chars N] "
        "[--continue-on-failure] [--output-contexts] [--output-diagnostics] "
        "[--context-lines N] [--max-diagnostics N] [--max-contexts N] "
        "[--max-bytes N] -- [path...]"
    )
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--max-paths": ("max_paths", "positive"),
        "--max-candidates": ("max_candidates", "positive"),
        "--max-commands": ("max_commands", "positive"),
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-diagnostics": ("max_diagnostics", "positive"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    bool_options = {
        "--output-contexts": ("extract_output_contexts", True),
        "--output-diagnostics": ("extract_output_diagnostics", True),
        "--continue-on-failure": ("stop_on_failure", False),
        "--stop-on-failure": ("stop_on_failure", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return argument, {}, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in recognized_flags:
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return argument, {}, None, False

    kwargs: dict[str, int | bool] = {}
    path_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            path_parts.extend(parts[index + 1 :])
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
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "nonnegative":
                value, error = parse_interactive_nonnegative_option(flag, raw_value)
            else:
                value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = int(value)
            continue
        path_parts.extend(parts[index:])
        break

    focused_argument = shlex.join(path_parts).strip() or None
    return focused_argument, kwargs, None, True


def parse_interactive_run_suggested_checks_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | bool], str | None, bool]:
    usage = (
        "Usage: /run-suggested-checks [--max-checks N] [--timeout-ms N] [--max-chars N] "
        "[--continue-on-failure] [--output-contexts] [--output-diagnostics] "
        "[--context-lines N] [--max-diagnostics N] [--max-contexts N] "
        "[--max-bytes N] -- [max]"
    )
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--max-checks": ("max_checks", "positive"),
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-diagnostics": ("max_diagnostics", "positive"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    bool_options = {
        "--output-contexts": ("extract_output_contexts", True),
        "--output-diagnostics": ("extract_output_diagnostics", True),
        "--continue-on-failure": ("stop_on_failure", False),
        "--stop-on-failure": ("stop_on_failure", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return argument, {}, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in recognized_flags:
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return argument, {}, None, False

    kwargs: dict[str, int | bool] = {}
    max_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            max_parts.extend(parts[index + 1 :])
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
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "nonnegative":
                value, error = parse_interactive_nonnegative_option(flag, raw_value)
            else:
                value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = int(value)
            continue
        max_parts.extend(parts[index:])
        break

    selected_max = shlex.join(max_parts).strip() or None
    if selected_max and len(max_parts) != 1:
        return None, {}, f"{usage}\n  error: expected at most one max value.", True
    if selected_max and "max_checks" in kwargs:
        return None, {}, f"{usage}\n  error: provide either --max-checks or trailing max, not both.", True
    return selected_max, kwargs, None, True


def parse_interactive_cwd_command_argument(
    argument: str | None,
    usage: str,
) -> tuple[str | None, str | None, str | None, bool]:
    if not argument:
        return None, None, None, False
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if "--cwd" in argument:
            return None, None, f"{usage}\n  error: {error}", True
        return argument, None, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag == "--cwd":
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return argument, None, None, False

    cwd: str | None = None
    command_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            command_parts.extend(parts[index + 1 :])
            break
        if part == "--cwd" or part.startswith("--cwd="):
            if cwd is not None:
                return None, None, f"{usage}\n  error: --cwd can only be provided once.", True
            if part.startswith("--cwd="):
                cwd = part.split("=", 1)[1]
                index += 1
            else:
                if index + 1 >= len(parts):
                    return None, None, f"{usage}\n  error: --cwd requires a value.", True
                cwd = parts[index + 1]
                index += 2
            continue
        command_parts.extend(parts[index:])
        break

    command = shlex.join(command_parts).strip()
    if not command:
        return None, cwd, f"{usage}\n  error: command is required.", True
    return command, cwd, None, True


def parse_interactive_check_run_sequence_argument(
    argument: str | None,
) -> tuple[list[str] | None, str | None, str | None, bool]:
    usage = "Usage: /check-run-seq [--cwd PATH] -- <cmd> ;; <cmd>"
    if not argument:
        return None, None, None, False
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if "--cwd" in argument:
            return None, None, f"{usage}\n  error: {error}", True
        return None, None, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag == "--cwd":
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return None, None, None, False

    cwd: str | None = None
    command_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            command_parts.extend(parts[index + 1 :])
            break
        if part == "--cwd" or part.startswith("--cwd="):
            if cwd is not None:
                return None, None, f"{usage}\n  error: --cwd can only be provided once.", True
            if part.startswith("--cwd="):
                cwd = part.split("=", 1)[1]
                index += 1
            else:
                if index + 1 >= len(parts):
                    return None, None, f"{usage}\n  error: --cwd requires a value.", True
                cwd = parts[index + 1]
                index += 2
            continue
        command_parts.extend(parts[index:])
        break

    commands: list[str] = []
    current: list[str] = []
    for part in command_parts:
        if part == ";;":
            command = shlex.join(current).strip()
            if command:
                commands.append(command)
            current = []
            continue
        current.append(part)
    command = shlex.join(current).strip()
    if command:
        commands.append(command)
    if not commands:
        return None, cwd, f"{usage}\n  error: at least one command is required.", True
    if len(commands) > 10:
        return None, cwd, f"{usage}\n  error: expected at most 10 commands.", True
    return commands, cwd, None, True

