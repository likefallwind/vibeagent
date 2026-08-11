from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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
