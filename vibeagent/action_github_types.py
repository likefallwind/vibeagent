from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class GitHubIssueContextAction:
    type: Literal["github_issue_context"]
    issue: str
    remote: str | None = None


@dataclass(frozen=True)
class CheckGitHubIssueCommentAction:
    type: Literal["check_github_issue_comment"]
    body: str
    issue: str
    remote: str | None = None


@dataclass(frozen=True)
class GitHubIssueCommentAction:
    type: Literal["github_issue_comment"]
    body: str
    issue: str
    remote: str | None = None


@dataclass(frozen=True)
class CheckGitHubPrCreateAction:
    type: Literal["check_github_pr_create"]
    title: str
    body: str = ""
    base: str | None = None
    remote: str | None = None
    draft: bool = False


@dataclass(frozen=True)
class GitHubPrCreateAction:
    type: Literal["github_pr_create"]
    title: str
    body: str = ""
    base: str | None = None
    remote: str | None = None
    draft: bool = False


@dataclass(frozen=True)
class GitHubPrContextAction:
    type: Literal["github_pr_context"]
    pr: str | None = None
    remote: str | None = None


@dataclass(frozen=True)
class GitHubPrCiLogsAction:
    type: Literal["github_pr_ci_logs"]
    pr: str | None = None
    remote: str | None = None
    max_runs: int = 3
    max_output_chars: int = 30_000


@dataclass(frozen=True)
class CheckGitHubPrCommentAction:
    type: Literal["check_github_pr_comment"]
    body: str
    pr: str | None = None
    remote: str | None = None
    reply_to: int | None = None


@dataclass(frozen=True)
class GitHubPrCommentAction:
    type: Literal["github_pr_comment"]
    body: str
    pr: str | None = None
    remote: str | None = None
    reply_to: int | None = None
