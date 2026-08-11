from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class GitHubPrComment:
    kind: Literal["comment", "inline"]
    author: str
    body: str
    created_at: str
    url: str
    comment_id: int | None = None
    path: str = ""
    line: int | None = None


@dataclass(frozen=True)
class GitHubPrReview:
    author: str
    state: str
    body: str
    submitted_at: str
    url: str


@dataclass(frozen=True)
class GitHubPrCheck:
    name: str
    state: str
    bucket: str
    workflow: str
    link: str


@dataclass(frozen=True)
class GitHubPrFile:
    path: str
    additions: int
    deletions: int


@dataclass(frozen=True)
class GitHubPrFailedCheck:
    name: str
    state: str
    workflow: str
    link: str
    run_id: str


@dataclass(frozen=True)
class GitHubPrCiRun:
    run_id: str
    url: str
    check_names: list[str]
    logs: str
    logs_truncated: bool
    error: str


@dataclass(frozen=True)
class CheckGitHubPrCreateObservation:
    kind: Literal["check_github_pr_create"]
    ok: bool
    repository: str
    remote: str
    head: str
    base: str
    title: str
    draft: bool
    ahead: int
    behind: int
    commits: int
    message: str


@dataclass(frozen=True)
class GitHubPrCreateObservation:
    kind: Literal["github_pr_create"]
    ok: bool
    repository: str
    remote: str
    head: str
    base: str
    title: str
    draft: bool
    ahead: int
    behind: int
    commits: int
    url: str
    message: str


@dataclass(frozen=True)
class GitHubPrContextObservation:
    kind: Literal["github_pr_context"]
    ok: bool
    repository: str
    number: int
    url: str
    title: str
    body: str
    author: str
    state: str
    is_draft: bool
    head: str
    base: str
    additions: int
    deletions: int
    changed_files: int
    mergeable: str
    merge_state: str
    review_decision: str
    comments: list[GitHubPrComment]
    comments_total: int
    comments_truncated: bool
    reviews: list[GitHubPrReview]
    reviews_total: int
    reviews_truncated: bool
    checks: list[GitHubPrCheck]
    checks_total: int
    checks_truncated: bool
    files: list[GitHubPrFile]
    files_total: int
    files_truncated: bool
    message: str


@dataclass(frozen=True)
class GitHubPrCiLogsObservation:
    kind: Literal["github_pr_ci_logs"]
    ok: bool
    repository: str
    selector: str
    failed_checks: list[GitHubPrFailedCheck]
    failed_total: int
    failed_truncated: bool
    runs: list[GitHubPrCiRun]
    runs_total: int
    runs_truncated: bool
    message: str


@dataclass(frozen=True)
class CheckGitHubPrCommentObservation:
    kind: Literal["check_github_pr_comment"]
    ok: bool
    repository: str
    selector: str
    pr: str | None
    remote: str | None
    reply_to: int | None
    body_chars: int
    body_sha256: str
    comment_target: str
    message: str


@dataclass(frozen=True)
class GitHubPrCommentObservation:
    kind: Literal["github_pr_comment"]
    ok: bool
    repository: str
    selector: str
    pr: str | None
    remote: str | None
    reply_to: int | None
    body_chars: int
    body_sha256: str
    comment_target: str
    url: str
    message: str
