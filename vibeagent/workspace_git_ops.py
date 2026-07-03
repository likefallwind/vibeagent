from __future__ import annotations

from .workspace_core import (
    GIT_CONFLICT_MARKERS,
    GIT_UNMERGED_STATUS_CODES,
    GitCommandResult,
    RunWorkspace,
)
from .workspace_git_utils import (
    run_git_mutation,
    run_readonly_git,
)
from .workspace_git_branch_ops import (
    git_branch_exists,
    git_status_has_non_runtime_changes,
    normalize_git_index_paths,
    read_git_current_branch,
    read_git_head,
    validate_git_branch_name,
)
from .workspace_git_index_ops import (
    commit_staged_changes,
    preview_commit_staged_changes,
    preview_restore_git_paths,
    preview_stage_git_paths,
    preview_switch_git_branch,
    preview_unstage_git_paths,
    restore_git_paths,
    stage_git_paths,
    switch_git_branch,
    unstage_git_paths,
    validate_git_tracked_paths,
)
from .workspace_git_remote_ops import (
    fetch_git_remote,
    preview_fetch_git_remote,
    preview_pull_git_upstream,
    preview_push_git_upstream,
    pull_git_upstream,
    push_git_upstream,
    read_git_info,
    read_git_upstream_parts,
    select_git_fetch_remote,
)
from .workspace_git_read_ops import (
    parse_git_diff_file_path,
    parse_git_diff_hunks,
    read_git_blame,
    read_git_diff,
    read_git_diff_hunks,
    read_git_log,
    read_git_show,
)
from .workspace_git_stash_ops import (
    apply_git_stash,
    dedupe_paths,
    drop_git_stash,
    git_stash_candidate_paths,
    normalize_git_stash_message,
    parse_git_stash_list,
    preview_apply_git_stash,
    preview_drop_git_stash,
    preview_stash_git_changes,
    read_git_stashes,
    stash_git_changes,
    validate_git_stash_ref,
)
from .workspace_project_info import list_search_files
from .workspace_resolve import resolve_inside_run


def read_git_status(workspace: RunWorkspace) -> GitCommandResult:
    return run_readonly_git(workspace.root, ["status", "--short", "--untracked-files=all"])


def read_git_conflicts(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_markers: int = 200,
    max_files: int = 5000,
) -> dict[str, object]:
    if max_markers < 1:
        raise ValueError("max_markers must be at least 1.")
    if max_markers > 1000:
        raise ValueError("max_markers must be at most 1000.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 10000:
        raise ValueError("max_files must be at most 10000.")

    selected_path = relative_path.strip() if relative_path else None
    status_args = ["status", "--porcelain=v1", "-z", "--untracked-files=all"]
    if selected_path:
        resolve_inside_run(workspace.root, selected_path)
        status_args.extend(["--", selected_path])
    status_result = run_readonly_git(workspace.root, status_args)
    if not status_result.ok:
        return {
            "ok": False,
            "path": selected_path or ".",
            "unmerged": [],
            "unmerged_total": 0,
            "markers": [],
            "markers_total": 0,
            "scanned_files": 0,
            "total_files": 0,
            "truncated": False,
            "message": status_result.stderr or "git status failed.",
        }

    unmerged = parse_git_unmerged_status(status_result.stdout)
    try:
        files = list_search_files(workspace, selected_path)
    except ValueError as error:
        if selected_path and unmerged:
            files = []
        else:
            raise error

    scanned_files = files[:max_files]
    markers: list[dict[str, object]] = []
    markers_total = 0
    for relative in scanned_files:
        path = resolve_inside_run(workspace.root, relative)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, start=1):
            marker = next((item for item in GIT_CONFLICT_MARKERS if line.startswith(item)), None)
            if marker is None:
                continue
            markers_total += 1
            if len(markers) >= max_markers:
                continue
            markers.append(
                {
                    "path": relative,
                    "line": line_number,
                    "marker": marker,
                    "text": line.strip(),
                }
            )

    truncated = len(files) > len(scanned_files) or markers_total > len(markers)
    return {
        "ok": True,
        "path": selected_path or ".",
        "unmerged": unmerged,
        "unmerged_total": len(unmerged),
        "markers": markers,
        "markers_total": markers_total,
        "scanned_files": len(scanned_files),
        "total_files": len(files),
        "truncated": truncated,
        "message": (
            f"Found {len(unmerged)} unmerged file(s) and {markers_total} conflict marker(s) "
            f"in {len(scanned_files)}/{len(files)} scanned file(s)."
        ),
    }

def parse_git_unmerged_status(output: str) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    parts = [part for part in output.split("\0") if part]
    index = 0
    while index < len(parts):
        entry = parts[index]
        index += 1
        if len(entry) < 4:
            continue
        status = entry[:2]
        path = entry[3:]
        if status in {"R ", "C "} and index < len(parts):
            index += 1
        if status not in GIT_UNMERGED_STATUS_CODES:
            continue
        entries.append({"path": path, "status": status})
    return entries


def read_git_branches(workspace: RunWorkspace, max_branches: int = 100) -> dict[str, object]:
    if max_branches < 1:
        raise ValueError("max_branches must be at least 1.")
    if max_branches > 500:
        raise ValueError("max_branches must be at most 500.")
    git_probe = run_readonly_git(workspace.root, ["rev-parse", "--is-inside-work-tree"])
    if not git_probe.ok or git_probe.stdout.strip() != "true":
        return {
            "ok": False,
            "current": "",
            "branches": [],
            "total": 0,
            "truncated": False,
            "status": "",
            "message": git_probe.stderr or "Not a git repository.",
        }

    current_result = run_readonly_git(workspace.root, ["branch", "--show-current"])
    branches_result = run_readonly_git(workspace.root, ["branch", "--list", "--format=%(refname:short)"])
    status = read_git_status(workspace)
    if not branches_result.ok:
        return {
            "ok": False,
            "current": current_result.stdout.strip() if current_result.ok else "",
            "branches": [],
            "total": 0,
            "truncated": False,
            "status": status.stdout if status.ok else "",
            "message": branches_result.stderr or "git branch failed.",
        }

    current = current_result.stdout.strip() if current_result.ok else ""
    names = [line.strip() for line in branches_result.stdout.splitlines() if line.strip()]
    total = len(names)
    shown = names[:max_branches]
    return {
        "ok": True,
        "current": current,
        "branches": [{"name": name, "current": name == current} for name in shown],
        "total": total,
        "truncated": len(shown) < total,
        "status": status.stdout if status.ok else "",
        "message": f"Found {total} local git branch(es).",
    }
