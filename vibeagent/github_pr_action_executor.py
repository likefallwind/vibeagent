from __future__ import annotations

from .github_pr_runtime import create_github_pr, preview_github_pr_create
from .types import (
    CheckGitHubPrCreateAction,
    CheckGitHubPrCreateObservation,
    GitHubPrCreateAction,
    GitHubPrCreateObservation,
    Observation,
)
from .workspace import RunWorkspace


def execute_github_pr_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if not isinstance(action, (CheckGitHubPrCreateAction, GitHubPrCreateAction)):
        return None
    options = {"title": action.title, "body": action.body, "base": action.base, "remote": action.remote, "draft": action.draft}
    result = preview_github_pr_create(workspace, **options) if isinstance(action, CheckGitHubPrCreateAction) else create_github_pr(workspace, **options)
    common = dict(
        ok=bool(result["ok"]), repository=str(result["repository"]), remote=str(result["remote"]),
        head=str(result["head"]), base=str(result["base"]), title=str(result["title"]),
        draft=bool(result["draft"]), ahead=int(result["ahead"]), behind=int(result["behind"]),
        commits=int(result["commits"]), message=str(result["message"]),
    )
    if isinstance(action, CheckGitHubPrCreateAction):
        return CheckGitHubPrCreateObservation(kind="check_github_pr_create", **common)
    return GitHubPrCreateObservation(kind="github_pr_create", url=str(result.get("url", "")), **common)
