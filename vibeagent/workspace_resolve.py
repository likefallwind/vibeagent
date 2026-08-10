from __future__ import annotations

from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_paths import is_protected_project_path


WorkspaceBoundary = str | Path | RunWorkspace


def workspace_roots(boundary: WorkspaceBoundary) -> tuple[Path, ...]:
    if isinstance(boundary, RunWorkspace):
        return (boundary.root.resolve(), *(root.resolve() for root in boundary.additional_roots))
    return (Path(boundary).resolve(),)


def workspace_root_for_path(boundary: WorkspaceBoundary, path: Path) -> Path | None:
    resolved = path.resolve()
    matches = [
        root
        for root in workspace_roots(boundary)
        if resolved == root or root in resolved.parents
    ]
    return max(matches, key=lambda root: len(root.parts), default=None)


def display_workspace_path(workspace: RunWorkspace, path: Path) -> str:
    resolved = path.resolve()
    root = workspace_root_for_path(workspace, resolved)
    if root is None:
        return str(resolved)
    if root == workspace.root.resolve():
        return resolved.relative_to(root).as_posix() or "."
    return str(resolved)


def resolve_inside_run(boundary: WorkspaceBoundary, relative_path: str) -> Path:
    # Additional roots are available only when the caller carries a RunWorkspace.
    if not relative_path or not relative_path.strip():
        raise ValueError("Path must not be empty.")

    candidate = Path(relative_path)
    if candidate.is_absolute() and not isinstance(boundary, RunWorkspace):
        raise ValueError(f"Absolute paths are not allowed: {relative_path}")

    primary_root = workspace_roots(boundary)[0]
    resolved_path = candidate.resolve() if candidate.is_absolute() else (primary_root / candidate).resolve()
    matched_root = workspace_root_for_path(boundary, resolved_path)
    if matched_root is None:
        raise ValueError(f"Path escapes the project directory: {relative_path}")
    if is_protected_project_path(matched_root, resolved_path):
        raise ValueError(f"Path is protected: {relative_path}")

    return resolved_path


def resolve_mutation_path(boundary: WorkspaceBoundary, relative_path: str) -> Path:
    target = resolve_inside_run(boundary, relative_path)
    primary_root = workspace_roots(boundary)[0]
    candidate = Path(relative_path)
    lexical_path = candidate if candidate.is_absolute() else primary_root / candidate
    lexical = Path(lexical_path.anchor)
    for part in lexical_path.parts[1:]:
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
    path = relative_path or "."
    target = resolve_inside_run(workspace, path)
    if not target.exists():
        raise ValueError(f"Command cwd does not exist: {path}")
    if not target.is_dir():
        raise ValueError(f"Command cwd is not a directory: {path}")
    return target
