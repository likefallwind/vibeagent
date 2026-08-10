from __future__ import annotations

import shutil
from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_paths import is_protected_project_path
from .workspace_resolve import display_workspace_path, resolve_mutation_path, workspace_root_for_path, workspace_roots


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
    source = resolve_mutation_path(workspace, source_path)
    destination = resolve_mutation_path(workspace, destination_path)
    if source == workspace.root.resolve():
        raise ValueError("Cannot move the project root directory.")
    if source in workspace.additional_roots:
        raise ValueError("Cannot move an additional workspace root directory.")
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
    source = resolve_mutation_path(workspace, source_path)
    destination = resolve_mutation_path(workspace, destination_path)
    if source == workspace.root.resolve():
        raise ValueError("Cannot copy the project root directory.")
    if source in workspace.additional_roots:
        raise ValueError("Cannot copy an additional workspace root directory.")
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
            raise ValueError(f"Directory contains a symbolic link: {display_workspace_path(workspace, path)}")
        access_root = workspace_root_for_path(workspace, path)
        if access_root is not None and is_protected_project_path(access_root, path.resolve()):
            raise ValueError(f"Directory contains a protected path: {display_workspace_path(workspace, path)}")
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
        for other in sources[index + 1 :]:
            if source == other or source in other.parents or other in source.parents:
                raise ValueError("Directory transfer sources must not overlap.")
    for index, destination in enumerate(destinations):
        for other in destinations[index + 1 :]:
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
    target = resolve_mutation_path(workspace, relative_path)
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
            relative_path = display_workspace_path(workspace, target)
            raise ValueError(f"Directory is not empty: {relative_path}") from error
    return targets


def preview_delete_project_empty_directory(workspace: RunWorkspace, relative_path: str) -> Path:
    target = resolve_mutation_path(workspace, relative_path)
    if target in workspace_roots(workspace):
        raise ValueError("Cannot delete a workspace root directory.")
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
        target = resolve_mutation_path(workspace, relative_path)
        if target in workspace_roots(workspace):
            raise ValueError("Cannot delete a workspace root directory.")
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
