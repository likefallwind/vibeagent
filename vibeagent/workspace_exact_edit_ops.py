from __future__ import annotations

from pathlib import Path

from .workspace_code_intel import build_simple_diff
from .workspace_core import RunWorkspace
from .workspace_file_read import read_utf8_text_file
from .workspace_resolve import resolve_mutation_path


def edit_project_file(workspace: RunWorkspace, relative_path: str, old: str, new: str) -> tuple[Path, str]:
    target, updated, diff = build_edit_file(workspace, relative_path, old, new)
    target.write_text(updated, encoding="utf-8")
    return target, diff


def preview_edit_project_file(workspace: RunWorkspace, relative_path: str, old: str, new: str) -> tuple[Path, str]:
    target, _updated, diff = build_edit_file(workspace, relative_path, old, new)
    return target, diff


def build_edit_file(workspace: RunWorkspace, relative_path: str, old: str, new: str) -> tuple[Path, str, str]:
    target = resolve_mutation_path(workspace, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    content = read_utf8_text_file(target, relative_path)
    if old not in content:
        raise ValueError(f"Old text was not found in {relative_path}")
    updated = content.replace(old, new, 1)
    if updated == content:
        raise ValueError(f"Edit made no changes to {relative_path}")
    return target, updated, build_simple_diff(relative_path, content, updated)


EditSpec = tuple[str, str] | tuple[str, str, bool]


def multi_edit_project_file(workspace: RunWorkspace, relative_path: str, edits: list[EditSpec]) -> tuple[Path, str]:
    target, updated, diff = build_multi_edit(workspace, relative_path, edits)
    target.write_text(updated, encoding="utf-8")
    return target, diff


def preview_multi_edit_project_file(workspace: RunWorkspace, relative_path: str, edits: list[EditSpec]) -> tuple[Path, str]:
    target, _updated, diff = build_multi_edit(workspace, relative_path, edits)
    return target, diff


def build_multi_edit(workspace: RunWorkspace, relative_path: str, edits: list[EditSpec]) -> tuple[Path, str, str]:
    target = resolve_mutation_path(workspace, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    if not edits:
        raise ValueError("At least one edit is required.")

    content = read_utf8_text_file(target, relative_path)
    updated = content
    for index, edit in enumerate(edits, start=1):
        old, new = edit[0], edit[1]
        replace_all = len(edit) > 2 and edit[2]
        if old == "":
            raise ValueError(f"Edit {index} old text must not be empty.")
        if old not in updated:
            raise ValueError(f"Edit {index} old text was not found in {relative_path}")
        updated = updated.replace(old, new) if replace_all else updated.replace(old, new, 1)

    if updated == content:
        raise ValueError(f"Edits made no changes to {relative_path}")
    return target, updated, build_simple_diff(relative_path, content, updated)
