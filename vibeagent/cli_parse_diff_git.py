from __future__ import annotations

from collections.abc import Sequence
import shlex

from .cli_parse_core import duplicate_option_error, parse_interactive_nonnegative_option, parse_interactive_positive_option


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
            duplicate_error = duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error
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
