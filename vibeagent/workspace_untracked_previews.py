from __future__ import annotations

from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_file_read import (
    detect_binary_file,
    read_utf8_text_file,
    truncate_utf8_text_bytes,
)
from .workspace_resolve import resolve_inside_run


def read_untracked_file_previews(
    workspace: RunWorkspace,
    files: list[dict[str, object]],
    max_files: int = 200,
    max_bytes: int = 4000,
) -> dict[str, object]:
    paths = [
        str(item["path"])
        for item in files
        if bool(item.get("untracked")) and isinstance(item.get("path"), str)
    ]
    previews: list[dict[str, object]] = []
    for relative_path in paths[:max_files]:
        candidate = Path(relative_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            previews.append(
                {
                    "path": relative_path,
                    "size_bytes": 0,
                    "is_binary": False,
                    "content": "",
                    "truncated": False,
                    "message": f"Unsafe untracked path preview omitted: {relative_path}",
                }
            )
            continue
        lexical_target = workspace.root / candidate
        if lexical_target.is_symlink():
            try:
                size_bytes = lexical_target.lstat().st_size
            except OSError:
                size_bytes = 0
            previews.append(
                {
                    "path": relative_path,
                    "size_bytes": size_bytes,
                    "is_binary": False,
                    "content": "",
                    "truncated": False,
                    "message": "Untracked symlink preview omitted.",
                }
            )
            continue
        target = resolve_inside_run(workspace.root, relative_path)
        if not target.is_file():
            previews.append(
                {
                    "path": relative_path,
                    "size_bytes": 0,
                    "is_binary": False,
                    "content": "",
                    "truncated": False,
                    "message": f"Untracked path is not a file: {relative_path}",
                }
            )
            continue
        size_bytes = target.stat().st_size
        if detect_binary_file(target):
            previews.append(
                {
                    "path": relative_path,
                    "size_bytes": size_bytes,
                    "is_binary": True,
                    "content": "",
                    "truncated": False,
                    "message": "Binary untracked file preview omitted.",
                }
            )
            continue
        content = read_utf8_text_file(target, relative_path)
        content_bytes = len(content.encode("utf-8"))
        truncated = content_bytes > max_bytes
        if truncated:
            content = f"{truncate_utf8_text_bytes(content, max_bytes)}\n[file truncated]"
        previews.append(
            {
                "path": relative_path,
                "size_bytes": size_bytes,
                "is_binary": False,
                "content": content,
                "truncated": truncated,
                "message": "Read untracked file preview.",
            }
        )

    return {
        "previews": previews,
        "total": len(paths),
        "truncated": len(paths) > len(previews) or any(bool(item["truncated"]) for item in previews),
    }
