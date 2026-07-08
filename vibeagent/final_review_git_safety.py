from __future__ import annotations

import os
from pathlib import Path

from .workspace import is_protected_project_path, read_git_status, should_ignore_path
from .workspace_core import RunWorkspace
from .workspace_git_utils import parse_git_short_status, run_readonly_git, should_ignore_git_path


def find_nested_git_repositories(workspace: RunWorkspace, max_repos: int = 10) -> tuple[list[str], int]:
    root = workspace.root.resolve()
    ignored_dirs = {
        ".agents",
        ".codex",
        ".git",
        ".pytest_cache",
        ".venv",
        ".vibeagent",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
    repos: list[str] = []
    total = 0
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        if current_path == root:
            if ".git" in dirs:
                dirs.remove(".git")
        elif ".git" in dirs or ".git" in files:
            total += 1
            if len(repos) < max_repos:
                repos.append(current_path.relative_to(root).as_posix())
            if ".git" in dirs:
                dirs.remove(".git")
        dirs[:] = [
            name
            for name in dirs
            if name not in ignored_dirs and not name.endswith(".egg-info")
        ]
    return repos, total


def find_changed_gitlinks(workspace: RunWorkspace, max_links: int = 10) -> tuple[list[str], int, list[str]]:
    links: list[str] = []
    total = 0
    warnings: list[str] = []
    seen: set[str] = set()
    for diff_args in (
        ["diff", "--raw", "--no-renames"],
        ["diff", "--cached", "--raw", "--no-renames"],
    ):
        result = run_readonly_git(workspace.root, diff_args)
        if not result.ok:
            warnings.append(result.stderr.strip() or f"git {' '.join(diff_args)} failed")
            continue
        for line in result.stdout.splitlines():
            path = gitlink_path_from_raw_diff_line(line)
            if path is None or path in seen:
                continue
            seen.add(path)
            total += 1
            if len(links) < max_links:
                links.append(path)
    return links, total, warnings


def gitlink_path_from_raw_diff_line(line: str) -> str | None:
    metadata, separator, path = line.partition("\t")
    if not separator:
        return None
    fields = metadata.split()
    if len(fields) < 2:
        return None
    old_mode = fields[0].removeprefix(":")
    new_mode = fields[1]
    if old_mode != "160000" and new_mode != "160000":
        return None
    return path.strip() or None


def find_hidden_tracked_git_changes(workspace: RunWorkspace, max_files: int = 10) -> tuple[list[dict[str, str]], int, list[str]]:
    status = read_git_status(workspace)
    if not status.ok:
        return [], 0, [status.stderr.strip() or "git status failed"]
    findings: list[dict[str, str]] = []
    total = 0
    for path, short_status in parse_git_short_status(status.stdout):
        if short_status == "??":
            continue
        if not should_ignore_git_path(workspace.root, path):
            continue
        total += 1
        if len(findings) < max_files:
            findings.append({"path": path, "status": short_status})
    return findings, total, []


def find_unsafe_changed_symlinks(
    workspace: RunWorkspace,
    files: list[dict[str, object]],
    max_links: int = 10,
) -> tuple[list[dict[str, str]], int, list[str], set[str]]:
    root = workspace.root.resolve()
    candidates: dict[str, str] = {}
    warnings: list[str] = []

    for item in files:
        raw_path = item.get("path") if isinstance(item, dict) else None
        if not isinstance(raw_path, str) or not raw_path:
            continue
        link_path = root / raw_path
        try:
            if link_path.is_symlink():
                candidates.setdefault(raw_path, "worktree")
        except OSError:
            continue

    for diff_args, source in (
        (["diff", "--raw", "--no-renames"], "worktree"),
        (["diff", "--cached", "--raw", "--no-renames"], "index"),
    ):
        result = run_readonly_git(workspace.root, diff_args)
        if not result.ok:
            warnings.append(result.stderr.strip() or f"git {' '.join(diff_args)} failed")
            continue
        for line in result.stdout.splitlines():
            path = symlink_path_from_raw_diff_line(line)
            if path is not None:
                candidates.setdefault(path, source)

    findings: list[dict[str, str]] = []
    reasons: set[str] = set()
    total = 0
    for relative_path, source in sorted(candidates.items()):
        target = read_changed_symlink_target(workspace, relative_path, source)
        if target is None:
            continue
        risk = changed_symlink_target_risk(root, root / relative_path, target)
        if risk is None:
            continue
        reasons.add(risk)
        total += 1
        if len(findings) < max_links:
            findings.append({"path": relative_path, "target": target, "reason": risk})
    return findings, total, warnings, reasons


def symlink_path_from_raw_diff_line(line: str) -> str | None:
    metadata, separator, path = line.partition("\t")
    if not separator:
        return None
    fields = metadata.split()
    if len(fields) < 2:
        return None
    new_mode = fields[1]
    if new_mode != "120000":
        return None
    return path.strip() or None


def read_changed_symlink_target(workspace: RunWorkspace, relative_path: str, source: str) -> str | None:
    link_path = workspace.root / relative_path
    if source == "worktree" or link_path.is_symlink():
        try:
            return os.readlink(link_path)
        except OSError:
            if source == "worktree":
                return None
    result = run_readonly_git(workspace.root, ["show", f":{relative_path}"])
    if not result.ok:
        return None
    target = result.stdout.strip()
    return target or None


def changed_symlink_target_risk(root: Path, link_path: Path, target: str) -> str | None:
    target_path = Path(target)
    if target_path.is_absolute():
        resolved = target_path.resolve(strict=False)
    else:
        resolved = (link_path.parent / target_path).resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        return "points outside project"
    if is_protected_project_path(root, resolved):
        return "points into protected project path"
    if should_ignore_path(root, resolved):
        return "points into ignored project path"
    return None


def read_git_operation_state(workspace: RunWorkspace) -> dict[str, object]:
    git_dir_result = run_readonly_git(workspace.root, ["rev-parse", "--git-dir"])
    if not git_dir_result.ok:
        return {"ok": False, "operations": [], "message": git_dir_result.stderr or "Not a git repository."}
    raw_git_dir = git_dir_result.stdout.strip().splitlines()[0] if git_dir_result.stdout.strip() else ""
    if not raw_git_dir:
        return {"ok": False, "operations": [], "message": "Could not determine git dir."}
    git_dir = Path(raw_git_dir)
    if not git_dir.is_absolute():
        git_dir = (workspace.root / git_dir).resolve()
    operation_paths = (
        ("merge", "MERGE_HEAD"),
        ("cherry-pick", "CHERRY_PICK_HEAD"),
        ("revert", "REVERT_HEAD"),
        ("rebase", "rebase-merge"),
        ("rebase", "rebase-apply"),
        ("bisect", "BISECT_LOG"),
    )
    operations: list[dict[str, str]] = []
    seen: set[str] = set()
    for name, relative in operation_paths:
        if name in seen:
            continue
        if (git_dir / relative).exists():
            operations.append({"operation": name, "path": relative})
            seen.add(name)
    message = "No git operation in progress." if not operations else "Git operation in progress."
    return {"ok": True, "operations": operations, "message": message}
