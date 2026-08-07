from __future__ import annotations

from pathlib import Path

from .workspace_code_intel import build_simple_diff
from .workspace_core import RunWorkspace
from .workspace_file_read import read_utf8_text_file
from .workspace_resolve import resolve_mutation_path


def write_run_file(workspace: RunWorkspace, relative_path: str, content: str) -> Path:
    target, _before, after, _diff = build_write_file(workspace, relative_path, content)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(after, encoding="utf-8")
    return target


def preview_write_run_file(workspace: RunWorkspace, relative_path: str, content: str) -> tuple[Path, str]:
    target, _before, _after, diff = build_write_file(workspace, relative_path, content)
    return target, diff


def build_write_file(workspace: RunWorkspace, relative_path: str, content: str) -> tuple[Path, str, str, str]:
    # Resolve and read existing UTF-8 content when replacing a file.
    target = resolve_mutation_path(workspace.root, relative_path)
    if target.exists() and not target.is_file():
        raise ValueError(f"Path is not a file: {relative_path}")
    before = read_utf8_text_file(target, relative_path) if target.exists() else ""
    return target, before, content, build_simple_diff(relative_path, before, content)


def write_run_files(workspace: RunWorkspace, files: list[tuple[str, str]]) -> list[Path]:
    prepared = prepare_write_run_files(workspace, files)

    snapshots: list[tuple[Path, bool, str | None]] = []
    written: list[Path] = []
    try:
        for _relative_path, target, before, content, _diff in prepared:
            snapshots.append((target, target.exists(), before if target.exists() else None))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            written.append(target)
    except OSError as error:
        for target, existed, previous in reversed(snapshots):
            try:
                if existed and previous is not None:
                    target.write_text(previous, encoding="utf-8")
                elif target.exists():
                    target.unlink()
            except OSError:
                pass
        raise ValueError(f"Failed to write files: {error}") from error

    return written


def preview_write_run_files(workspace: RunWorkspace, files: list[tuple[str, str]]) -> list[tuple[str, Path, str]]:
    prepared = prepare_write_run_files(workspace, files)
    return [(relative_path, target, diff) for relative_path, target, _before, _content, diff in prepared]


def prepare_write_run_files(workspace: RunWorkspace, files: list[tuple[str, str]]) -> list[tuple[str, Path, str, str, str]]:
    if not files:
        raise ValueError("At least one file is required.")
    if len(files) > 20:
        raise ValueError("write_files supports at most 20 files.")

    prepared: list[tuple[str, Path, str, str, str]] = []
    seen: set[Path] = set()
    for index, (relative_path, content) in enumerate(files, start=1):
        if not relative_path or not relative_path.strip():
            raise ValueError(f"File {index} path must not be empty.")
        target, before, after, diff = build_write_file(workspace, relative_path, content)
        if target in seen:
            raise ValueError(f"Duplicate file path: {relative_path}")
        seen.add(target)
        prepared.append((relative_path, target, before, after, diff))

    return prepared
