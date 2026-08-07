from __future__ import annotations

from pathlib import Path

from .workspace_code_intel import (
    code_language_for_path,
    read_code_outline,
    read_python_symbol_outline,
    supports_code_outline_path,
)
from .workspace_core import RunWorkspace


def build_repo_map(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_depth: int = 3,
    max_files: int = 80,
    max_symbols: int = 120,
) -> dict[str, object]:
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1.")
    if max_depth > 10:
        raise ValueError("max_depth must be at most 10.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    if max_symbols < 1:
        raise ValueError("max_symbols must be at least 1.")
    if max_symbols > 500:
        raise ValueError("max_symbols must be at most 500.")

    from .workspace_path_discovery import list_project_files, list_project_tree

    path_label = relative_path or "."
    tree_entries, total_tree_entries = list_project_tree(
        workspace,
        relative_path,
        max_depth=max_depth,
        max_entries=max_files,
    )
    files, total_files = list_project_files(workspace, relative_path, max_files=max_files)

    python_files: list[dict[str, object]] = []
    used_symbols = 0
    symbols_truncated = False
    for file in files:
        if not file.endswith(".py"):
            continue
        remaining = max_symbols - used_symbols
        if remaining <= 0:
            symbols_truncated = True
            break
        try:
            outline = read_python_symbol_outline(workspace, file, max_symbols=remaining)
            symbols = list(outline["symbols"])
            used_symbols += len(symbols)
            python_files.append(
                {
                    "path": file,
                    "ok": True,
                    "imports": list(outline["imports"]),
                    "symbols": symbols,
                    "message": str(outline["message"]),
                }
            )
            if used_symbols >= max_symbols and len(symbols) == remaining:
                symbols_truncated = True
        except ValueError as error:
            python_files.append(
                {
                    "path": file,
                    "ok": False,
                    "imports": [],
                    "symbols": [],
                    "message": str(error),
                }
            )

    code_files: list[dict[str, object]] = []
    used_code_symbols = 0
    code_symbols_truncated = False
    for file in files:
        if not supports_code_outline_path(file):
            continue
        remaining = max_symbols - used_code_symbols
        if remaining <= 0:
            code_symbols_truncated = True
            break
        try:
            outline = read_code_outline(workspace, file, max_symbols=remaining)
            symbols = list(outline["symbols"])
            used_code_symbols += len(symbols)
            code_files.append(
                {
                    "path": file,
                    "ok": True,
                    "language": str(outline["language"]),
                    "imports": list(outline["imports"]),
                    "symbols": symbols,
                    "message": str(outline["message"]),
                }
            )
            if used_code_symbols >= max_symbols and len(symbols) == remaining:
                code_symbols_truncated = True
        except ValueError as error:
            code_files.append(
                {
                    "path": file,
                    "ok": False,
                    "language": code_language_for_path(Path(file)),
                    "imports": [],
                    "symbols": [],
                    "message": str(error),
                }
            )

    truncated = len(tree_entries) < total_tree_entries or len(files) < total_files or symbols_truncated or code_symbols_truncated
    return {
        "path": path_label,
        "tree": tree_entries,
        "files": files,
        "python_files": python_files,
        "code_files": code_files,
        "total_tree_entries": total_tree_entries,
        "total_files": total_files,
        "truncated": truncated,
        "message": (
            f"Mapped {len(files)}/{total_files} file(s), "
            f"{len(python_files)} Python file(s), and {len(code_files)} source file(s)."
        ),
    }
