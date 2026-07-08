from __future__ import annotations

import re
import stat as stat_module
from pathlib import Path

from .workspace_code_intel import build_simple_diff
from .workspace_core import RunWorkspace
from .workspace_file_read import read_utf8_text_file
from .workspace_file_path_ops import (
    build_delete_file,
    build_delete_files,
    copy_project_file,
    copy_project_files,
    delete_project_file,
    delete_project_files,
    move_project_file,
    move_project_files,
    prepare_project_file_copies,
    prepare_project_file_transfer,
    prepare_project_file_transfers,
    preview_copy_project_file,
    preview_copy_project_files,
    preview_delete_project_file,
    preview_delete_project_files,
    preview_move_project_file,
    preview_move_project_files,
)
from .workspace_json_edit_ops import (
    add_json_pointer_value,
    apply_json_patch_operation,
    build_json_patch,
    build_json_remove,
    build_json_set,
    format_json_document,
    json_patch_project_file,
    json_remove_project_file,
    json_set_project_file,
    parse_json_array_index,
    parse_json_pointer,
    preview_json_patch_project_file,
    preview_json_remove_project_file,
    preview_json_set_project_file,
    remove_json_pointer_value,
    set_json_pointer_value,
)
from .workspace_directory_ops import (
    copy_project_directories,
    copy_project_directory,
    create_project_directories,
    create_project_directory,
    delete_project_empty_directories,
    delete_project_empty_directory,
    move_project_directories,
    move_project_directory,
    prepare_project_directory_copy,
    prepare_project_directory_move,
    preview_copy_project_directories,
    preview_copy_project_directory,
    preview_create_project_directories,
    preview_create_project_directory,
    preview_delete_project_empty_directories,
    preview_delete_project_empty_directory,
    preview_move_project_directories,
    preview_move_project_directory,
    validate_project_directory_transfer_batch,
)
from .workspace_text_edit_ops import (
    append_project_file,
    build_append_file,
    build_edit_file,
    build_insert_lines,
    build_multi_edit,
    build_regex_replacement,
    build_replace_lines,
    build_write_file,
    edit_project_file,
    insert_project_file_lines,
    multi_edit_project_file,
    prepare_write_run_files,
    preview_append_project_file,
    preview_edit_project_file,
    preview_insert_project_file_lines,
    preview_multi_edit_project_file,
    preview_regex_replace_project_file,
    preview_replace_project_file_lines,
    preview_write_run_file,
    preview_write_run_files,
    regex_replace_project_file,
    replace_project_file_lines,
    write_run_file,
    write_run_files,
)
from .workspace_resolve import resolve_mutation_path


def set_project_file_executable(workspace: RunWorkspace, relative_path: str, executable: bool = True) -> tuple[Path, int, int]:
    target, before, after = preview_set_project_file_executable(workspace, relative_path, executable=executable)
    if after != before:
        target.chmod(after)
    return target, before, after


def preview_set_project_file_executable(workspace: RunWorkspace, relative_path: str, executable: bool = True) -> tuple[Path, int, int]:
    target = resolve_mutation_path(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = stat_module.S_IMODE(target.stat().st_mode)
    if executable:
        after = before | stat_module.S_IXUSR | stat_module.S_IXGRP | stat_module.S_IXOTH
    else:
        after = before & ~(stat_module.S_IXUSR | stat_module.S_IXGRP | stat_module.S_IXOTH)
    return target, before, after


def patch_project_file(workspace: RunWorkspace, relative_path: str, patch: str) -> tuple[Path, str]:
    target = resolve_mutation_path(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    if not patch.strip():
        raise ValueError("Patch must not be empty.")

    before = read_utf8_text_file(target, relative_path)
    after = apply_unified_patch(before, patch)
    if after == before:
        raise ValueError(f"Patch made no changes to {relative_path}")
    target.write_text(after, encoding="utf-8")
    return target, build_simple_diff(relative_path, before, after)


def check_project_patch(workspace: RunWorkspace, relative_path: str, patch: str) -> tuple[Path, str]:
    target = resolve_mutation_path(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    if not patch.strip():
        raise ValueError("Patch must not be empty.")

    before = read_utf8_text_file(target, relative_path)
    after = apply_unified_patch(before, patch)
    if after == before:
        raise ValueError(f"Patch made no changes to {relative_path}")
    return target, build_simple_diff(relative_path, before, after)


def patch_project_files(workspace: RunWorkspace, patch: str) -> tuple[list[Path], str]:
    if not patch.strip():
        raise ValueError("Patch must not be empty.")

    file_patches = split_unified_patch_by_file(patch)
    if not file_patches:
        raise ValueError("Patch must include file headers for at least one file.")

    prepared: list[tuple[Path, str, str, str, str]] = []
    seen: set[str] = set()
    for relative_path, file_patch, operation in file_patches:
        if relative_path in seen:
            raise ValueError(f"Patch contains duplicate file section: {relative_path}")
        seen.add(relative_path)

        target = resolve_mutation_path(workspace.root, relative_path)
        if operation == "create":
            if target.exists():
                raise ValueError(f"File already exists: {relative_path}")
            before = ""
        elif not target.is_file():
            raise ValueError(f"File does not exist: {relative_path}")
        else:
            before = read_utf8_text_file(target, relative_path)
        after = apply_unified_patch(before, file_patch)
        if after == before:
            raise ValueError(f"Patch made no changes to {relative_path}")
        if operation == "delete" and after:
            raise ValueError(f"Patch delete file section must remove all content: {relative_path}")
        prepared.append((target, relative_path, before, after, operation))

    for target, _relative_path, _before, after, operation in prepared:
        if operation == "create":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(after, encoding="utf-8")
        elif operation == "delete":
            target.unlink()
        else:
            target.write_text(after, encoding="utf-8")

    diff = "".join(
        build_simple_diff(relative_path, before, after)
        for _target, relative_path, before, after, _operation in prepared
    )
    return [target for target, _relative_path, _before, _after, _operation in prepared], diff


def check_project_patches(workspace: RunWorkspace, patch: str) -> tuple[list[Path], str]:
    if not patch.strip():
        raise ValueError("Patch must not be empty.")

    file_patches = split_unified_patch_by_file(patch)
    if not file_patches:
        raise ValueError("Patch must include file headers for at least one file.")

    prepared: list[tuple[Path, str, str, str]] = []
    seen: set[str] = set()
    for relative_path, file_patch, operation in file_patches:
        if relative_path in seen:
            raise ValueError(f"Patch contains duplicate file section: {relative_path}")
        seen.add(relative_path)

        target = resolve_mutation_path(workspace.root, relative_path)
        if operation == "create":
            if target.exists():
                raise ValueError(f"File already exists: {relative_path}")
            before = ""
        elif not target.is_file():
            raise ValueError(f"File does not exist: {relative_path}")
        else:
            before = read_utf8_text_file(target, relative_path)
        after = apply_unified_patch(before, file_patch)
        if after == before:
            raise ValueError(f"Patch made no changes to {relative_path}")
        if operation == "delete" and after:
            raise ValueError(f"Patch delete file section must remove all content: {relative_path}")
        prepared.append((target, relative_path, before, after))

    diff = "".join(build_simple_diff(relative_path, before, after) for _target, relative_path, before, after in prepared)
    return [target for target, _relative_path, _before, _after in prepared], diff


def split_unified_patch_by_file(patch: str) -> list[tuple[str, str, str]]:
    patch_lines = patch.splitlines(keepends=True)
    sections: list[tuple[str, str, str]] = []
    index = 0
    while index < len(patch_lines):
        if not is_file_header_at(patch_lines, index):
            index += 1
            continue

        old_path = parse_unified_diff_path(patch_lines[index][4:])
        new_path = parse_unified_diff_path(patch_lines[index + 1][4:])
        if old_path is None and new_path is None:
            raise ValueError("Patch file section must include a target path.")
        if old_path is not None and new_path is not None and old_path != new_path:
            raise ValueError(f"Patch rename sections are not supported: {old_path} -> {new_path}")
        relative_path = new_path or old_path
        if relative_path is None:
            raise ValueError("Patch file section must include a target path.")
        operation = "modify"
        if old_path is None:
            operation = "create"
        elif new_path is None:
            operation = "delete"

        start = index
        index += 2
        while index < len(patch_lines) and not is_file_header_at(patch_lines, index):
            index += 1
        sections.append((relative_path, "".join(patch_lines[start:index]), operation))

    return sections


def is_file_header_at(lines: list[str], index: int) -> bool:
    return index + 1 < len(lines) and lines[index].startswith("--- ") and lines[index + 1].startswith("+++ ")


def parse_unified_diff_path(value: str) -> str | None:
    token = value.strip().split("\t", 1)[0].strip()
    if token == "/dev/null":
        return None
    if token.startswith("a/") or token.startswith("b/"):
        token = token[2:]
    return token


def apply_unified_patch(content: str, patch: str) -> str:
    lines = content.splitlines(keepends=True)
    patch_lines = patch.splitlines(keepends=True)
    hunks = parse_unified_patch_hunks(patch_lines)
    if not hunks:
        raise ValueError("Patch must contain at least one unified diff hunk.")

    offset = 0
    updated = list(lines)
    for hunk in hunks:
        old_start, old_count, old_chunk, new_chunk = hunk
        if old_count == 0:
            position = old_start + offset
        else:
            position = old_start - 1 + offset
        if position < 0 or position > len(updated):
            raise ValueError("Patch hunk target is outside the file.")
        if updated[position : position + len(old_chunk)] != old_chunk:
            raise ValueError("Patch context did not match file content.")
        updated[position : position + len(old_chunk)] = new_chunk
        offset += len(new_chunk) - len(old_chunk)

    return "".join(updated)


def parse_unified_patch_hunks(patch_lines: list[str]) -> list[tuple[int, int, list[str], list[str]]]:
    hunks: list[tuple[int, int, list[str], list[str]]] = []
    index = 0
    while index < len(patch_lines):
        line = patch_lines[index]
        if not line.startswith("@@ "):
            index += 1
            continue

        match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if not match:
            raise ValueError(f"Invalid patch hunk header: {line.strip()}")
        old_start = int(match.group(1))
        old_count = int(match.group(2) or "1")
        new_count = int(match.group(4) or "1")
        index += 1
        old_chunk: list[str] = []
        new_chunk: list[str] = []

        while index < len(patch_lines) and not patch_lines[index].startswith("@@ "):
            raw = patch_lines[index]
            marker = raw[:1]
            text = raw[1:]
            if marker == " ":
                old_chunk.append(text)
                new_chunk.append(text)
            elif marker == "-":
                old_chunk.append(text)
            elif marker == "+":
                new_chunk.append(text)
            elif marker == "\\":
                pass
            elif raw.startswith(("--- ", "+++ ", "diff ", "index ")):
                pass
            else:
                raise ValueError(f"Invalid patch hunk line: {raw.strip()}")
            index += 1

        if len(old_chunk) != old_count:
            raise ValueError("Patch hunk old line count does not match header.")
        if len(new_chunk) != new_count:
            raise ValueError("Patch hunk new line count does not match header.")
        hunks.append((old_start, old_count, old_chunk, new_chunk))

    return hunks
