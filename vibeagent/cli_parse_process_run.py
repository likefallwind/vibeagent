from __future__ import annotations

from pathlib import Path
import shlex

from .cli_parse_core import (
    parse_interactive_max_chars_option,
    parse_interactive_positive_option,
    parse_interactive_timeout_option,
)
from .cli_process_stdin import read_project_stdin_file


def _duplicate_option_error(kwargs: dict[str, int | str | bool], keyword: str, flag: str, usage: str) -> str | None:
    if keyword in kwargs:
        return f"{usage}\n  error: provide {flag} at most once."
    return None


def parse_interactive_wait_process_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | str | bool], str | None]:
    usage = (
        "Usage: /wait-process <id> [timeout-ms] [chars] "
        "[--timeout-ms N] [--max-chars N] [--stdout TEXT] [--stderr TEXT] [--regex]"
    )
    if not argument:
        return None, {}, None
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
            return None, {}, f"{usage}\n  error: {error}"
        return None, {}, None

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
                return None, {}, f"{usage}\n  error: {flag} does not take a value."
            keyword = bool_options[flag]
            duplicate_error = _duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error
            kwargs[keyword] = True
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
            elif keyword == "max_output_chars":
                value, error = parse_interactive_max_chars_option(flag, raw_value)
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
                return None, {}, f"{usage}\n  error: {error}"
            duplicate_error = _duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error
            kwargs[keyword] = value
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}"
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: process id is required."
    if len(positional) > 3:
        return None, {}, usage
    process_id = positional[0]
    if len(positional) >= 2:
        if "timeout_ms" in kwargs:
            return None, {}, f"{usage}\n  error: provide either --timeout-ms or positional timeout-ms, not both."
        value, error = parse_interactive_timeout_option("[timeout-ms]", positional[1])
        if error:
            return None, {}, f"{usage}\n  error: invalid timeout ms: {positional[1]}"
        kwargs["timeout_ms"] = int(value)
    if len(positional) == 3:
        if "max_output_chars" in kwargs:
            return None, {}, f"{usage}\n  error: provide either --max-chars or positional chars, not both."
        value, error = parse_interactive_max_chars_option("[chars]", positional[2])
        if error:
            return None, {}, f"{usage}\n  error: invalid max chars: {positional[2]}"
        kwargs["max_output_chars"] = int(value)
    return process_id, kwargs, None


def parse_interactive_write_process_argument(
    argument: str | None,
    *,
    project_root: str | Path = ".",
    usage: str = "Usage: /write-process <id> <text> [--stdin-file PATH]",
) -> tuple[str | None, str | None, str | None]:
    if not argument:
        return None, None, f"{usage}\n  error: process id is required."
    if "--stdin-file" not in argument:
        return None, None, None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, None, f"{usage}\n  error: {error}"

    process_id: str | None = None
    content_parts: list[str] = []
    stdin_file: str | None = None
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            content_parts.extend(parts[index + 1 :])
            break
        if part == "--stdin-file" or part.startswith("--stdin-file="):
            if stdin_file is not None:
                return None, None, f"{usage}\n  error: --stdin-file can only be provided once."
            if part.startswith("--stdin-file="):
                stdin_file = part.split("=", 1)[1]
                index += 1
            else:
                if index + 1 >= len(parts):
                    return None, None, f"{usage}\n  error: --stdin-file requires a value."
                stdin_file = parts[index + 1]
                index += 2
            if stdin_file == "":
                return None, None, f"{usage}\n  error: --stdin-file must be a non-empty path."
            continue
        if part.startswith("--"):
            return None, None, f"{usage}\n  error: Unknown option: {part}"
        if process_id is None:
            process_id = part
        else:
            content_parts.append(part)
        index += 1

    if not process_id:
        return None, None, f"{usage}\n  error: process id is required."
    content = " ".join(content_parts) if content_parts else None
    if stdin_file is not None and content is not None:
        return None, None, f"{usage}\n  error: text and --stdin-file cannot be used together."
    if stdin_file is not None:
        try:
            content = read_project_stdin_file(project_root, stdin_file, "--stdin-file")
        except ValueError as error:
            return None, None, f"{usage}\n  error: {error}"
    if content is None or content == "":
        return None, None, f"{usage}\n  error: stdin text is required."
    return process_id, content.replace("\\r", "\r").replace("\\n", "\n").replace("\\t", "\t"), None
