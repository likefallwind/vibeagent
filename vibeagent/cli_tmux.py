from __future__ import annotations

from collections.abc import Mapping, Sequence
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

from .cli_worktree import CliWorktree


def normalize_tmux_arguments(argv: Sequence[str]) -> list[str]:
    """Keep a bare --tmux from consuming the positional task as its mode."""
    normalized: list[str] = []
    options_finished = False
    for value in argv:
        if value == "--":
            options_finished = True
        normalized.append(
            "--tmux=auto" if value == "--tmux" and not options_finished else value
        )
    return normalized


def ensure_tmux_available() -> None:
    if shutil.which("tmux") is None:
        raise ValueError("--tmux requires the tmux executable on PATH.")


def launch_tmux_worktree_session(
    argv: Sequence[str],
    worktree: CliWorktree,
    *,
    mode: str,
    environ: Mapping[str, str] | None = None,
) -> int:
    if mode not in {"auto", "classic"}:
        raise ValueError(f"Unsupported tmux mode: {mode}")
    env = os.environ if environ is None else environ
    command = ["tmux"]
    if mode == "auto" and env.get("TERM_PROGRAM") == "iTerm.app":
        command.append("-CC")
    child_command = [
        sys.executable,
        "-m",
        "vibeagent",
        *_build_child_arguments(argv, worktree.root),
    ]
    command.extend(
        [
            "new-session",
            "-s",
            _tmux_session_name(worktree.name),
            "-c",
            str(worktree.root),
            shlex.join(child_command),
        ]
    )
    return subprocess.run(command, cwd=worktree.root, check=False).returncode


def _build_child_arguments(argv: Sequence[str], worktree_root: Path) -> list[str]:
    child: list[str] = ["--cwd", str(worktree_root)]
    values = list(argv)
    index = 0
    while index < len(values):
        value = values[index]
        if value == "--":
            child.extend(values[index:])
            break
        if value in {"--tmux", "--cwd", "--worktree", "-w"}:
            index += 1
            if value != "--tmux" and index < len(values) and not values[index].startswith("-"):
                index += 1
            continue
        if value.startswith(("--tmux=", "--cwd=", "--worktree=")) or (
            value.startswith("-w") and value != "-w"
        ):
            index += 1
            continue
        child.append(value)
        index += 1
    return child


def _tmux_session_name(worktree_name: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "-", worktree_name).strip("-")
    return f"vibeagent-{safe_name or 'worktree'}"[:80]
