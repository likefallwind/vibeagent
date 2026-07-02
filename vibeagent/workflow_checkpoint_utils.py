from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess


CHECKPOINT_UNTRACKED_SHOW_LIMIT = 50


def parse_checkpoint_keep_last(value: str | int | None, usage: str) -> tuple[int, str | None]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return 0, f"Usage: {usage}"
    try:
        keep_last = int(value)
    except (TypeError, ValueError):
        return 0, f"Usage: {usage}\nError: keep-last must be an integer."
    if keep_last < 0:
        return 0, f"Usage: {usage}\nError: keep-last must be at least 0."
    if keep_last > 1000:
        return 0, f"Usage: {usage}\nError: keep-last must be at most 1000."
    return keep_last, None


def read_git_head(root: Path) -> str:
    result = run_git_checkpoint_command(root, ["rev-parse", "HEAD"], None)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def short_head(value: str) -> str:
    return value[:12] if value else "."


def run_git_checkpoint_command(root: Path, args: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def read_checkpoint_patch(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def save_local_checkpoint_untracked_files(root: Path, checkpoint_dir: Path, status: str) -> tuple[int, int]:
    paths = local_checkpoint_untracked_paths(status)
    saved = 0
    skipped = 0
    manifest: list[dict[str, object]] = []
    storage_root = checkpoint_dir / "untracked_files"
    for path_text in paths:
        if not is_safe_checkpoint_relative_path(path_text):
            skipped += 1
            continue
        path = root / path_text
        if not path.is_file() or path.is_symlink():
            skipped += 1
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:
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


def local_checkpoint_untracked_paths(status: str) -> list[str]:
    paths: list[str] = []
    for raw_line in status.splitlines():
        if not raw_line.startswith("?? "):
            continue
        path_text = raw_line[3:].strip()
        if path_text and not is_runtime_checkpoint_path(path_text):
            paths.append(path_text)
    return paths


def clip_local_checkpoint_untracked_paths(paths: list[str]) -> tuple[list[str], bool]:
    return paths[:CHECKPOINT_UNTRACKED_SHOW_LIMIT], len(paths) > CHECKPOINT_UNTRACKED_SHOW_LIMIT


def read_local_checkpoint_untracked_manifest(checkpoint_dir: Path) -> list[dict[str, str]]:
    manifest_path = checkpoint_dir / "untracked_manifest.json"
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


def local_checkpoint_untracked_files_match(root: Path, checkpoint_dir: Path, saved_untracked: int) -> bool:
    manifest = read_local_checkpoint_untracked_manifest(checkpoint_dir)
    if saved_untracked == 0:
        return True
    if len(manifest) != saved_untracked:
        return False
    storage_root = checkpoint_dir / "untracked_files"
    for item in manifest:
        relative = item["path"]
        if not is_safe_checkpoint_relative_path(relative):
            return False
        source = storage_root / relative
        target = root / relative
        try:
            if not target.is_file() or source.read_bytes() != target.read_bytes():
                return False
        except OSError:
            return False
    return True


def restore_local_checkpoint_untracked_files(root: Path, checkpoint_dir: Path) -> str | None:
    manifest = read_local_checkpoint_untracked_manifest(checkpoint_dir)
    storage_root = checkpoint_dir / "untracked_files"
    for item in manifest:
        relative = item["path"]
        if not is_safe_checkpoint_relative_path(relative):
            return f"Refusing to restore unsafe untracked file path: {relative}"
        source = storage_root / relative
        destination = root / relative
        try:
            destination.relative_to(root)
        except ValueError:
            return f"Refusing to restore untracked file outside project: {relative}"
        if not source.is_file():
            return f"Saved untracked file is missing from checkpoint: {relative}"
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        except OSError as error:
            return f"Failed to restore untracked file {relative}: {error}"
    return None


def is_safe_checkpoint_relative_path(path: str) -> bool:
    candidate = Path(path)
    return bool(path) and not candidate.is_absolute() and ".." not in candidate.parts


def is_runtime_checkpoint_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    return normalized == ".git" or normalized.startswith(".git/") or normalized == ".vibeagent" or normalized.startswith(".vibeagent/")


def format_checkpoint_created(metadata: dict[str, object]) -> str:
    label = str(metadata.get("label") or "")
    lines = [
        "Checkpoint:",
        "  created: yes",
        f"  id: {metadata['id']}",
        f"  label: {label}",
        f"  projectRoot: {metadata['project_root']}",
        f"  head: {short_head(str(metadata.get('head') or ''))}",
        f"  changedFiles: {metadata['changed_files']}",
        f"  stagedFiles: {metadata['staged_files']}",
        f"  unstagedFiles: {metadata['unstaged_files']}",
        f"  untrackedFiles: {metadata['untracked_files']}",
        f"  unstagedPatchChars: {metadata['unstaged_diff_chars']}",
        f"  stagedPatchChars: {metadata['staged_diff_chars']}",
        "  message: Saved checkpoint metadata, patch files, and ordinary untracked files under .vibeagent/checkpoints.",
    ]
    return "\n".join(lines)


def read_checkpoints(root: Path) -> list[dict[str, object]]:
    checkpoints: list[dict[str, object]] = []
    base = checkpoint_root(root)
    if not base.is_dir():
        return []
    for path in base.iterdir():
        metadata_path = path / "metadata.json"
        if not path.is_dir() or not metadata_path.is_file():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(metadata, dict) and isinstance(metadata.get("id"), str):
            checkpoints.append(metadata)
    checkpoints.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")), reverse=True)
    return checkpoints


def checkpoint_root(root: Path) -> Path:
    return root / ".vibeagent" / "checkpoints"


def resolve_checkpoint_dir(root: Path, checkpoint_id: str) -> Path:
    normalized = resolve_checkpoint_id(root, checkpoint_id)
    return checkpoint_root(root) / normalized


def resolve_checkpoint_id(root: Path, checkpoint_id: str) -> str:
    normalized = checkpoint_id.strip()
    if not normalized or Path(normalized).name != normalized:
        raise ValueError(f"Invalid checkpoint id: {checkpoint_id}")
    if normalized == "latest":
        checkpoints = read_checkpoints(root)
        if checkpoints:
            latest = checkpoints[0].get("id")
            if isinstance(latest, str) and latest:
                return latest
    return normalized


def normalize_checkpoint_label(label: str | None) -> str:
    return " ".join((label or "").strip().split())[:120]


def count_status_kinds(status: str) -> dict[str, int]:
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


def display_checkpoint_file(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
