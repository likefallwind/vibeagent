from __future__ import annotations

from .prompt_observation_utils import truncate


def format_review_observation(index: int, observation: object) -> str | None:
    if getattr(observation, "kind", None) == "deep_review":
        return _format_deep_review(index, observation)
    if observation.kind == "review_changes":
        return _format_review_changes(index, observation)
    if observation.kind == "final_review":
        return _format_final_review(index, observation)
    return None


def _format_deep_review(index: int, observation: object) -> str:
    scope = (
        getattr(observation, "target", None)
        or getattr(observation, "base_ref", None)
        or "current branch and worktree"
    )
    parts = [
        f"{index}. deep_review scope={scope}: {getattr(observation, 'message', '')}",
        f"verified findings:\n{truncate(str(getattr(observation, 'summary', '')))}",
    ]
    for result in getattr(observation, "results", []):
        parts.append(
            f"[{getattr(result, 'perspective', '')}] ok={str(bool(getattr(result, 'ok', False))).lower()} "
            f"iterations={getattr(result, 'iterations', 0)}\n"
            f"{truncate(str(getattr(result, 'summary', '')))}"
        )
    return "\n".join(parts)


def _format_review_changes(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. review_changes: {observation.message} "
            f"ok={str(observation.ok).lower()} "
            f"diffCheck={str(observation.diff_check_ok).lower()} "
            f"stagedDiffCheck={str(observation.staged_diff_check_ok).lower()} "
            f"pythonOk={str(observation.python_ok).lower()} "
            f"configOk={str(observation.config_ok).lower()} "
            f"changed={len(observation.files)}/{observation.total_files} "
            f"python={len(observation.python)}/{observation.python_total} "
            f"pythonTruncated={str(observation.python_truncated).lower()} "
            f"config={len(observation.config)}/{observation.config_total} "
            f"configTruncated={str(observation.config_truncated).lower()} "
            f"suggestedChecks={len(observation.suggested_checks)}/{observation.suggested_checks_total} "
            f"suggestedChecksTruncated={str(observation.suggested_checks_truncated).lower()} "
            f"diffHunks={len(observation.diff_hunks)}/{observation.diff_hunks_total} "
            f"diffHunksTruncated={str(observation.diff_hunks_truncated).lower()} "
            f"stagedDiffHunks={len(observation.staged_diff_hunks)}/{observation.staged_diff_hunks_total} "
            f"stagedDiffHunksTruncated={str(observation.staged_diff_hunks_truncated).lower()} "
            f"untrackedPreviews={len(observation.untracked_previews)}/{observation.untracked_previews_total} "
            f"untrackedPreviewsTruncated={str(observation.untracked_previews_truncated).lower()}"
        )
    ]
    for file in observation.files[:120]:
        parts.append(
            (
                f"file: {file.path} status={file.status or '..'} "
                f"staged={str(file.staged).lower()} unstaged={str(file.unstaged).lower()} "
                f"untracked={str(file.untracked).lower()}"
            )
        )
    for file in observation.python[:120]:
        location = ""
        if file.line is not None:
            location = f" line={file.line} column={file.column or 'unknown'}"
        parts.append(f"python: {file.path} ok={str(file.ok).lower()}{location} message={file.message}")
    for file in observation.config[:120]:
        location = ""
        if file.line is not None:
            location = f" line={file.line} column={file.column or 'unknown'}"
        parts.append(
            (
                f"config: {file.path} format={file.format} ok={str(file.ok).lower()}"
                f"{location} message={file.message}"
            )
        )
    for check in observation.suggested_checks[:40]:
        parts.append(
            (
                f"check: cwd={check.cwd} command={check.command} "
                f"available={str(check.available).lower()} missingTool={check.missing_tool or '.'} "
                f"source={check.source} reason={check.reason}"
            )
        )
    for hunk in observation.diff_hunks[:40]:
        parts.append(
            (
                f"diff_hunk: {hunk.file} old={hunk.old_start},{hunk.old_count} "
                f"new={hunk.new_start},{hunk.new_count} added={hunk.added} "
                f"deleted={hunk.deleted} linesTruncated={str(hunk.lines_truncated).lower()}"
            )
        )
    for hunk in observation.staged_diff_hunks[:40]:
        parts.append(
            (
                f"staged_diff_hunk: {hunk.file} old={hunk.old_start},{hunk.old_count} "
                f"new={hunk.new_start},{hunk.new_count} added={hunk.added} "
                f"deleted={hunk.deleted} linesTruncated={str(hunk.lines_truncated).lower()}"
            )
        )
    for preview in observation.untracked_previews[:40]:
        parts.append(
            (
                f"untracked_preview: {preview.path} size={preview.size_bytes} "
                f"binary={str(preview.is_binary).lower()} "
                f"truncated={str(preview.truncated).lower()} message={preview.message}"
            )
        )
        if preview.content:
            parts.append(f"untracked_content {preview.path}:\n{truncate(preview.content, 4000)}")
    if observation.diff_check.strip():
        parts.append(f"diff_check:\n{truncate(observation.diff_check)}")
    if observation.staged_diff_check.strip():
        parts.append(f"staged_diff_check:\n{truncate(observation.staged_diff_check)}")
    if observation.status.strip():
        parts.append(f"status:\n{truncate(observation.status)}")
    return "\n".join(parts)


def _format_final_review(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. final_review: {observation.message} "
            f"ok={str(observation.ok).lower()} "
            f"ready={str(observation.ready).lower()} "
            f"blocking={len(observation.blocking_issues)} "
            f"warnings={len(observation.warnings)} "
            f"runningProcesses={len(observation.running_processes)} "
            f"changed={len(observation.files)}/{observation.total_files} "
            f"suggestedChecks={len(observation.suggested_checks)}/{observation.suggested_checks_total} "
            f"suggestedChecksTruncated={str(observation.suggested_checks_truncated).lower()} "
            f"focusedTests={len(observation.focused_test_commands)}/{observation.focused_test_commands_total} "
            f"focusedTestsTruncated={str(observation.focused_test_commands_truncated).lower()} "
            f"relatedTests={observation.focused_test_related_tests_total}"
        )
    ]
    for issue in observation.blocking_issues[:20]:
        parts.append(f"blocking_issue: {issue}")
    for warning in observation.warnings[:20]:
        parts.append(f"warning: {warning}")
    for check in observation.python[:20]:
        if not check.ok:
            parts.append(
                (
                    f"python_failure: {check.path} line={check.line or '.'} "
                    f"column={check.column or '.'} message={check.message}"
                )
            )
    for check in observation.config[:20]:
        if not check.ok:
            parts.append(
                (
                    f"config_failure: {check.path} line={check.line or '.'} "
                    f"column={check.column or '.'} message={check.message}"
                )
            )
    for process in observation.running_processes[:20]:
        parts.append(
            (
                f"running_process: {process.process_id} pid={process.pid} cwd={process.cwd} "
                f"command={process.command}"
            )
        )
    for file in observation.files[:120]:
        parts.append(
            (
                f"file: {file.path} status={file.status or '..'} "
                f"staged={str(file.staged).lower()} unstaged={str(file.unstaged).lower()} "
                f"untracked={str(file.untracked).lower()}"
            )
        )
    for check in observation.suggested_checks[:40]:
        parts.append(
            (
                f"check: cwd={check.cwd} command={check.command} "
                f"available={str(check.available).lower()} missingTool={check.missing_tool or '.'} "
                f"source={check.source} reason={check.reason}"
            )
        )
    for command in observation.focused_test_commands[:40]:
        parts.append(
            (
                f"focused_test: cwd={command.cwd} command={command.command} "
                f"test={command.test_path} source={command.source} reason={command.reason}"
            )
        )
    if observation.diff_check.strip():
        parts.append(f"diff_check:\n{truncate(observation.diff_check)}")
    if observation.staged_diff_check.strip():
        parts.append(f"staged_diff_check:\n{truncate(observation.staged_diff_check)}")
    if observation.status.strip():
        parts.append(f"status:\n{truncate(observation.status)}")
    return "\n".join(parts)


__all__ = ["format_review_observation"]
