from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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
