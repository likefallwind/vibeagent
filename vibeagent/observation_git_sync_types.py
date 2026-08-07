from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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


__all__ = [
    "CheckGitFetchObservation",
    "CheckGitPullObservation",
    "CheckGitPushObservation",
    "GitFetchObservation",
    "GitPullObservation",
    "GitPushObservation",
]
