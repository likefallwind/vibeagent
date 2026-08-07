from __future__ import annotations
from pathlib import Path

from .workspace_code_intel import build_simple_diff
from .workspace_core import RunWorkspace
from .workspace_file_read import read_utf8_text_file
from .workspace_exact_edit_ops import (
    EditSpec,
    build_edit_file,
    build_multi_edit,
    edit_project_file,
    multi_edit_project_file,
    preview_edit_project_file,
    preview_multi_edit_project_file,
)
from .workspace_line_edit_ops import (
    build_insert_lines,
    build_replace_lines,
    insert_project_file_lines,
    preview_insert_project_file_lines,
    preview_replace_project_file_lines,
    replace_project_file_lines,
)
from .workspace_regex_edit_ops import (
    build_regex_replacement,
    preview_regex_replace_project_file,
    regex_replace_project_file,
)
from .workspace_resolve import resolve_mutation_path
from .workspace_write_edit_ops import (
    build_write_file,
    prepare_write_run_files,
    preview_write_run_file,
    preview_write_run_files,
    write_run_file,
    write_run_files,
)


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
    target = resolve_mutation_path(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    after = before + content
    if after == before:
        raise ValueError(f"Append made no changes to {relative_path}")
    return target, after, build_simple_diff(relative_path, before, after)
