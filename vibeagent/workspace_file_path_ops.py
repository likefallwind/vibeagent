from __future__ import annotations

import shutil
from pathlib import Path

from .workspace_code_intel import build_simple_diff
from .workspace_core import RunWorkspace
from .workspace_file_read import read_utf8_text_file
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
