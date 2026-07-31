from __future__ import annotations

import json
import shutil
from pathlib import Path

from .workspace_resolve import resolve_mutation_path


CHECKPOINT_UNTRACKED_SHOW_LIMIT = 50


def save_checkpoint_untracked_files(root: Path, checkpoint_dir: Path, status: str) -> tuple[int, int]:
    paths = checkpoint_untracked_paths(status)
    saved = 0
    skipped = 0
    manifest: list[dict[str, object]] = []
    storage_root = checkpoint_dir / "untracked_files"
    for path_text in paths:
        if not is_safe_checkpoint_relative_path(path_text):
            skipped += 1
            continue
        try:
            path = resolve_mutation_path(root, path_text)
            relative = path.relative_to(Path(root).resolve())
        except ValueError:
            skipped += 1
            continue
        if not path.is_file() or path.is_symlink():
            skipped += 1
            continue
        destination = storage_root / relative
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            manifest.append({"path": relative.as_posix(), "size_bytes": path.stat().st_size})
            saved += 1
        except OSError:
            skipped += 1
    if manifest:
        (checkpoint_dir / "untracked_manifest.json").write_text(
            json.dumps({"files": manifest}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return saved, skipped


def checkpoint_untracked_paths(status: str) -> list[str]:
    paths: list[str] = []
    for raw_line in status.splitlines():
        if not raw_line.startswith("?? "):
            continue
        path_text = raw_line[3:].strip()
        if path_text and not is_runtime_checkpoint_path(path_text):
            paths.append(path_text)
    return paths


def read_checkpoint_untracked_paths(root: Path, checkpoint_id: str) -> set[str]:
    return {item["path"] for item in read_checkpoint_untracked_manifest(root, checkpoint_id)}


def clip_checkpoint_untracked_paths(paths: list[str]) -> tuple[list[str], bool]:
    return paths[:CHECKPOINT_UNTRACKED_SHOW_LIMIT], len(paths) > CHECKPOINT_UNTRACKED_SHOW_LIMIT


def read_checkpoint_untracked_manifest(root: Path, checkpoint_id: str) -> list[dict[str, str]]:
    manifest_path = checkpoint_file_for_read_func(root, checkpoint_id, "untracked_manifest.json")
    if manifest_path is None:
        return []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(files, list):
        return []
    items: list[dict[str, str]] = []
    for item in files:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if isinstance(path, str) and is_safe_checkpoint_relative_path(path):
            items.append({"path": path})
    return items


def checkpoint_file_for_read_func(root: Path, checkpoint_id: str, name: str) -> Path | None:
    from .checkpoint_storage import checkpoint_file_for_read

    return checkpoint_file_for_read(root, checkpoint_id, name)


def checkpoint_root_func(root: Path) -> Path:
    from .checkpoint_storage import checkpoint_root

    return checkpoint_root(root)


def is_safe_checkpoint_relative_path(path: str) -> bool:
    candidate = Path(path)
    return bool(path) and not candidate.is_absolute() and ".." not in candidate.parts


def checkpoint_untracked_files_match(root: Path, checkpoint_id: str, saved_untracked: int) -> bool:
    manifest = read_checkpoint_untracked_manifest(root, checkpoint_id)
    if saved_untracked == 0:
        return True
    if len(manifest) != saved_untracked:
        return False
    storage_root = checkpoint_root_func(root) / checkpoint_id / "untracked_files"
    for item in manifest:
        relative = item["path"]
        if not is_safe_checkpoint_relative_path(relative):
            return False
        source = storage_root / relative
        try:
            target = resolve_mutation_path(root, relative)
        except ValueError:
            return False
        try:
            if not target.is_file() or source.read_bytes() != target.read_bytes():
                return False
        except OSError:
            return False
    return True


def check_checkpoint_untracked_restore_files(root: Path, checkpoint_id: str) -> str | None:
    manifest = read_checkpoint_untracked_manifest(root, checkpoint_id)
    storage_root = checkpoint_root_func(root) / checkpoint_id / "untracked_files"
    for item in manifest:
        relative = item["path"]
        if not is_safe_checkpoint_relative_path(relative):
            return f"Refusing to restore unsafe untracked file path: {relative}"
        try:
            resolve_mutation_path(root, relative)
        except ValueError as error:
            return f"Refusing to restore untracked file {relative}: {error}"
        source = storage_root / relative
        if not source.is_file():
            return f"Saved untracked file is missing from checkpoint: {relative}"
    return None


def restore_checkpoint_untracked_files(root: Path, checkpoint_id: str) -> str | None:
    preflight_error = check_checkpoint_untracked_restore_files(root, checkpoint_id)
    if preflight_error:
        return preflight_error
    manifest = read_checkpoint_untracked_manifest(root, checkpoint_id)
    storage_root = checkpoint_root_func(root) / checkpoint_id / "untracked_files"
    for item in manifest:
        relative = item["path"]
        try:
            destination = resolve_mutation_path(root, relative)
        except ValueError as error:
            return f"Refusing to restore untracked file {relative}: {error}"
        source = storage_root / relative
        if not source.is_file():
            return f"Saved untracked file is missing from checkpoint: {relative}"
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        except OSError as error:
            return f"Failed to restore untracked file {relative}: {error}"
    return None


def is_runtime_checkpoint_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    return normalized == ".git" or normalized.startswith(".git/") or normalized == ".vibeagent" or normalized.startswith(".vibeagent/")
