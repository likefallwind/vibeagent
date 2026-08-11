from __future__ import annotations

from .github_issue_comment_runtime import (
    create_github_issue_comment,
    preview_github_issue_comment,
)
from .github_issue_context_runtime import read_github_issue_context
from .types import (
    CheckGitHubIssueCommentAction,
    CheckGitHubIssueCommentObservation,
    GitHubIssueComment,
    GitHubIssueCommentAction,
    GitHubIssueCommentObservation,
    GitHubIssueContextAction,
    GitHubIssueContextObservation,
    Observation,
)
from .workspace import RunWorkspace


def execute_github_issue_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, GitHubIssueContextAction):
        result = read_github_issue_context(
            workspace,
            issue=action.issue,
            remote=action.remote,
        )
        return GitHubIssueContextObservation(
            kind="github_issue_context",
            ok=bool(result["ok"]),
            repository=str(result["repository"]),
            number=int(result["number"]),
            url=str(result["url"]),
            title=str(result["title"]),
            body=str(result["body"]),
            author=str(result["author"]),
            state=str(result["state"]),
            state_reason=str(result["state_reason"]),
            created_at=str(result["created_at"]),
            updated_at=str(result["updated_at"]),
            milestone=str(result["milestone"]),
            labels=[str(item) for item in result["labels"]],
            labels_total=int(result["labels_total"]),
            labels_truncated=bool(result["labels_truncated"]),
            assignees=[str(item) for item in result["assignees"]],
            assignees_total=int(result["assignees_total"]),
            assignees_truncated=bool(result["assignees_truncated"]),
            comments=[GitHubIssueComment(**item) for item in result["comments"]],
            comments_total=int(result["comments_total"]),
            comments_truncated=bool(result["comments_truncated"]),
            message=str(result["message"]),
        )
    if not isinstance(action, (CheckGitHubIssueCommentAction, GitHubIssueCommentAction)):
        return None
    options = {
        "body": action.body,
        "issue": action.issue,
        "remote": action.remote,
    }
    result = (
        preview_github_issue_comment(workspace, **options)
        if isinstance(action, CheckGitHubIssueCommentAction)
        else create_github_issue_comment(workspace, **options)
    )
    common = dict(
        ok=bool(result["ok"]),
        repository=str(result["repository"]),
        selector=str(result["selector"]),
        issue=str(result["issue"]),
        remote=result["remote"],
        body_chars=int(result["body_chars"]),
        body_sha256=str(result["body_sha256"]),
        comment_target=str(result["comment_target"]),
        message=str(result["message"]),
    )
    if isinstance(action, CheckGitHubIssueCommentAction):
        return CheckGitHubIssueCommentObservation(kind="check_github_issue_comment", **common)
    return GitHubIssueCommentObservation(
        kind="github_issue_comment",
        url=str(result.get("url", "")),
        **common,
    )


__all__ = ["execute_github_issue_action"]
