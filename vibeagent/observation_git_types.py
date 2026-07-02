from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .observation_read_types import ReadFileContextResult


@dataclass(frozen=True)
class GitStatusObservation:
    kind: Literal["git_status"]
    ok: bool
    status: str
    message: str


@dataclass(frozen=True)
class GitConflictStatus:
    path: str
    status: str


@dataclass(frozen=True)
class GitConflictMarker:
    path: str
    line: int
    marker: str
    text: str


@dataclass(frozen=True)
class GitConflictsObservation:
    kind: Literal["git_conflicts"]
    ok: bool
    path: str
    unmerged: list[GitConflictStatus]
    unmerged_total: int
    markers: list[GitConflictMarker]
    markers_total: int
    scanned_files: int
    total_files: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class GitRemote:
    name: str
    url: str
    kind: str


@dataclass(frozen=True)
class GitInfoObservation:
    kind: Literal["git_info"]
    ok: bool
    is_git_repo: bool
    branch: str
    head: str
    upstream: str
    ahead: int
    behind: int
    remotes: list[GitRemote]
    status: str
    message: str


@dataclass(frozen=True)
class GitChangeFile:
    path: str
    status: str
    staged: bool
    unstaged: bool
    untracked: bool
    staged_insertions: int
    staged_deletions: int
    unstaged_insertions: int
    unstaged_deletions: int
    binary: bool


@dataclass(frozen=True)
class GitChangesObservation:
    kind: Literal["git_changes"]
    ok: bool
    files: list[GitChangeFile]
    status: str
    message: str


@dataclass(frozen=True)
class GitBranchInfo:
    name: str
    current: bool


@dataclass(frozen=True)
class GitBranchesObservation:
    kind: Literal["git_branches"]
    ok: bool
    current: str
    branches: list[GitBranchInfo]
    total: int
    truncated: bool
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitFetchObservation:
    kind: Literal["check_git_fetch"]
    ok: bool
    remote: str
    remote_url: str
    branch: str
    upstream: str
    ahead: int
    behind: int
    message: str


@dataclass(frozen=True)
class GitFetchObservation:
    kind: Literal["git_fetch"]
    ok: bool
    remote: str
    remote_url: str
    branch: str
    upstream: str
    ahead_before: int
    behind_before: int
    ahead_after: int
    behind_after: int
    message: str


@dataclass(frozen=True)
class CheckGitPullObservation:
    kind: Literal["check_git_pull"]
    ok: bool
    remote: str
    branch: str
    current: str
    upstream: str
    ahead: int
    behind: int
    worktree_clean: bool
    status: str
    message: str


@dataclass(frozen=True)
class GitPullObservation:
    kind: Literal["git_pull"]
    ok: bool
    remote: str
    branch: str
    current_before: str
    current_after: str
    upstream: str
    ahead_before: int
    behind_before: int
    ahead_after: int
    behind_after: int
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitPushObservation:
    kind: Literal["check_git_push"]
    ok: bool
    remote: str
    branch: str
    current: str
    upstream: str
    ahead: int
    behind: int
    worktree_clean: bool
    status: str
    message: str


@dataclass(frozen=True)
class GitPushObservation:
    kind: Literal["git_push"]
    ok: bool
    remote: str
    branch: str
    current: str
    upstream: str
    ahead_before: int
    behind_before: int
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitRestoreObservation:
    kind: Literal["check_git_restore"]
    ok: bool
    paths: list[str]
    diff: str
    status: str
    message: str


@dataclass(frozen=True)
class GitRestoreObservation:
    kind: Literal["git_restore"]
    ok: bool
    paths: list[str]
    diff: str
    status: str
    message: str


@dataclass(frozen=True)
class GitStashEntry:
    name: str
    summary: str


@dataclass(frozen=True)
class GitStashesObservation:
    kind: Literal["git_stashes"]
    ok: bool
    entries: list[GitStashEntry]
    total: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class CheckGitStashObservation:
    kind: Literal["check_git_stash"]
    ok: bool
    message_text: str
    include_untracked: bool
    status: str
    diff: str
    message: str


@dataclass(frozen=True)
class GitStashObservation:
    kind: Literal["git_stash"]
    ok: bool
    message_text: str
    include_untracked: bool
    stash_ref: str
    status: str
    diff: str
    message: str


@dataclass(frozen=True)
class CheckGitStashApplyObservation:
    kind: Literal["check_git_stash_apply"]
    ok: bool
    stash_ref: str
    worktree_clean: bool
    patch: str
    status: str
    message: str


@dataclass(frozen=True)
class GitStashApplyObservation:
    kind: Literal["git_stash_apply"]
    ok: bool
    stash_ref: str
    patch: str
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitStashDropObservation:
    kind: Literal["check_git_stash_drop"]
    ok: bool
    stash_ref: str
    patch: str
    summary: str
    message: str


@dataclass(frozen=True)
class GitStashDropObservation:
    kind: Literal["git_stash_drop"]
    ok: bool
    stash_ref: str
    patch: str
    summary: str
    remaining_total: int
    message: str


@dataclass(frozen=True)
class GitSwitchObservation:
    kind: Literal["git_switch"]
    ok: bool
    branch: str
    create: bool
    current_before: str
    current_after: str
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitSwitchObservation:
    kind: Literal["check_git_switch"]
    ok: bool
    branch: str
    create: bool
    current_before: str
    branch_exists: bool
    worktree_clean: bool
    status: str
    message: str


@dataclass(frozen=True)
class GitStageObservation:
    kind: Literal["git_stage"]
    ok: bool
    paths: list[str]
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitStageObservation:
    kind: Literal["check_git_stage"]
    ok: bool
    paths: list[str]
    status: str
    message: str


@dataclass(frozen=True)
class GitUnstageObservation:
    kind: Literal["git_unstage"]
    ok: bool
    paths: list[str]
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitUnstageObservation:
    kind: Literal["check_git_unstage"]
    ok: bool
    paths: list[str]
    status: str
    message: str


@dataclass(frozen=True)
class GitCommitObservation:
    kind: Literal["git_commit"]
    ok: bool
    head_before: str
    head_after: str
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitCommitObservation:
    kind: Literal["check_git_commit"]
    ok: bool
    head_before: str
    head_after: str
    status: str
    message: str


@dataclass(frozen=True)
class GitDiffHunk:
    file: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    added: int
    deleted: int
    context: int
    header: str
    lines: list[str]
    lines_truncated: bool


@dataclass(frozen=True)
class UntrackedFilePreview:
    path: str
    size_bytes: int
    is_binary: bool
    content: str
    truncated: bool
    message: str


@dataclass(frozen=True)
class GitDiffObservation:
    kind: Literal["git_diff"]
    ok: bool
    diff: str
    path: str | None
    staged: bool
    truncated: bool
    max_output_chars: int
    message: str


@dataclass(frozen=True)
class GitDiffHunksObservation:
    kind: Literal["git_diff_hunks"]
    ok: bool
    hunks: list[GitDiffHunk]
    total_hunks: int
    truncated: bool
    path: str | None
    staged: bool
    message: str


@dataclass(frozen=True)
class GitDiffContext:
    hunk: GitDiffHunk
    context: ReadFileContextResult


@dataclass(frozen=True)
class GitDiffContextsObservation:
    kind: Literal["git_diff_contexts"]
    ok: bool
    contexts: list[GitDiffContext]
    total_hunks: int
    truncated: bool
    path: str | None
    staged: bool
    context_lines: int
    message: str


@dataclass(frozen=True)
class GitLogObservation:
    kind: Literal["git_log"]
    ok: bool
    log: str
    max_count: int
    path: str | None
    message: str


@dataclass(frozen=True)
class GitShowObservation:
    kind: Literal["git_show"]
    ok: bool
    output: str
    rev: str
    path: str | None
    truncated: bool
    max_output_chars: int
    message: str


@dataclass(frozen=True)
class GitBlameObservation:
    kind: Literal["git_blame"]
    ok: bool
    blame: str
    path: str
    start_line: int | None
    line_count: int | None
    truncated: bool
    max_output_chars: int
    message: str
