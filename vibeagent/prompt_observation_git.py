from __future__ import annotations

from .prompt_observation_git_sync import (
    format_git_fetch_observation,
    format_git_switch_observation,
    format_git_sync_observation,
)
from .prompt_observation_utils import truncate


def format_git_observation(index: int, observation: object) -> str | None:
    if observation.kind == "git_status":
        return "\n".join(
            [
                f"{index}. git_status: {observation.message}",
                f"status:\n{truncate(observation.status)}",
            ]
        )

    if observation.kind == "git_conflicts":
        unmerged = "\n".join(f"{item.status} {item.path}" for item in observation.unmerged[:80]) or "none"
        markers = "\n".join(
            f"{item.path}:{item.line} [{item.marker}] {item.text}"
            for item in observation.markers[:120]
        ) or "none"
        return "\n".join(
            [
                f"{index}. git_conflicts {observation.path}: {observation.message}",
                f"ok: {observation.ok}",
                f"unmerged: {len(observation.unmerged)}/{observation.unmerged_total}",
                f"markers: {len(observation.markers)}/{observation.markers_total}",
                f"scannedFiles: {observation.scanned_files}/{observation.total_files}",
                f"truncated: {observation.truncated}",
                f"unmergedFiles:\n{truncate(unmerged)}",
                f"markerLines:\n{truncate(markers)}",
            ]
        )

    if observation.kind == "git_info":
        parts = [
            (
                f"{index}. git_info: {observation.message} "
                f"branch={observation.branch or 'detached'} head={observation.head or 'unknown'} "
                f"upstream={observation.upstream or 'none'} ahead={observation.ahead} behind={observation.behind}"
            )
        ]
        for remote in observation.remotes[:20]:
            parts.append(f"remote: {remote.name} {remote.kind} {remote.url}")
        if observation.status.strip():
            parts.append(f"status:\n{truncate(observation.status)}")
        return "\n".join(parts)

    if observation.kind == "git_changes":
        parts = [f"{index}. git_changes: {observation.message}"]
        for file in observation.files[:120]:
            parts.append(
                (
                    f"file: {file.path} status={file.status or '..'} "
                    f"staged={str(file.staged).lower()} unstaged={str(file.unstaged).lower()} "
                    f"untracked={str(file.untracked).lower()} "
                    f"stagedLines=+{file.staged_insertions}/-{file.staged_deletions} "
                    f"unstagedLines=+{file.unstaged_insertions}/-{file.unstaged_deletions} "
                    f"binary={str(file.binary).lower()}"
                )
            )
        if observation.status.strip():
            parts.append(f"status:\n{truncate(observation.status)}")
        return "\n".join(parts)

    if observation.kind == "git_branches":
        parts = [
            (
                f"{index}. git_branches: {observation.message} "
                f"current={observation.current or 'detached'} shown={len(observation.branches)}/{observation.total} "
                f"truncated={str(observation.truncated).lower()}"
            )
        ]
        for branch in observation.branches[:120]:
            marker = "*" if branch.current else "-"
            parts.append(f"{marker} {branch.name}")
        if observation.status.strip():
            parts.append(f"status:\n{truncate(observation.status)}")
        return "\n".join(parts)

    if observation.kind in {"check_git_fetch", "git_fetch"}:
        return format_git_fetch_observation(index, observation)

    if observation.kind in {"check_git_pull", "git_pull", "check_git_push", "git_push"}:
        return format_git_sync_observation(index, observation)

    if observation.kind in {"check_git_restore", "git_restore"}:
        return "\n".join(
            [
                f"{index}. {observation.kind}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"paths: {', '.join(observation.paths)}",
                f"diff:\n{truncate(observation.diff)}",
                f"status:\n{truncate(observation.status)}",
            ]
        )

    if observation.kind == "git_stashes":
        parts = [
            (
                f"{index}. git_stashes: {observation.message} "
                f"shown={len(observation.entries)}/{observation.total} "
                f"truncated={str(observation.truncated).lower()}"
            )
        ]
        for entry in observation.entries[:50]:
            parts.append(f"stash: {entry.name} {entry.summary}")
        return "\n".join(parts)

    if observation.kind in {"check_git_stash", "git_stash"}:
        stash_ref = f"\nstashRef: {observation.stash_ref}" if observation.kind == "git_stash" else ""
        return "\n".join(
            [
                f"{index}. {observation.kind}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"messageText: {observation.message_text}",
                f"includeUntracked: {str(observation.include_untracked).lower()}{stash_ref}",
                f"diff:\n{truncate(observation.diff)}",
                f"status:\n{truncate(observation.status)}",
            ]
        )

    if observation.kind in {"check_git_stash_apply", "git_stash_apply"}:
        worktree = (
            f"\nworktreeClean: {str(observation.worktree_clean).lower()}"
            if observation.kind == "check_git_stash_apply"
            else ""
        )
        return "\n".join(
            [
                f"{index}. {observation.kind} {observation.stash_ref}: {observation.message}",
                f"ok: {str(observation.ok).lower()}{worktree}",
                f"patch:\n{truncate(observation.patch)}",
                f"status:\n{truncate(observation.status)}",
            ]
        )

    if observation.kind in {"check_git_stash_drop", "git_stash_drop"}:
        remaining = (
            f"\nremainingTotal: {observation.remaining_total}"
            if observation.kind == "git_stash_drop"
            else ""
        )
        return "\n".join(
            [
                f"{index}. {observation.kind} {observation.stash_ref}: {observation.message}",
                f"ok: {str(observation.ok).lower()}{remaining}",
                f"summary: {observation.summary}",
                f"patch:\n{truncate(observation.patch)}",
            ]
        )

    if observation.kind in {"check_git_switch", "git_switch"}:
        return format_git_switch_observation(index, observation)

    if observation.kind in {"check_git_stage", "git_stage", "check_git_unstage", "git_unstage"}:
        parts = [
            (
                f"{index}. {observation.kind}: {observation.message} "
                f"ok={str(observation.ok).lower()} paths={', '.join(observation.paths)}"
            )
        ]
        if observation.status.strip():
            parts.append(f"status:\n{truncate(observation.status)}")
        return "\n".join(parts)

    if observation.kind in {"check_git_commit", "git_commit"}:
        parts = [
            (
                f"{index}. {observation.kind}: {observation.message} ok={str(observation.ok).lower()} "
                f"head={observation.head_before or 'none'}->{observation.head_after or 'none'}"
            )
        ]
        if observation.status.strip():
            parts.append(f"status:\n{truncate(observation.status)}")
        return "\n".join(parts)

    if observation.kind == "git_diff":
        return "\n".join(
            [
                f"{index}. git_diff {observation.path or '.'}: {observation.message}",
                f"staged: {str(observation.staged).lower()}",
                f"maxOutputChars: {observation.max_output_chars}",
                f"truncated: {str(observation.truncated).lower()}",
                f"diff:\n{truncate(observation.diff)}",
            ]
        )

    if observation.kind == "git_diff_hunks":
        parts = [
            (
                f"{index}. git_diff_hunks {observation.path or '.'}: {observation.message} "
                f"shown={len(observation.hunks)}/{observation.total_hunks} "
                f"staged={str(observation.staged).lower()} "
                f"truncated={str(observation.truncated).lower()}"
            )
        ]
        for hunk in observation.hunks[:120]:
            parts.append(
                (
                    f"hunk: {hunk.file} old={hunk.old_start},{hunk.old_count} "
                    f"new={hunk.new_start},{hunk.new_count} "
                    f"added={hunk.added} deleted={hunk.deleted} context={hunk.context} "
                    f"linesTruncated={str(hunk.lines_truncated).lower()}"
                )
            )
            if hunk.lines:
                parts.append("lines:\n" + truncate("\n".join(hunk.lines)))
        return "\n".join(parts)

    if observation.kind == "git_diff_contexts":
        parts = [
            (
                f"{index}. git_diff_contexts {observation.path or '.'}: {observation.message} "
                f"shown={len(observation.contexts)}/{observation.total_hunks} "
                f"staged={str(observation.staged).lower()} "
                f"contextLines={observation.context_lines} "
                f"truncated={str(observation.truncated).lower()}"
            )
        ]
        for item in observation.contexts[:80]:
            hunk = item.hunk
            context = item.context
            parts.append(
                (
                    f"hunkContext: {hunk.file} old={hunk.old_start},{hunk.old_count} "
                    f"new={hunk.new_start},{hunk.new_count} added={hunk.added} deleted={hunk.deleted} "
                    f"contextOk={str(context.ok).lower()} targetExists={str(context.target_line_exists).lower()} "
                    f"sourceRange={context.start_line}-{context.end_line}"
                )
            )
            if context.ok and context.content:
                parts.append("source:\n" + truncate(context.content))
            elif not context.ok:
                parts.append(f"sourceError: {context.message}")
        return "\n".join(parts)

    if observation.kind == "git_log":
        return "\n".join(
            [
                f"{index}. git_log {observation.path or '.'}: {observation.message}",
                f"maxCount: {observation.max_count}",
                f"log:\n{truncate(observation.log)}",
            ]
        )

    if observation.kind == "git_show":
        target = f"{observation.rev} -- {observation.path}" if observation.path else observation.rev
        return "\n".join(
            [
                f"{index}. git_show {target}: {observation.message}",
                f"maxOutputChars: {observation.max_output_chars}",
                f"truncated: {str(observation.truncated).lower()}",
                f"output:\n{truncate(observation.output)}",
            ]
        )

    if observation.kind == "git_blame":
        line_range = ""
        if observation.start_line is not None:
            line_range = f":{observation.start_line}+{observation.line_count or 120}"
        return "\n".join(
            [
                f"{index}. git_blame {observation.path}{line_range}: {observation.message}",
                f"maxOutputChars: {observation.max_output_chars}",
                f"truncated: {str(observation.truncated).lower()}",
                f"blame:\n{truncate(observation.blame)}",
            ]
        )

    return None
__all__ = ["format_git_observation"]
