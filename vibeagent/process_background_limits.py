from __future__ import annotations

from collections.abc import Mapping, Sequence
import os
from pathlib import Path
import sys


BACKGROUND_TASKS_DISABLED_ENV = "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS"
MAX_BACKGROUND_OUTPUT_BYTES = 5 * 1024**3


def background_tasks_disabled(environment: Mapping[str, str] | None = None) -> bool:
    source = os.environ if environment is None else environment
    return source.get(BACKGROUND_TASKS_DISABLED_ENV) == "1"


def prepare_background_output_launch(
    argv: Sequence[str],
    *,
    stdout_path: Path,
    stderr_path: Path,
    exit_code_path: Path,
    max_output_bytes: int = MAX_BACKGROUND_OUTPUT_BYTES,
) -> tuple[str, ...]:
    if max_output_bytes < 1:
        raise ValueError("Background output limit must be positive.")
    return (
        sys.executable,
        "-m",
        "vibeagent.process_output_supervisor",
        str(max_output_bytes),
        stdout_path.as_posix(),
        stderr_path.as_posix(),
        exit_code_path.as_posix(),
        "--",
        *tuple(argv),
    )


def format_output_bytes(value: int) -> str:
    for suffix, size in (("GiB", 1024**3), ("MiB", 1024**2), ("KiB", 1024)):
        if value >= size and value % size == 0:
            return f"{value // size} {suffix}"
    return f"{value} bytes"


def background_output_exceeded_message(max_output_bytes: int) -> str:
    return (
        "Command terminated after combined background output exceeded "
        f"{format_output_bytes(max_output_bytes)}."
    )


__all__ = [
    "BACKGROUND_TASKS_DISABLED_ENV",
    "MAX_BACKGROUND_OUTPUT_BYTES",
    "background_output_exceeded_message",
    "background_tasks_disabled",
    "format_output_bytes",
    "prepare_background_output_launch",
]
