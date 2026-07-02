from __future__ import annotations

from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_paths import is_protected_project_path


def resolve_inside_run(root: str | Path, relative_path: str) -> Path:
    # Enforce relative paths to prevent reads/writes outside the active project directory.
    if not relative_path or not relative_path.strip():
        raise ValueError("Path must not be empty.")

    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {relative_path}")

    resolved_root = Path(root).resolve()
    resolved_path = (resolved_root / candidate).resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise ValueError(f"Path escapes the project directory: {relative_path}")
    if is_protected_project_path(resolved_root, resolved_path):
        raise ValueError(f"Path is protected: {relative_path}")

    return resolved_path


def resolve_mutation_path(root: str | Path, relative_path: str) -> Path:
    target = resolve_inside_run(root, relative_path)
    resolved_root = Path(root).resolve()
    candidate = Path(relative_path)
    lexical = resolved_root
    for part in candidate.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            lexical = lexical.parent
            continue
        lexical = lexical / part
        if lexical.is_symlink():
            raise ValueError(f"Path uses a symbolic link: {relative_path}")
    return target


def resolve_command_cwd(workspace: RunWorkspace, relative_path: str | None) -> Path:
    target = resolve_inside_run(workspace.root, relative_path or ".")
    if not target.exists():
        raise ValueError(f"Command cwd does not exist: {relative_path or '.'}")
    if not target.is_dir():
        raise ValueError(f"Command cwd is not a directory: {relative_path or '.'}")
    return target

