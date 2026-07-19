from __future__ import annotations

from pathlib import Path

from .workspace_resolve import resolve_inside_run


def read_project_stdin_file(project_root: str | Path, relative_path: str, option_name: str) -> str:
    path = resolve_inside_run(project_root, relative_path)
    if not path.exists():
        raise ValueError(f"{option_name} does not exist: {relative_path}")
    if not path.is_file():
        raise ValueError(f"{option_name} is not a file: {relative_path}")
    return path.read_text(encoding="utf-8")
