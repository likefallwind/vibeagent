from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex

from .cli_additional_directories import MAX_ADDITIONAL_DIRECTORIES, resolve_additional_directories
from .workspace_core import normalize_additional_roots


@dataclass(frozen=True)
class AdditionalDirectoryUpdate:
    directories: tuple[Path, ...]
    text: str
    changed: bool = False


def update_additional_directory_state(
    current: tuple[Path, ...],
    argument: str | None,
    *,
    project_root: Path,
) -> AdditionalDirectoryUpdate:
    root = project_root.resolve()
    if argument is None or argument.strip().lower() in {"list", "status"}:
        return AdditionalDirectoryUpdate(current, format_additional_directories(root, current))

    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return AdditionalDirectoryUpdate(current, f"Invalid /add-dir arguments: {error}")
    if not parts:
        return AdditionalDirectoryUpdate(current, format_additional_directories(root, current))

    operation = parts[0].lower()
    if operation in {"clear", "off", "none"}:
        if len(parts) != 1:
            return AdditionalDirectoryUpdate(current, "Usage: /add-dir clear")
        if not current:
            return AdditionalDirectoryUpdate(current, "No additional working directories are configured.")
        return AdditionalDirectoryUpdate((), "Cleared additional working directories.", changed=True)

    if operation in {"remove", "delete", "rm"}:
        if len(parts) != 2:
            return AdditionalDirectoryUpdate(current, "Usage: /add-dir remove <path>")
        candidate = _non_strict_path(parts[1], root)
        remaining = tuple(path for path in current if path != candidate)
        if remaining == current:
            return AdditionalDirectoryUpdate(current, f"Additional working directory is not registered: {candidate}")
        return AdditionalDirectoryUpdate(
            remaining,
            f"Removed additional working directory: {candidate}",
            changed=True,
        )

    if operation == "add":
        parts = parts[1:]
    if len(parts) != 1:
        return AdditionalDirectoryUpdate(current, "Usage: /add-dir <path>")

    try:
        candidate = resolve_additional_directories(parts, invocation_root=root)[0]
        updated = normalize_additional_roots(root, (*current, candidate))
    except (OSError, ValueError) as error:
        return AdditionalDirectoryUpdate(current, str(error))
    if updated == current:
        return AdditionalDirectoryUpdate(current, f"Working directory is already available: {candidate}")
    if len(updated) > MAX_ADDITIONAL_DIRECTORIES:
        return AdditionalDirectoryUpdate(
            current,
            f"/add-dir supports at most {MAX_ADDITIONAL_DIRECTORIES} additional directories per session.",
        )
    return AdditionalDirectoryUpdate(
        updated,
        f"Added working directory: {candidate}",
        changed=True,
    )


def format_additional_directories(project_root: Path, directories: tuple[Path, ...]) -> str:
    lines = [f"Primary working directory: {project_root.resolve()}"]
    if not directories:
        lines.append("Additional working directories: none")
    else:
        lines.append("Additional working directories:")
        lines.extend(f"  {path}" for path in directories)
    return "\n".join(lines)


def _non_strict_path(value: str, project_root: Path) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate.resolve(strict=False)


__all__ = [
    "AdditionalDirectoryUpdate",
    "format_additional_directories",
    "update_additional_directory_state",
]
