from __future__ import annotations

from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_paths import should_ignore_path
from .workspace_resolve import display_workspace_path, resolve_inside_run, workspace_root_for_path


def list_files(root: str | Path) -> list[str]:
    # Enumerate all files in deterministic order so prompt diffs stay stable.
    root_path = Path(root).resolve()
    files = [
        path.relative_to(root_path).as_posix()
        for path in root_path.rglob("*")
        if not path.is_symlink() and path.is_file() and not should_ignore_path(root_path, path)
    ]
    return sorted(files)


def list_search_files(workspace: RunWorkspace, relative_path: str | None) -> list[str]:
    if not relative_path:
        return list_files(workspace.root)

    base = resolve_inside_run(workspace, relative_path)
    access_root = workspace_root_for_path(workspace, base)
    if access_root is None:
        raise ValueError(f"Path escapes the project directory: {relative_path}")
    if not base.exists():
        raise ValueError(f"Path does not exist: {relative_path}")
    if base.is_file():
        return [display_workspace_path(workspace, base)]
    return [
        display_workspace_path(workspace, path)
        for path in sorted(base.rglob("*"))
        if not path.is_symlink() and path.is_file() and not should_ignore_path(access_root, path)
    ]
