from __future__ import annotations

import json
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .types import CheckpointInfo
from .checkpoint_untracked_storage import (
    CHECKPOINT_UNTRACKED_SHOW_LIMIT,
    check_checkpoint_untracked_restore_files,
    checkpoint_untracked_files_match,
    checkpoint_untracked_paths,
    clip_checkpoint_untracked_paths,
    is_runtime_checkpoint_path,
    is_safe_checkpoint_relative_path,
    read_checkpoint_untracked_manifest,
    read_checkpoint_untracked_paths,
    restore_checkpoint_untracked_files,
    save_checkpoint_untracked_files,
)


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
