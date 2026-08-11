from __future__ import annotations

from .github_pr_context_runtime import read_github_pr_context
from .github_pr_ci_runtime import read_github_pr_ci_logs
from .github_pr_runtime import create_github_pr, preview_github_pr_create
from .types import (
    CheckGitHubPrCreateAction,
    CheckGitHubPrCreateObservation,
    GitHubPrCheck,
    GitHubPrCiLogsAction,
    GitHubPrCiLogsObservation,
    GitHubPrCiRun,
    GitHubPrComment,
    GitHubPrContextAction,
    GitHubPrContextObservation,
    GitHubPrCreateAction,
    GitHubPrCreateObservation,
    GitHubPrFailedCheck,
    GitHubPrFile,
    GitHubPrReview,
    Observation,
)
from .workspace import RunWorkspace


def execute_github_pr_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, GitHubPrCiLogsAction):
        result = read_github_pr_ci_logs(
            workspace,
            pr=action.pr,
            remote=action.remote,
            max_runs=action.max_runs,
            max_output_chars=action.max_output_chars,
        )
        return GitHubPrCiLogsObservation(
            kind="github_pr_ci_logs",
            ok=bool(result["ok"]),
            repository=str(result["repository"]),
            selector=str(result["selector"]),
            failed_checks=[GitHubPrFailedCheck(**item) for item in result["failed_checks"]],
            failed_total=int(result["failed_total"]),
            failed_truncated=bool(result["failed_truncated"]),
            runs=[GitHubPrCiRun(**item) for item in result["runs"]],
            runs_total=int(result["runs_total"]),
            runs_truncated=bool(result["runs_truncated"]),
            message=str(result["message"]),
        )
    if isinstance(action, GitHubPrContextAction):
        result = read_github_pr_context(workspace, pr=action.pr, remote=action.remote)
        return GitHubPrContextObservation(
            kind="github_pr_context",
            ok=bool(result["ok"]),
            repository=str(result["repository"]),
            number=int(result["number"]),
            url=str(result["url"]),
            title=str(result["title"]),
            body=str(result["body"]),
            author=str(result["author"]),
            state=str(result["state"]),
            is_draft=bool(result["is_draft"]),
            head=str(result["head"]),
            base=str(result["base"]),
            additions=int(result["additions"]),
            deletions=int(result["deletions"]),
            changed_files=int(result["changed_files"]),
            mergeable=str(result["mergeable"]),
            merge_state=str(result["merge_state"]),
            review_decision=str(result["review_decision"]),
            comments=[GitHubPrComment(**item) for item in result["comments"]],
            comments_total=int(result["comments_total"]),
            comments_truncated=bool(result["comments_truncated"]),
            reviews=[GitHubPrReview(**item) for item in result["reviews"]],
            reviews_total=int(result["reviews_total"]),
            reviews_truncated=bool(result["reviews_truncated"]),
            checks=[GitHubPrCheck(**item) for item in result["checks"]],
            checks_total=int(result["checks_total"]),
            checks_truncated=bool(result["checks_truncated"]),
            files=[GitHubPrFile(**item) for item in result["files"]],
            files_total=int(result["files_total"]),
            files_truncated=bool(result["files_truncated"]),
            message=str(result["message"]),
        )
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
