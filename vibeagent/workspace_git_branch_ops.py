from __future__ import annotations

from .workspace_core import RunWorkspace
from .workspace_git_utils import run_readonly_git
from .workspace_resolve import resolve_inside_run


def validate_git_branch_name(workspace: RunWorkspace, branch: str) -> str:
    normalized = branch.strip()
    if not normalized:
        raise ValueError("branch must be a non-empty string.")
    if len(normalized) > 200:
        raise ValueError("branch must be at most 200 characters.")
    result = run_readonly_git(workspace.root, ["check-ref-format", "--branch", normalized])
    if not result.ok:
        raise ValueError(result.stderr.strip() or f"Invalid git branch name: {normalized}")
    return normalized


def git_branch_exists(workspace: RunWorkspace, branch: str) -> bool:
    result = run_readonly_git(workspace.root, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"])
    return result.exit_code == 0


def read_git_current_branch(workspace: RunWorkspace) -> str:
    result = run_readonly_git(workspace.root, ["branch", "--show-current"])
    return result.stdout.strip() if result.ok else ""


def git_status_has_non_runtime_changes(status: str) -> bool:
    for line in status.splitlines():
        path = line[3:] if len(line) > 3 else line
        if path == ".vibeagent" or path.startswith(".vibeagent/"):
            continue
        return True
    return False


def read_git_head(workspace: RunWorkspace) -> str:
    result = run_readonly_git(workspace.root, ["rev-parse", "--short", "HEAD"])
    return result.stdout.strip() if result.ok else ""


def normalize_git_index_paths(workspace: RunWorkspace, paths: list[str]) -> list[str]:
    if not paths:
        raise ValueError("paths must contain at least one path.")
    if len(paths) > 100:
        raise ValueError("paths must contain at most 100 paths.")

    normalized: list[str] = []
    seen: set[str] = set()
    for path in paths:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("paths must contain non-empty strings.")
        raw = path.strip()
        resolve_inside_run(workspace.root, raw)
        if raw not in seen:
            seen.add(raw)
            normalized.append(raw)
    return normalized
