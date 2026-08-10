from __future__ import annotations

from pathlib import Path

from .workspace_code_intel import build_simple_diff
from .workspace_core import RunWorkspace
from .workspace_file_read import read_utf8_text_file
from .workspace_resolve import resolve_mutation_path


def append_project_file(workspace: RunWorkspace, relative_path: str, content: str) -> tuple[Path, str]:
    target, after, diff = build_append_file(workspace, relative_path, content)
    target.write_text(after, encoding="utf-8")
    return target, diff


def preview_append_project_file(workspace: RunWorkspace, relative_path: str, content: str) -> tuple[Path, str]:
    target, _after, diff = build_append_file(workspace, relative_path, content)
    return target, diff


def build_append_file(workspace: RunWorkspace, relative_path: str, content: str) -> tuple[Path, str, str]:
    if content == "":
        raise ValueError("content must not be empty.")
    target = resolve_mutation_path(workspace, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    after = before + content
    if after == before:
        raise ValueError(f"Append made no changes to {relative_path}")
    return target, after, build_simple_diff(relative_path, before, after)
