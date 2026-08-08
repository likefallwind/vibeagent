from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class EnterWorktreeAction:
    type: Literal["enter_worktree"]
    name: str | None = None
    path: str | None = None


@dataclass(frozen=True)
class ExitWorktreeAction:
    type: Literal["exit_worktree"]


@dataclass(frozen=True)
class GitStatusAction:
    type: Literal["git_status"]


@dataclass(frozen=True)
class GitConflictsAction:
    type: Literal["git_conflicts"]
    path: str | None = None
    max_markers: int = 200
    max_files: int = 5000


@dataclass(frozen=True)
class GitInfoAction:
    type: Literal["git_info"]


@dataclass(frozen=True)
class GitChangesAction:
    type: Literal["git_changes"]


@dataclass(frozen=True)
class GitBranchesAction:
    type: Literal["git_branches"]
    max_branches: int = 100


@dataclass(frozen=True)
class CheckGitFetchAction:
    type: Literal["check_git_fetch"]
    remote: str | None = None


@dataclass(frozen=True)
class GitFetchAction:
    type: Literal["git_fetch"]
    remote: str | None = None


@dataclass(frozen=True)
class CheckGitPullAction:
    type: Literal["check_git_pull"]


@dataclass(frozen=True)
class GitPullAction:
    type: Literal["git_pull"]


@dataclass(frozen=True)
class CheckGitPushAction:
    type: Literal["check_git_push"]


@dataclass(frozen=True)
class GitPushAction:
    type: Literal["git_push"]


@dataclass(frozen=True)
class CheckGitRestoreAction:
    type: Literal["check_git_restore"]
    paths: list[str]


@dataclass(frozen=True)
class GitRestoreAction:
    type: Literal["git_restore"]
    paths: list[str]


@dataclass(frozen=True)
class GitStashesAction:
    type: Literal["git_stashes"]
    max_entries: int = 20


@dataclass(frozen=True)
class CheckGitStashAction:
    type: Literal["check_git_stash"]
    message: str | None = None
    include_untracked: bool = False


@dataclass(frozen=True)
class GitStashAction:
    type: Literal["git_stash"]
    message: str | None = None
    include_untracked: bool = False


@dataclass(frozen=True)
class CheckGitStashApplyAction:
    type: Literal["check_git_stash_apply"]
    stash_ref: str


@dataclass(frozen=True)
class GitStashApplyAction:
    type: Literal["git_stash_apply"]
    stash_ref: str


@dataclass(frozen=True)
class CheckGitStashDropAction:
    type: Literal["check_git_stash_drop"]
    stash_ref: str


@dataclass(frozen=True)
class GitStashDropAction:
    type: Literal["git_stash_drop"]
    stash_ref: str


@dataclass(frozen=True)
class GitSwitchAction:
    type: Literal["git_switch"]
    branch: str
    create: bool = False


@dataclass(frozen=True)
class CheckGitSwitchAction:
    type: Literal["check_git_switch"]
    branch: str
    create: bool = False


@dataclass(frozen=True)
class GitStageAction:
    type: Literal["git_stage"]
    paths: list[str]


@dataclass(frozen=True)
class CheckGitStageAction:
    type: Literal["check_git_stage"]
    paths: list[str]


@dataclass(frozen=True)
class GitUnstageAction:
    type: Literal["git_unstage"]
    paths: list[str]


@dataclass(frozen=True)
class CheckGitUnstageAction:
    type: Literal["check_git_unstage"]
    paths: list[str]


@dataclass(frozen=True)
class GitCommitAction:
    type: Literal["git_commit"]
    message: str


@dataclass(frozen=True)
class CheckGitCommitAction:
    type: Literal["check_git_commit"]
    message: str


@dataclass(frozen=True)
class GitDiffAction:
    type: Literal["git_diff"]
    path: str | None = None
    staged: bool = False
    max_output_chars: int = 12000


@dataclass(frozen=True)
class GitDiffHunksAction:
    type: Literal["git_diff_hunks"]
    path: str | None = None
    staged: bool = False
    max_hunks: int = 80
    max_lines_per_hunk: int = 80


@dataclass(frozen=True)
class GitDiffContextsAction:
    type: Literal["git_diff_contexts"]
    path: str | None = None
    staged: bool = False
    context_lines: int = 5
    max_hunks: int = 80
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class GitLogAction:
    type: Literal["git_log"]
    max_count: int = 5
    path: str | None = None


@dataclass(frozen=True)
class GitShowAction:
    type: Literal["git_show"]
    rev: str = "HEAD"
    path: str | None = None
    max_output_chars: int = 12000


@dataclass(frozen=True)
class GitBlameAction:
    type: Literal["git_blame"]
    path: str
    start_line: int | None = None
    line_count: int | None = None
    max_output_chars: int = 12000
