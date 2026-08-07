from __future__ import annotations

from pathlib import Path

from .workspace_code_intel import build_simple_diff, split_replacement_lines
from .workspace_core import RunWorkspace
from .workspace_file_read import read_utf8_text_file
from .workspace_resolve import resolve_mutation_path


def replace_project_file_lines(
    workspace: RunWorkspace,
    relative_path: str,
    start_line: int,
    end_line: int,
    new_content: str,
) -> tuple[Path, str]:
    target, after, diff = build_replace_lines(workspace, relative_path, start_line, end_line, new_content)
    target.write_text(after, encoding="utf-8")
    return target, diff


def preview_replace_project_file_lines(
    workspace: RunWorkspace,
    relative_path: str,
    start_line: int,
    end_line: int,
    new_content: str,
) -> tuple[Path, str]:
    target, _after, diff = build_replace_lines(workspace, relative_path, start_line, end_line, new_content)
    return target, diff


def build_replace_lines(
    workspace: RunWorkspace,
    relative_path: str,
    start_line: int,
    end_line: int,
    new_content: str,
) -> tuple[Path, str, str]:
    if start_line < 1:
        raise ValueError("start_line must be at least 1.")
    if end_line < start_line:
        raise ValueError("end_line must be greater than or equal to start_line.")

    target = resolve_mutation_path(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    lines = before.splitlines(keepends=True)
    if end_line > len(lines):
        raise ValueError(f"end_line exceeds file line count: {len(lines)}")

    replacement = split_replacement_lines(new_content)
    updated_lines = lines[: start_line - 1] + replacement + lines[end_line:]
    after = "".join(updated_lines)
    if after == before:
        raise ValueError(f"Line replacement made no changes to {relative_path}")
    return target, after, build_simple_diff(relative_path, before, after)


def insert_project_file_lines(
    workspace: RunWorkspace,
    relative_path: str,
    line: int,
    content: str,
) -> tuple[Path, str]:
    target, after, diff = build_insert_lines(workspace, relative_path, line, content)
    target.write_text(after, encoding="utf-8")
    return target, diff


def preview_insert_project_file_lines(
    workspace: RunWorkspace,
    relative_path: str,
    line: int,
    content: str,
) -> tuple[Path, str]:
    target, _after, diff = build_insert_lines(workspace, relative_path, line, content)
    return target, diff


def build_insert_lines(
    workspace: RunWorkspace,
    relative_path: str,
    line: int,
    content: str,
) -> tuple[Path, str, str]:
    if line < 1:
        raise ValueError("line must be at least 1.")
    if content == "":
        raise ValueError("content must not be empty.")

    target = resolve_mutation_path(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    lines = before.splitlines(keepends=True)
    if line > len(lines) + 1:
        raise ValueError(f"line exceeds append position: {len(lines) + 1}")

    insertion = split_replacement_lines(content)
    updated_lines = lines[: line - 1] + insertion + lines[line - 1 :]
    after = "".join(updated_lines)
    if after == before:
        raise ValueError(f"Line insertion made no changes to {relative_path}")
    return target, after, build_simple_diff(relative_path, before, after)
