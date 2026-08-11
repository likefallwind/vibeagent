from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex


@dataclass(frozen=True)
class InteractiveDirectoryChange:
    target: Path | None
    text: str
    changed: bool = False


def resolve_interactive_directory_change(
    project_root: Path,
    argument: str | None,
) -> InteractiveDirectoryChange:
    if not argument:
        return InteractiveDirectoryChange(None, "Usage: /cd <path>")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return InteractiveDirectoryChange(None, f"Invalid /cd path: {error}")
    if len(parts) != 1:
        return InteractiveDirectoryChange(None, "Usage: /cd <path>")

    candidate = Path(parts[0]).expanduser()
    if not candidate.is_absolute():
        candidate = project_root / candidate
    try:
        target = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        return InteractiveDirectoryChange(None, f"Cannot change directory: {error}")
    if not target.is_dir():
        return InteractiveDirectoryChange(None, f"Cannot change directory: not a directory: {target}")

    current = project_root.resolve()
    if target == current:
        return InteractiveDirectoryChange(target, f"Already using project directory: {target}")
    return InteractiveDirectoryChange(target, f"Changed project directory to: {target}", changed=True)


__all__ = ["InteractiveDirectoryChange", "resolve_interactive_directory_change"]
