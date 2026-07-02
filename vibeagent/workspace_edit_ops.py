from __future__ import annotations

import re
import shutil
import stat as stat_module
from pathlib import Path

from .workspace_code_intel import build_simple_diff
from .workspace_core import RunWorkspace
from .workspace_file_read import read_utf8_text_file
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
from .workspace_paths import is_protected_project_path
from .workspace_resolve import resolve_mutation_path


def delete_project_file(workspace: RunWorkspace, relative_path: str) -> tuple[Path, str]:
    target, diff = build_delete_file(workspace, relative_path)
    target.unlink()
    return target, diff


def preview_delete_project_file(workspace: RunWorkspace, relative_path: str) -> tuple[Path, str]:
    return build_delete_file(workspace, relative_path)


def delete_project_files(workspace: RunWorkspace, relative_paths: list[str]) -> tuple[list[Path], str]:
    targets, diff = build_delete_files(workspace, relative_paths)
    for target in targets:
        target.unlink()
    return targets, diff


def preview_delete_project_files(workspace: RunWorkspace, relative_paths: list[str]) -> tuple[list[Path], str]:
    return build_delete_files(workspace, relative_paths)


def build_delete_files(workspace: RunWorkspace, relative_paths: list[str]) -> tuple[list[Path], str]:
    if not relative_paths:
        raise ValueError("At least one file path is required.")
    if len(relative_paths) > 100:
        raise ValueError("At most 100 file paths can be deleted at once.")
    seen: set[str] = set()
    prepared: list[tuple[Path, str]] = []
    for relative_path in relative_paths:
        if relative_path in seen:
            raise ValueError(f"Duplicate file path: {relative_path}")
        seen.add(relative_path)
        prepared.append(build_delete_file(workspace, relative_path))
    diff = "".join(file_diff for _target, file_diff in prepared)
    return [target for target, _diff in prepared], diff


def build_delete_file(workspace: RunWorkspace, relative_path: str) -> tuple[Path, str]:
    target = resolve_mutation_path(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    return target, build_simple_diff(relative_path, before, "")


def move_project_file(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    source, destination = prepare_project_file_transfer(workspace, source_path, destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)
    return source, destination


def preview_move_project_file(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    return prepare_project_file_transfer(workspace, source_path, destination_path)


def move_project_files(workspace: RunWorkspace, transfers: list[dict[str, str]]) -> list[tuple[Path, Path]]:
    prepared = prepare_project_file_transfers(workspace, transfers)
    for source, destination in prepared:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
    return prepared


def preview_move_project_files(workspace: RunWorkspace, transfers: list[dict[str, str]]) -> list[tuple[Path, Path]]:
    return prepare_project_file_transfers(workspace, transfers)


def prepare_project_file_transfers(workspace: RunWorkspace, transfers: list[dict[str, str]]) -> list[tuple[Path, Path]]:
    if not transfers:
        raise ValueError("At least one file transfer is required.")
    if len(transfers) > 100:
        raise ValueError("At most 100 files can be moved at once.")

    prepared: list[tuple[Path, Path]] = []
    seen_sources: set[Path] = set()
    seen_destinations: set[Path] = set()
    for transfer in transfers:
        source_label = transfer.get("source", "")
        destination_label = transfer.get("destination", "")
        source, destination = prepare_project_file_transfer(workspace, source_label, destination_label)
        if source in seen_sources:
            raise ValueError(f"Duplicate source file: {source_label}")
        if destination in seen_destinations:
            raise ValueError(f"Duplicate destination file: {destination_label}")
        seen_sources.add(source)
        seen_destinations.add(destination)
        prepared.append((source, destination))

    for source, destination in prepared:
        if destination in seen_sources:
            raise ValueError(f"Destination overlaps another source file: {destination.relative_to(workspace.root).as_posix()}")
        if source in seen_destinations:
            raise ValueError(f"Source overlaps another destination file: {source.relative_to(workspace.root).as_posix()}")
        for parent in destination.parents:
            if parent == workspace.root:
                break
            if parent in seen_destinations:
                raise ValueError(f"Destination parent overlaps another destination file: {destination.relative_to(workspace.root).as_posix()}")
            if parent in seen_sources:
                raise ValueError(f"Destination parent overlaps another source file: {destination.relative_to(workspace.root).as_posix()}")

    return prepared


def copy_project_file(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    source, destination = prepare_project_file_transfer(workspace, source_path, destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return source, destination


def preview_copy_project_file(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    return prepare_project_file_transfer(workspace, source_path, destination_path)


def copy_project_files(workspace: RunWorkspace, transfers: list[dict[str, str]]) -> list[tuple[Path, Path]]:
    prepared = prepare_project_file_copies(workspace, transfers)
    for source, destination in prepared:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return prepared


def preview_copy_project_files(workspace: RunWorkspace, transfers: list[dict[str, str]]) -> list[tuple[Path, Path]]:
    return prepare_project_file_copies(workspace, transfers)


def prepare_project_file_copies(workspace: RunWorkspace, transfers: list[dict[str, str]]) -> list[tuple[Path, Path]]:
    if not transfers:
        raise ValueError("At least one file transfer is required.")
    if len(transfers) > 100:
        raise ValueError("At most 100 files can be copied at once.")

    prepared: list[tuple[Path, Path]] = []
    seen_destinations: set[Path] = set()
    for transfer in transfers:
        source_label = transfer.get("source", "")
        destination_label = transfer.get("destination", "")
        source, destination = prepare_project_file_transfer(workspace, source_label, destination_label)
        if destination in seen_destinations:
            raise ValueError(f"Duplicate destination file: {destination_label}")
        seen_destinations.add(destination)
        prepared.append((source, destination))

    for _source, destination in prepared:
        for parent in destination.parents:
            if parent == workspace.root:
                break
            if parent in seen_destinations:
                raise ValueError(f"Destination parent overlaps another destination file: {destination.relative_to(workspace.root).as_posix()}")

    return prepared


def prepare_project_file_transfer(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    source = resolve_mutation_path(workspace.root, source_path)
    destination = resolve_mutation_path(workspace.root, destination_path)
    if source == destination:
        raise ValueError("Source and destination must be different.")
    if not source.is_file():
        raise ValueError(f"File does not exist: {source_path}")
    if destination.exists():
        raise ValueError(f"Destination already exists: {destination_path}")
    return source, destination


def move_project_directory(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    source, destination = prepare_project_directory_move(workspace, source_path, destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)
    return source, destination


def move_project_directories(workspace: RunWorkspace, transfers: list[tuple[str, str]]) -> list[tuple[Path, Path]]:
    prepared = preview_move_project_directories(workspace, transfers)
    for source, destination in prepared:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
    return prepared


def preview_move_project_directory(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    return prepare_project_directory_move(workspace, source_path, destination_path)


def preview_move_project_directories(workspace: RunWorkspace, transfers: list[tuple[str, str]]) -> list[tuple[Path, Path]]:
    prepared = [prepare_project_directory_move(workspace, source, destination) for source, destination in transfers]
    validate_project_directory_transfer_batch(prepared, operation="move")
    return prepared


def prepare_project_directory_move(workspace: RunWorkspace, source_path: str, destination_path: str) -> tuple[Path, Path]:
    source = resolve_mutation_path(workspace.root, source_path)
    destination = resolve_mutation_path(workspace.root, destination_path)
    if source == workspace.root:
        raise ValueError("Cannot move the project root directory.")
    if source == destination:
        raise ValueError("Source and destination must be different.")
    if not source.is_dir():
        raise ValueError(f"Directory does not exist: {source_path}")
    if destination.exists():
        raise ValueError(f"Destination already exists: {destination_path}")
    if source in destination.parents:
        raise ValueError("Cannot move a directory inside itself.")
    return source, destination


def copy_project_directory(
    workspace: RunWorkspace,
    source_path: str,
    destination_path: str,
    max_entries: int = 2000,
    max_bytes: int = 50 * 1024 * 1024,
) -> tuple[Path, Path]:
    source, destination = prepare_project_directory_copy(
        workspace,
        source_path,
        destination_path,
        max_entries=max_entries,
        max_bytes=max_bytes,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    return source, destination


def copy_project_directories(
    workspace: RunWorkspace,
    transfers: list[tuple[str, str]],
    max_entries: int = 2000,
    max_bytes: int = 50 * 1024 * 1024,
) -> list[tuple[Path, Path]]:
    prepared = preview_copy_project_directories(
        workspace,
        transfers,
        max_entries=max_entries,
        max_bytes=max_bytes,
    )
    for source, destination in prepared:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination)
    return prepared


def preview_copy_project_directory(
    workspace: RunWorkspace,
    source_path: str,
    destination_path: str,
    max_entries: int = 2000,
    max_bytes: int = 50 * 1024 * 1024,
) -> tuple[Path, Path]:
    return prepare_project_directory_copy(
        workspace,
        source_path,
        destination_path,
        max_entries=max_entries,
        max_bytes=max_bytes,
    )


def preview_copy_project_directories(
    workspace: RunWorkspace,
    transfers: list[tuple[str, str]],
    max_entries: int = 2000,
    max_bytes: int = 50 * 1024 * 1024,
) -> list[tuple[Path, Path]]:
    prepared = [
        prepare_project_directory_copy(
            workspace,
            source,
            destination,
            max_entries=max_entries,
            max_bytes=max_bytes,
        )
        for source, destination in transfers
    ]
    validate_project_directory_transfer_batch(prepared, operation="copy")
    return prepared


def prepare_project_directory_copy(
    workspace: RunWorkspace,
    source_path: str,
    destination_path: str,
    max_entries: int = 2000,
    max_bytes: int = 50 * 1024 * 1024,
) -> tuple[Path, Path]:
    source = resolve_mutation_path(workspace.root, source_path)
    destination = resolve_mutation_path(workspace.root, destination_path)
    if source == workspace.root:
        raise ValueError("Cannot copy the project root directory.")
    if source == destination:
        raise ValueError("Source and destination must be different.")
    if not source.is_dir():
        raise ValueError(f"Directory does not exist: {source_path}")
    if destination.exists():
        raise ValueError(f"Destination already exists: {destination_path}")
    if source in destination.parents:
        raise ValueError("Cannot copy a directory inside itself.")

    entry_count = 0
    total_bytes = 0
    for path in source.rglob("*"):
        entry_count += 1
        if entry_count > max_entries:
            raise ValueError(f"Directory has more than {max_entries} entries: {source_path}")
        if path.is_symlink():
            raise ValueError(f"Directory contains a symbolic link: {path.relative_to(workspace.root).as_posix()}")
        if is_protected_project_path(workspace.root, path.resolve()):
            raise ValueError(f"Directory contains a protected path: {path.relative_to(workspace.root).as_posix()}")
        if path.is_file():
            total_bytes += path.stat().st_size
            if total_bytes > max_bytes:
                raise ValueError(f"Directory exceeds {max_bytes} bytes: {source_path}")

    return source, destination


def validate_project_directory_transfer_batch(prepared: list[tuple[Path, Path]], operation: str) -> None:
    if not prepared:
        raise ValueError(f"Directory {operation} requires at least one transfer.")
    if len(prepared) > 100:
        raise ValueError(f"Directory {operation} supports at most 100 transfers.")

    sources = [source.resolve() for source, _destination in prepared]
    destinations = [destination.resolve() for _source, destination in prepared]
    for index, source in enumerate(sources):
        for other in sources[index + 1:]:
            if source == other or source in other.parents or other in source.parents:
                raise ValueError("Directory transfer sources must not overlap.")
    for index, destination in enumerate(destinations):
        for other in destinations[index + 1:]:
            if destination == other or destination in other.parents or other in destination.parents:
                raise ValueError("Directory transfer destinations must not overlap.")
    for destination in destinations:
        for source in sources:
            if destination == source or source in destination.parents:
                raise ValueError("Directory transfer destination must not overlap a source.")


def create_project_directory(workspace: RunWorkspace, relative_path: str) -> Path:
    target = preview_create_project_directory(workspace, relative_path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def create_project_directories(workspace: RunWorkspace, relative_paths: list[str]) -> list[Path]:
    targets = preview_create_project_directories(workspace, relative_paths)
    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
    return targets


def preview_create_project_directory(workspace: RunWorkspace, relative_path: str) -> Path:
    target = resolve_mutation_path(workspace.root, relative_path)
    if target.exists() and not target.is_dir():
        raise ValueError(f"Path already exists and is not a directory: {relative_path}")
    return target


def preview_create_project_directories(workspace: RunWorkspace, relative_paths: list[str]) -> list[Path]:
    if not relative_paths:
        raise ValueError("Directory creation requires at least one path.")
    if len(relative_paths) > 100:
        raise ValueError("Directory creation supports at most 100 paths.")

    targets: list[Path] = []
    seen: set[Path] = set()
    for index, relative_path in enumerate(relative_paths, start=1):
        target = preview_create_project_directory(workspace, relative_path)
        normalized = target.resolve()
        if normalized in seen:
            raise ValueError(f"Directory path {index} duplicates an earlier target: {relative_path}")
        seen.add(normalized)
        targets.append(target)
    return targets


def delete_project_empty_directory(workspace: RunWorkspace, relative_path: str) -> Path:
    target = preview_delete_project_empty_directory(workspace, relative_path)
    try:
        target.rmdir()
    except OSError as error:
        raise ValueError(f"Directory is not empty: {relative_path}") from error
    return target


def delete_project_empty_directories(workspace: RunWorkspace, relative_paths: list[str]) -> list[Path]:
    targets = preview_delete_project_empty_directories(workspace, relative_paths)
    for target in sorted(targets, key=lambda path: len(path.parts), reverse=True):
        try:
            target.rmdir()
        except OSError as error:
            relative_path = target.relative_to(workspace.root).as_posix()
            raise ValueError(f"Directory is not empty: {relative_path}") from error
    return targets


def preview_delete_project_empty_directory(workspace: RunWorkspace, relative_path: str) -> Path:
    target = resolve_mutation_path(workspace.root, relative_path)
    if not target.is_dir():
        raise ValueError(f"Directory does not exist: {relative_path}")
    if any(target.iterdir()):
        raise ValueError(f"Directory is not empty: {relative_path}")
    return target


def preview_delete_project_empty_directories(workspace: RunWorkspace, relative_paths: list[str]) -> list[Path]:
    if not relative_paths:
        raise ValueError("Empty-directory deletion requires at least one path.")
    if len(relative_paths) > 100:
        raise ValueError("Empty-directory deletion supports at most 100 paths.")

    targets: list[Path] = []
    relative_by_target: dict[Path, str] = {}
    for index, relative_path in enumerate(relative_paths, start=1):
        target = resolve_mutation_path(workspace.root, relative_path)
        normalized = target.resolve()
        if normalized in relative_by_target:
            raise ValueError(f"Directory path {index} duplicates an earlier target: {relative_path}")
        if not target.is_dir():
            raise ValueError(f"Directory does not exist: {relative_path}")
        relative_by_target[normalized] = relative_path
        targets.append(target)

    target_set = set(relative_by_target)
    for target in targets:
        for child in target.iterdir():
            child_path = child.resolve()
            if child_path in target_set and child.is_dir():
                continue
            relative_path = relative_by_target[target.resolve()]
            raise ValueError(f"Directory is not empty: {relative_path}")
    return targets


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
