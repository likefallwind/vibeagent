from __future__ import annotations

import shlex

from .cli_parse_core import (
    parse_interactive_nonnegative_option,
    parse_interactive_positive_option,
    parse_interactive_timeout_option,
)
from .session_input import normalize_optional_run_id


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
        run_id = normalize_optional_run_id(part)
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
            run_id = normalize_optional_run_id(parts[index + 1])
            index += 2
            continue
        if part.startswith("--run="):
            run_id = normalize_optional_run_id(part.split("=", 1)[1])
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
            if keyword in kwargs:
                return None, {}, f"{usage}\n  error: provide {flag} at most once."
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}"
        if run_id is not None:
            return None, {}, usage
        run_id = normalize_optional_run_id(part)
        index += 1
    return run_id, kwargs, None


def parse_interactive_run_session_verification_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | bool], str | None]:
    usage = (
        "Usage: /run-session-verification [run-id] [--max-checks N] [--timeout-ms N] "
        "[--max-output-chars N] [--no-failed] [--no-pending] [--continue-on-failure] "
        "[--output-contexts] [--output-diagnostics] [--context-lines N] "
        "[--max-diagnostics N] [--max-contexts N] [--max-bytes N]"
    )
    if not argument:
        return None, {}, None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, {}, f"{usage}\n  error: {error}"
    run_id: str | None = None
    kwargs: dict[str, int | bool] = {}
    value_options: dict[str, tuple[str, str]] = {
        "--max-checks": ("max_checks", "positive"),
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-output-chars": ("max_output_chars", "positive"),
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-diagnostics": ("max_diagnostics", "positive"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    bool_options = {
        "--no-failed": ("include_failed", False),
        "--no-pending": ("include_pending", False),
        "--continue-on-failure": ("stop_on_failure", False),
        "--stop-on-failure": ("stop_on_failure", True),
        "--output-contexts": ("extract_output_contexts", True),
        "--output-diagnostics": ("extract_output_diagnostics", True),
    }
    index = 0
    while index < len(parts):
        part = parts[index]
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value."
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
                return None, {}, f"{usage}\n  error: {error}"
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}"
        if run_id is not None:
            return None, {}, usage
        run_id = normalize_optional_run_id(part)
        index += 1
    if kwargs.get("include_failed") is False and kwargs.get("include_pending") is False:
        return None, {}, f"{usage}\n  error: --no-failed and --no-pending cannot be used together."
    return run_id, kwargs, None
