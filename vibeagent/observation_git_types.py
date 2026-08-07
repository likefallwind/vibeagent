from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .observation_git_conflict_types import GitConflictMarker, GitConflictStatus, GitConflictsObservation
from .observation_git_read_types import (
    GitBlameObservation,
    GitDiffContext,
    GitDiffContextsObservation,
    GitDiffHunk,
    GitDiffHunksObservation,
    GitDiffObservation,
    GitLogObservation,
    GitShowObservation,
    UntrackedFilePreview,
)
from .observation_git_sync_types import (
    CheckGitFetchObservation,
    CheckGitPullObservation,
    CheckGitPushObservation,
    GitFetchObservation,
    GitPullObservation,
    GitPushObservation,
)


@dataclass(frozen=True)
class GitStatusObservation:
    kind: Literal["git_status"]
    ok: bool
    status: str
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
    message_text: str = ""


@dataclass(frozen=True)
class CheckGitCommitObservation:
    kind: Literal["check_git_commit"]
    ok: bool
    head_before: str
    head_after: str
    status: str
    message: str
    message_text: str = ""
