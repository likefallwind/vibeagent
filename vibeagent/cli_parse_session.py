from __future__ import annotations

import shlex

from .cli_parse_core import parse_interactive_nonnegative_option, parse_interactive_positive_option
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
        "[--max-output-chars N] [--no-failed] [--no-pending] [--continue-on-failure]"
    )
    if not argument:
        return None, {}, None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, {}, f"{usage}\n  error: {error}"
    run_id: str | None = None
    kwargs: dict[str, int | bool] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in {"--max-checks", "--timeout-ms", "--max-output-chars"}:
            keyword = {
                "--max-checks": "max_checks",
                "--timeout-ms": "timeout_ms",
                "--max-output-chars": "max_output_chars",
            }[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            kwargs[keyword] = int(value)
            continue
        if part == "--no-failed":
            kwargs["include_failed"] = False
            index += 1
            continue
        if part == "--no-pending":
            kwargs["include_pending"] = False
            index += 1
            continue
        if part == "--continue-on-failure":
            kwargs["stop_on_failure"] = False
            index += 1
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
