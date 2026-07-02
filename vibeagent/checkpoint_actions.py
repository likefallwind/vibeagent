from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .types import (
    CheckCheckpointDeleteObservation,
    CheckCheckpointPruneObservation,
    CheckCheckpointRestoreObservation,
    CheckpointCreateObservation,
    CheckpointDeleteObservation,
    CheckpointDiffObservation,
    CheckpointInfo,
    CheckpointListObservation,
    CheckpointPruneObservation,
    CheckpointRestoreObservation,
    CheckpointShowObservation,
    CheckpointStatusObservation,
)
from .workspace import (
    RunWorkspace,
    read_git_diff,
    read_git_status,
)
from .workspace_resolve import resolve_mutation_path


CHECKPOINT_UNTRACKED_SHOW_LIMIT = 50


def create_checkpoint_observation(workspace: RunWorkspace, label: str | None = None) -> CheckpointCreateObservation:
    status = read_git_status(workspace)
    if not status.ok:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=status.stderr or "git status failed.",
        )
    staged = read_git_diff(workspace, staged=True)
    unstaged = read_git_diff(workspace, staged=False)
    if not staged.ok or not unstaged.ok:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=staged.stderr or unstaged.stderr or "git diff failed.",
        )
    head = read_checkpoint_git_head(workspace.root)
    if not head:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message="git rev-parse HEAD failed.",
        )

    filtered_status = filter_checkpoint_status(status.stdout)
    counts = count_checkpoint_status_kinds(filtered_status)
    checkpoint_id = make_checkpoint_id()
    created_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    info = CheckpointInfo(
        checkpoint_id=checkpoint_id,
        label=normalize_checkpoint_label(label),
        created_at=created_at,
        head=head,
        changed_files=counts["changed_files"],
        staged_files=counts["staged_files"],
        unstaged_files=counts["unstaged_files"],
        untracked_files=counts["untracked_files"],
    )
    root_error = checkpoint_root_safety_error(workspace.root)
    if root_error:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=root_error,
        )
    checkpoint_base = checkpoint_root(workspace.root)
    try:
        checkpoint_base.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=f"Failed to create checkpoint root: {error}",
        )
    root_error = checkpoint_root_safety_error(workspace.root)
    if root_error:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=root_error,
        )
    checkpoint_dir = checkpoint_base / checkpoint_id
    try:
        checkpoint_dir.mkdir(exist_ok=False)
    except OSError as error:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=f"Failed to create checkpoint directory: {error}",
        )
    metadata = checkpoint_info_to_metadata(info, str(workspace.root), filtered_status, len(staged.stdout), len(unstaged.stdout))
    saved_untracked, skipped_untracked = save_checkpoint_untracked_files(workspace.root, checkpoint_dir, filtered_status)
    metadata["untracked_saved_files"] = saved_untracked
    metadata["untracked_skipped_files"] = skipped_untracked
    (checkpoint_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (checkpoint_dir / "staged.patch").write_text(staged.stdout, encoding="utf-8")
    (checkpoint_dir / "unstaged.patch").write_text(unstaged.stdout, encoding="utf-8")
    return CheckpointCreateObservation(
        kind="checkpoint_create",
        ok=True,
        checkpoint=info,
        staged_patch_chars=len(staged.stdout),
        unstaged_patch_chars=len(unstaged.stdout),
        message=f"Saved checkpoint {checkpoint_id}.",
    )


def list_checkpoints_observation(root: Path, max_entries: int = 20) -> CheckpointListObservation:
    checkpoints = read_checkpoint_infos(root)
    shown = checkpoints[:max_entries]
    return CheckpointListObservation(
        kind="checkpoint_list",
        ok=True,
        checkpoints=shown,
        total=len(checkpoints),
        message=f"Found {len(checkpoints)} checkpoint(s).",
    )


def checkpoint_show_observation(root: Path, checkpoint_id: str) -> CheckpointShowObservation:
    metadata, message = read_checkpoint_metadata(root, checkpoint_id)
    if metadata is None:
        return CheckpointShowObservation(
            kind="checkpoint_show",
            ok=False,
            checkpoint=None,
            project_root="",
            git_status="",
            untracked_saved_files=0,
            untracked_skipped_files=0,
            saved_untracked_paths=[],
            saved_untracked_paths_truncated=False,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=message,
        )
    info = checkpoint_info_from_metadata(metadata)
    if info is None:
        return CheckpointShowObservation(
            kind="checkpoint_show",
            ok=False,
            checkpoint=None,
            project_root=str(metadata.get("project_root") or ""),
            git_status="",
            untracked_saved_files=0,
            untracked_skipped_files=0,
            saved_untracked_paths=[],
            saved_untracked_paths_truncated=False,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=f"Checkpoint metadata is invalid: {checkpoint_id}",
        )
    saved_untracked_paths, saved_untracked_paths_truncated = clip_checkpoint_untracked_paths(
        [item["path"] for item in read_checkpoint_untracked_manifest(root, info.checkpoint_id)],
    )
    return CheckpointShowObservation(
        kind="checkpoint_show",
        ok=True,
        checkpoint=info,
        project_root=str(metadata.get("project_root") or ""),
        git_status=str(metadata.get("git_status") or ""),
        untracked_saved_files=int(metadata.get("untracked_saved_files") or 0),
        untracked_skipped_files=int(metadata.get("untracked_skipped_files") or 0),
        saved_untracked_paths=saved_untracked_paths,
        saved_untracked_paths_truncated=saved_untracked_paths_truncated,
        staged_patch_chars=int(metadata.get("staged_diff_chars") or 0),
        unstaged_patch_chars=int(metadata.get("unstaged_diff_chars") or 0),
        message=f"Read checkpoint {info.checkpoint_id}.",
    )


def checkpoint_diff_observation(root: Path, checkpoint_id: str, max_chars: int = 40_000) -> CheckpointDiffObservation:
    metadata, message = read_checkpoint_metadata(root, checkpoint_id)
    if metadata is None:
        return CheckpointDiffObservation(
            kind="checkpoint_diff",
            ok=False,
            checkpoint_id=checkpoint_id,
            label="",
            created_at="",
            staged_patch="",
            staged_patch_chars=0,
            staged_patch_truncated=False,
            unstaged_patch="",
            unstaged_patch_chars=0,
            unstaged_patch_truncated=False,
            max_chars=max_chars,
            message=message,
        )
    checkpoint_id = str(metadata.get("id") or checkpoint_id)
    staged_patch = read_checkpoint_patch(root, checkpoint_id, "staged.patch")
    unstaged_patch = read_checkpoint_patch(root, checkpoint_id, "unstaged.patch")
    staged_text, staged_truncated = clip_text_with_flag(staged_patch, max_chars)
    unstaged_text, unstaged_truncated = clip_text_with_flag(unstaged_patch, max_chars)
    return CheckpointDiffObservation(
        kind="checkpoint_diff",
        ok=True,
        checkpoint_id=checkpoint_id,
        label=str(metadata.get("label") or ""),
        created_at=str(metadata.get("created_at") or ""),
        staged_patch=staged_text,
        staged_patch_chars=len(staged_patch),
        staged_patch_truncated=staged_truncated,
        unstaged_patch=unstaged_text,
        unstaged_patch_chars=len(unstaged_patch),
        unstaged_patch_truncated=unstaged_truncated,
        max_chars=max_chars,
        message=f"Read checkpoint diff {checkpoint_id}.",
    )


def checkpoint_status_observation(workspace: RunWorkspace, checkpoint_id: str) -> CheckpointStatusObservation:
    metadata, message = read_checkpoint_metadata(workspace.root, checkpoint_id)
    if metadata is None:
        return empty_checkpoint_status(checkpoint_id, message)
    status = read_git_status(workspace)
    staged = read_git_diff(workspace, staged=True)
    unstaged = read_git_diff(workspace, staged=False)
    if not status.ok or not staged.ok or not unstaged.ok:
        return empty_checkpoint_status(
            str(metadata.get("id") or checkpoint_id),
            status.stderr or staged.stderr or unstaged.stderr or "git status/diff failed.",
        )
    saved_status = str(metadata.get("git_status") or "")
    saved_staged = read_checkpoint_patch(workspace.root, checkpoint_id, "staged.patch")
    saved_unstaged = read_checkpoint_patch(workspace.root, checkpoint_id, "unstaged.patch")
    untracked_matches = checkpoint_untracked_files_match(workspace.root, checkpoint_id, int(metadata.get("untracked_files") or 0))
    current_status = filter_checkpoint_status(status.stdout)
    current_counts = count_checkpoint_status_kinds(current_status)
    status_matches = current_status == saved_status
    staged_matches = staged.stdout == saved_staged
    unstaged_matches = unstaged.stdout == saved_unstaged
    matches = status_matches and staged_matches and unstaged_matches and untracked_matches
    return CheckpointStatusObservation(
        kind="checkpoint_status",
        ok=True,
        checkpoint_id=str(metadata.get("id") or checkpoint_id),
        matches=matches,
        status_matches=status_matches,
        staged_patch_matches=staged_matches,
        unstaged_patch_matches=unstaged_matches,
        untracked_file_matches=untracked_matches,
        saved_changed_files=int(metadata.get("changed_files") or 0),
        saved_staged_files=int(metadata.get("staged_files") or 0),
        saved_unstaged_files=int(metadata.get("unstaged_files") or 0),
        saved_untracked_files=int(metadata.get("untracked_files") or 0),
        current_changed_files=current_counts["changed_files"],
        current_staged_files=current_counts["staged_files"],
        current_unstaged_files=current_counts["unstaged_files"],
        current_untracked_files=current_counts["untracked_files"],
        message="Current worktree matches checkpoint." if matches else "Current worktree differs from checkpoint.",
    )


def check_checkpoint_restore_observation(workspace: RunWorkspace, checkpoint_id: str) -> CheckCheckpointRestoreObservation:
    metadata, message = read_checkpoint_metadata(workspace.root, checkpoint_id)
    if metadata is None:
        return empty_check_checkpoint_restore(checkpoint_id, message)
    status = read_git_status(workspace)
    if not status.ok:
        return empty_check_checkpoint_restore(str(metadata.get("id") or checkpoint_id), status.stderr or "git status failed.")
    current_head = read_checkpoint_git_head(workspace.root)
    saved_head = metadata.get("head")
    current_counts = count_checkpoint_status_kinds(filter_checkpoint_status(status.stdout))
    saved_untracked = int(metadata.get("untracked_files") or 0)
    saved_untracked_paths = read_checkpoint_untracked_paths(workspace.root, checkpoint_id)
    current_untracked_paths = set(checkpoint_untracked_paths(filter_checkpoint_status(status.stdout)))
    staged_patch = read_checkpoint_patch(workspace.root, checkpoint_id, "staged.patch")
    unstaged_patch = read_checkpoint_patch(workspace.root, checkpoint_id, "unstaged.patch")
    can_restore = True
    restore_message = "Checkpoint can restore tracked staged/unstaged changes and saved untracked files."
    if not isinstance(saved_head, str) or not saved_head:
        can_restore = False
        restore_message = "Checkpoint does not record HEAD; create a new checkpoint before using restore."
    elif current_head != saved_head:
        can_restore = False
        restore_message = f"Checkpoint was created at HEAD {short_checkpoint_head(saved_head)}, but current HEAD is {short_checkpoint_head(current_head)}."
    elif saved_untracked and len(saved_untracked_paths) != saved_untracked:
        can_restore = False
        restore_message = "Checkpoint contains untracked files that were not fully saved."
    elif current_untracked_paths - saved_untracked_paths:
        can_restore = False
        restore_message = "Current worktree contains extra untracked files; move, delete, or commit them before checkpoint restore."
    else:
        untracked_restore_error = check_checkpoint_untracked_restore_files(workspace.root, str(metadata.get("id") or checkpoint_id))
        if untracked_restore_error:
            can_restore = False
            restore_message = untracked_restore_error
    return CheckCheckpointRestoreObservation(
        kind="check_checkpoint_restore",
        ok=can_restore,
        checkpoint_id=str(metadata.get("id") or checkpoint_id),
        can_restore=can_restore,
        saved_head=saved_head if isinstance(saved_head, str) else "",
        current_head=current_head,
        saved_untracked_files=saved_untracked,
        current_untracked_files=current_counts["untracked_files"],
        staged_patch_chars=len(staged_patch),
        unstaged_patch_chars=len(unstaged_patch),
        message=restore_message,
    )


def checkpoint_restore_observation(workspace: RunWorkspace, checkpoint_id: str) -> CheckpointRestoreObservation:
    restore_check = check_checkpoint_restore_observation(workspace, checkpoint_id)
    if not restore_check.ok:
        return CheckpointRestoreObservation(
            kind="checkpoint_restore",
            ok=False,
            checkpoint_id=restore_check.checkpoint_id,
            restored=False,
            matches=False,
            saved_head=restore_check.saved_head,
            current_head=restore_check.current_head,
            saved_untracked_files=restore_check.saved_untracked_files,
            current_untracked_files=restore_check.current_untracked_files,
            staged_patch_chars=restore_check.staged_patch_chars,
            unstaged_patch_chars=restore_check.unstaged_patch_chars,
            message=restore_check.message,
        )

    restored_id = restore_check.checkpoint_id
    staged_patch = read_checkpoint_patch(workspace.root, restored_id, "staged.patch")
    unstaged_patch = read_checkpoint_patch(workspace.root, restored_id, "unstaged.patch")
    steps: list[tuple[list[str], str | None]] = [(["restore", "--staged", "--worktree", "--", "."], None)]
    if staged_patch.strip():
        steps.extend(
            [
                (["apply", "--check", "--whitespace=nowarn", "-"], staged_patch),
                (["apply", "--cached", "--check", "--whitespace=nowarn", "-"], staged_patch),
                (["apply", "--whitespace=nowarn", "-"], staged_patch),
                (["apply", "--cached", "--whitespace=nowarn", "-"], staged_patch),
            ]
        )
    if unstaged_patch.strip():
        steps.extend(
            [
                (["apply", "--check", "--whitespace=nowarn", "-"], unstaged_patch),
                (["apply", "--whitespace=nowarn", "-"], unstaged_patch),
            ]
        )

    for args, stdin in steps:
        result = run_checkpoint_git_command(workspace.root, args, stdin)
        if result.returncode != 0:
            return CheckpointRestoreObservation(
                kind="checkpoint_restore",
                ok=False,
                checkpoint_id=restore_check.checkpoint_id,
                restored=False,
                matches=False,
                saved_head=restore_check.saved_head,
                current_head=restore_check.current_head,
                saved_untracked_files=restore_check.saved_untracked_files,
                current_untracked_files=restore_check.current_untracked_files,
                staged_patch_chars=restore_check.staged_patch_chars,
                unstaged_patch_chars=restore_check.unstaged_patch_chars,
                message=(
                    f"Failed to restore checkpoint while running git {' '.join(args)}: "
                    f"{result.stderr.strip() or result.stdout.strip() or 'unknown error'}"
                ),
            )

    restore_untracked_error = restore_checkpoint_untracked_files(workspace.root, restored_id)
    if restore_untracked_error:
        return CheckpointRestoreObservation(
            kind="checkpoint_restore",
            ok=False,
            checkpoint_id=restore_check.checkpoint_id,
            restored=False,
            matches=False,
            saved_head=restore_check.saved_head,
            current_head=restore_check.current_head,
            saved_untracked_files=restore_check.saved_untracked_files,
            current_untracked_files=restore_check.current_untracked_files,
            staged_patch_chars=restore_check.staged_patch_chars,
            unstaged_patch_chars=restore_check.unstaged_patch_chars,
            message=restore_untracked_error,
        )

    status = checkpoint_status_observation(workspace, restored_id)
    current_head = read_checkpoint_git_head(workspace.root)
    return CheckpointRestoreObservation(
        kind="checkpoint_restore",
        ok=status.ok and status.matches,
        checkpoint_id=restore_check.checkpoint_id,
        restored=status.ok and status.matches,
        matches=status.matches if status.ok else False,
        saved_head=restore_check.saved_head,
        current_head=current_head,
        saved_untracked_files=restore_check.saved_untracked_files,
        current_untracked_files=status.current_untracked_files if status.ok else restore_check.current_untracked_files,
        staged_patch_chars=restore_check.staged_patch_chars,
        unstaged_patch_chars=restore_check.unstaged_patch_chars,
        message=(
            "Restored tracked staged/unstaged changes and saved untracked files from checkpoint."
            if status.ok and status.matches
            else status.message
        ),
    )


def check_checkpoint_delete_observation(root: Path, checkpoint_id: str) -> CheckCheckpointDeleteObservation:
    metadata, message = read_checkpoint_metadata(root, checkpoint_id)
    if metadata is None:
        return CheckCheckpointDeleteObservation(
            kind="check_checkpoint_delete",
            ok=False,
            checkpoint_id=checkpoint_id,
            can_delete=False,
            label="",
            created_at="",
            message=message,
        )
    resolved_id = checkpoint_id.strip()
    display_id = str(metadata.get("id") or resolved_id)
    return CheckCheckpointDeleteObservation(
        kind="check_checkpoint_delete",
        ok=True,
        checkpoint_id=display_id,
        can_delete=True,
        label=str(metadata.get("label") or ""),
        created_at=str(metadata.get("created_at") or ""),
        message=f"Checkpoint delete would remove saved checkpoint {display_id}.",
    )


def checkpoint_delete_observation(root: Path, checkpoint_id: str) -> CheckpointDeleteObservation:
    preview = check_checkpoint_delete_observation(root, checkpoint_id)
    if not preview.ok:
        return CheckpointDeleteObservation(
            kind="checkpoint_delete",
            ok=False,
            checkpoint_id=preview.checkpoint_id,
            deleted=False,
            message=preview.message,
        )
    resolved_id = checkpoint_id.strip()
    display_id = preview.checkpoint_id
    checkpoint_dir, message = checkpoint_directory_for_deletion(root, resolved_id)
    if checkpoint_dir is None:
        return CheckpointDeleteObservation(
            kind="checkpoint_delete",
            ok=False,
            checkpoint_id=display_id,
            deleted=False,
            message=message,
        )
    try:
        shutil.rmtree(checkpoint_dir)
    except OSError as error:
        return CheckpointDeleteObservation(
            kind="checkpoint_delete",
            ok=False,
            checkpoint_id=display_id,
            deleted=False,
            message=f"Failed to delete checkpoint {display_id}: {error}",
        )
    return CheckpointDeleteObservation(
        kind="checkpoint_delete",
        ok=True,
        checkpoint_id=display_id,
        deleted=True,
        message=f"Deleted checkpoint {display_id}.",
    )


def check_checkpoint_prune_observation(root: Path, keep_last: int) -> CheckCheckpointPruneObservation:
    checkpoints = read_checkpoint_infos(root)
    to_delete = checkpoints[keep_last:] if keep_last < len(checkpoints) else []
    kept = len(checkpoints) - len(to_delete)
    return CheckCheckpointPruneObservation(
        kind="check_checkpoint_prune",
        ok=True,
        keep_last=keep_last,
        total=len(checkpoints),
        kept=kept,
        delete_count=len(to_delete),
        checkpoints=to_delete,
        message=(
            f"Checkpoint prune would delete {len(to_delete)} saved checkpoint(s)."
            if to_delete
            else "No checkpoints need pruning."
        ),
    )


def checkpoint_prune_observation(root: Path, keep_last: int) -> CheckpointPruneObservation:
    preview = check_checkpoint_prune_observation(root, keep_last)
    deleted = 0
    for checkpoint in preview.checkpoints:
        checkpoint_dir, message = checkpoint_directory_for_deletion(root, checkpoint.checkpoint_id)
        if checkpoint_dir is None:
            return CheckpointPruneObservation(
                kind="checkpoint_prune",
                ok=False,
                keep_last=keep_last,
                total=preview.total,
                kept=preview.kept,
                deleted=deleted,
                checkpoints=preview.checkpoints,
                message=message,
            )
        try:
            shutil.rmtree(checkpoint_dir)
        except OSError as error:
            return CheckpointPruneObservation(
                kind="checkpoint_prune",
                ok=False,
                keep_last=keep_last,
                total=preview.total,
                kept=preview.kept,
                deleted=deleted,
                checkpoints=preview.checkpoints,
                message=f"Failed to prune checkpoint {checkpoint.checkpoint_id}: {error}",
            )
        deleted += 1
    return CheckpointPruneObservation(
        kind="checkpoint_prune",
        ok=True,
        keep_last=keep_last,
        total=preview.total,
        kept=preview.kept,
        deleted=deleted,
        checkpoints=preview.checkpoints,
        message=(
            f"Pruned {deleted} saved checkpoint(s)."
            if deleted
            else "No checkpoints needed pruning."
        ),
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
    normalized = checkpoint_id.strip()
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
    normalized = checkpoint_id.strip()
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
    normalized = checkpoint_id.strip()
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


def empty_checkpoint_status(checkpoint_id: str, message: str) -> CheckpointStatusObservation:
    return CheckpointStatusObservation(
        kind="checkpoint_status",
        ok=False,
        checkpoint_id=checkpoint_id,
        matches=False,
        status_matches=False,
        staged_patch_matches=False,
        unstaged_patch_matches=False,
        untracked_file_matches=False,
        saved_changed_files=0,
        saved_staged_files=0,
        saved_unstaged_files=0,
        saved_untracked_files=0,
        current_changed_files=0,
        current_staged_files=0,
        current_unstaged_files=0,
        current_untracked_files=0,
        message=message,
    )


def empty_check_checkpoint_restore(checkpoint_id: str, message: str) -> CheckCheckpointRestoreObservation:
    return CheckCheckpointRestoreObservation(
        kind="check_checkpoint_restore",
        ok=False,
        checkpoint_id=checkpoint_id,
        can_restore=False,
        saved_head="",
        current_head="",
        saved_untracked_files=0,
        current_untracked_files=0,
        staged_patch_chars=0,
        unstaged_patch_chars=0,
        message=message,
    )


def short_checkpoint_head(value: str) -> str:
    return value[:12] if value else "."

