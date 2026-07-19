from __future__ import annotations

import shlex


def usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def validate_diff_hunks_limits(usage: str, max_hunks: int, max_lines_per_hunk: int) -> str | None:
    if max_hunks < 1:
        return usage_error(usage, "max_hunks must be at least 1.")
    if max_hunks > 500:
        return usage_error(usage, "max_hunks must be at most 500.")
    if max_lines_per_hunk < 1:
        return usage_error(usage, "max_lines_per_hunk must be at least 1.")
    if max_lines_per_hunk > 500:
        return usage_error(usage, "max_lines_per_hunk must be at most 500.")
    return None


def validate_diff_contexts_limits(
    usage: str,
    context_lines: int,
    max_hunks: int,
    max_bytes_per_context: int,
) -> str | None:
    if context_lines < 0:
        return usage_error(usage, "context_lines must be at least 0.")
    if context_lines > 500:
        return usage_error(usage, "context_lines must be at most 500.")
    if max_hunks < 1:
        return usage_error(usage, "max_hunks must be at least 1.")
    if max_hunks > 500:
        return usage_error(usage, "max_hunks must be at most 500.")
    if max_bytes_per_context < 1_000:
        return usage_error(usage, "max_bytes_per_context must be at least 1000.")
    if max_bytes_per_context > 200_000:
        return usage_error(usage, "max_bytes_per_context must be at most 200000.")
    return None


def parse_diff_argument(argument: str | None) -> tuple[bool, str | None] | None:
    if not argument:
        return False, None
    try:
        parts = shlex.split(argument)
    except ValueError:
        return None
    staged = False
    paths: list[str] = []
    for part in parts:
        if part in {"--staged", "--cached"}:
            staged = True
        elif part == "--":
            continue
        elif part.startswith("-"):
            return None
        else:
            paths.append(part)
    if len(paths) > 1:
        return None
    return staged, paths[0] if paths else None


def clip_with_flag(value: str, max_chars: int) -> tuple[str, bool]:
    if len(value) <= max_chars:
        return value.rstrip(), False
    return f"{value[:max_chars].rstrip()}\n[diff output truncated]", True


def indent_block(value: str, spaces: int = 2) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in value.splitlines())
