from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .types import CheckpointInfo
from .workspace_resolve import resolve_mutation_path


CHECKPOINT_UNTRACKED_SHOW_LIMIT = 50


def run_checkpoint_git_command(root: Path, args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def checkpoint_root(root: Path) -> Path:
    return root / ".vibeagent" / "checkpoints"


def checkpoint_root_safety_error(root: Path) -> str | None:
    runtime_dir = root / ".vibeagent"
    base = checkpoint_root(root)
    if runtime_dir.is_symlink():
        return "Checkpoint runtime path is not a regular directory: .vibeagent"
    if runtime_dir.exists() and not runtime_dir.is_dir():
        return "Checkpoint runtime path is not a directory: .vibeagent"
    if base.is_symlink():
        return "Checkpoint root path is not a regular directory: .vibeagent/checkpoints"
    if base.exists() and not base.is_dir():
        return "Checkpoint root path is not a directory: .vibeagent/checkpoints"
    return None


def make_checkpoint_id() -> str:
    stamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return f"{stamp.replace(':', '-').replace('.', '-')}-{uuid.uuid4().hex[:8]}"


def normalize_checkpoint_label(label: str | None) -> str:
    return " ".join((label or "").strip().split())[:120]


def checkpoint_info_to_metadata(
    info: CheckpointInfo,
    project_root: str,
    git_status: str,
    staged_patch_chars: int,
    unstaged_patch_chars: int,
) -> dict[str, object]:
    return {
        "id": info.checkpoint_id,
        "label": info.label,
        "created_at": info.created_at,
        "project_root": project_root,
        "head": info.head,
        "git_status": git_status,
        "changed_files": info.changed_files,
        "staged_files": info.staged_files,
        "unstaged_files": info.unstaged_files,
        "untracked_files": info.untracked_files,
        "staged_diff_chars": staged_patch_chars,
        "unstaged_diff_chars": unstaged_patch_chars,
    }


def read_checkpoint_infos(root: Path) -> list[CheckpointInfo]:
    if checkpoint_root_safety_error(root):
        return []
    base = checkpoint_root(root)
    if not base.is_dir():
        return []
    infos: list[CheckpointInfo] = []
    for path in base.iterdir():
        metadata_path = path / "metadata.json"
        if path.is_symlink() or not path.is_dir() or not metadata_path.is_file():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        info = checkpoint_info_from_metadata(metadata)
        if info is not None and info.checkpoint_id == path.name:
            infos.append(info)
    infos.sort(key=lambda item: (item.created_at, item.checkpoint_id), reverse=True)
    return infos


def checkpoint_info_from_metadata(metadata: object) -> CheckpointInfo | None:
    if not isinstance(metadata, dict):
        return None
    checkpoint_id = metadata.get("id")
    if not isinstance(checkpoint_id, str) or not checkpoint_id:
        return None
    return CheckpointInfo(
        checkpoint_id=checkpoint_id,
        label=str(metadata.get("label") or ""),
        created_at=str(metadata.get("created_at") or ""),
        head=str(metadata.get("head") or ""),
        changed_files=int(metadata.get("changed_files") or 0),
        staged_files=int(metadata.get("staged_files") or 0),
        unstaged_files=int(metadata.get("unstaged_files") or 0),
        untracked_files=int(metadata.get("untracked_files") or 0),
    )


def read_checkpoint_metadata(root: Path, checkpoint_id: str) -> tuple[dict[str, object] | None, str]:
    normalized = resolve_checkpoint_id(root, checkpoint_id)
    if not normalized or Path(normalized).name != normalized:
        return None, f"Invalid checkpoint id: {checkpoint_id}"
    root_error = checkpoint_root_safety_error(root)
    if root_error:
        return None, root_error
    checkpoint_dir = checkpoint_root(root) / normalized
    if checkpoint_dir.is_symlink():
        return None, f"Checkpoint path is not a regular directory: {checkpoint_id}"
    if not checkpoint_dir.is_dir():
        return None, f"Checkpoint not found: {checkpoint_id}"
    metadata_path = checkpoint_dir / "metadata.json"
    if not metadata_path.is_file():
        return None, f"Checkpoint not found: {checkpoint_id}"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, f"Checkpoint metadata is unreadable: {checkpoint_id}"
    if not isinstance(metadata, dict):
        return None, f"Checkpoint metadata is invalid: {checkpoint_id}"
    metadata_id = metadata.get("id")
    if isinstance(metadata_id, str) and metadata_id and metadata_id != normalized:
        return None, f"Checkpoint metadata id does not match directory: {checkpoint_id}"
    return metadata, "ok"


def checkpoint_directory_for_deletion(root: Path, checkpoint_id: str) -> tuple[Path | None, str]:
    normalized = resolve_checkpoint_id(root, checkpoint_id)
    if not normalized or Path(normalized).name != normalized:
        return None, f"Invalid checkpoint id: {checkpoint_id}"
    root_error = checkpoint_root_safety_error(root)
    if root_error:
        return None, root_error
    checkpoint_dir = checkpoint_root(root) / normalized
    if checkpoint_dir.is_symlink():
        return None, f"Refusing to delete checkpoint symlink: {checkpoint_id}"
    if not checkpoint_dir.is_dir():
        return None, f"Checkpoint not found: {checkpoint_id}"
    try:
        resolved_base = checkpoint_root(root).resolve()
        resolved_dir = checkpoint_dir.resolve()
    except OSError as error:
        return None, f"Failed to resolve checkpoint {checkpoint_id}: {error}"
    if resolved_dir != resolved_base and resolved_base not in resolved_dir.parents:
        return None, f"Refusing to delete checkpoint outside checkpoint directory: {checkpoint_id}"
    return checkpoint_dir, "ok"


def read_checkpoint_patch(root: Path, checkpoint_id: str, name: str) -> str:
    path = checkpoint_file_for_read(root, checkpoint_id, name)
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def checkpoint_file_for_read(root: Path, checkpoint_id: str, name: str) -> Path | None:
    normalized = resolve_checkpoint_id(root, checkpoint_id)
    if not normalized or Path(normalized).name != normalized or Path(name).name != name:
        return None
    if checkpoint_root_safety_error(root):
        return None
    checkpoint_dir = checkpoint_root(root) / normalized
    if checkpoint_dir.is_symlink() or not checkpoint_dir.is_dir():
        return None
    path = checkpoint_dir / name
    if path.is_symlink() or not path.is_file():
        return None
    try:
        resolved_dir = checkpoint_dir.resolve()
        resolved_path = path.resolve()
    except OSError:
        return None
    if resolved_path != resolved_dir and resolved_dir not in resolved_path.parents:
        return None
    return path


def resolve_checkpoint_id(root: Path, checkpoint_id: str) -> str:
    normalized = checkpoint_id.strip()
    if not normalized or Path(normalized).name != normalized:
        return normalized
    if normalized == "latest":
        checkpoints = read_checkpoint_infos(root)
        if checkpoints:
            return checkpoints[0].checkpoint_id
    return normalized


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
    manifest_path = checkpoint_file_for_read(root, checkpoint_id, "untracked_manifest.json")
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


def is_safe_checkpoint_relative_path(path: str) -> bool:
    candidate = Path(path)
    return bool(path) and not candidate.is_absolute() and ".." not in candidate.parts


def checkpoint_untracked_files_match(root: Path, checkpoint_id: str, saved_untracked: int) -> bool:
    manifest = read_checkpoint_untracked_manifest(root, checkpoint_id)
    if saved_untracked == 0:
        return True
    if len(manifest) != saved_untracked:
        return False
    storage_root = checkpoint_root(root) / checkpoint_id / "untracked_files"
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
    storage_root = checkpoint_root(root) / checkpoint_id / "untracked_files"
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
    storage_root = checkpoint_root(root) / checkpoint_id / "untracked_files"
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


def clip_text_with_flag(value: str, max_chars: int) -> tuple[str, bool]:
    if len(value) <= max_chars:
        return value, False
    return value[:max_chars], True


def read_checkpoint_git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def filter_checkpoint_status(status: str) -> str:
    lines: list[str] = []
    for raw_line in status.splitlines():
        path_text = raw_line[3:] if len(raw_line) > 3 else raw_line.strip()
        paths = path_text.split(" -> ") if " -> " in path_text else [path_text]
        if any(is_runtime_checkpoint_path(path.strip()) for path in paths):
            continue
        lines.append(raw_line)
    return "\n".join(lines)


def is_runtime_checkpoint_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    return normalized == ".git" or normalized.startswith(".git/") or normalized == ".vibeagent" or normalized.startswith(".vibeagent/")


def count_checkpoint_status_kinds(status: str) -> dict[str, int]:
    changed = staged = unstaged = untracked = 0
    for line in status.splitlines():
        if len(line) < 2:
            continue
        code = line[:2]
        changed += 1
        if code == "??":
            untracked += 1
            continue
        if code[0] != " ":
            staged += 1
        if code[1] != " ":
            unstaged += 1
    return {
        "changed_files": changed,
        "staged_files": staged,
        "unstaged_files": unstaged,
        "untracked_files": untracked,
    }


def short_checkpoint_head(value: str) -> str:
    return value[:12] if value else "."
