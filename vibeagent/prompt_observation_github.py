from __future__ import annotations

from .prompt_observation_utils import truncate


def format_github_observation(index: int, observation: object) -> str | None:
    if observation.kind in {"check_github_pr_create", "github_pr_create"}:
        url = f"\nurl: {observation.url}" if observation.kind == "github_pr_create" and observation.url else ""
        return "\n".join(
            [
                f"{index}. {observation.kind}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"repository: {observation.repository or 'none'}",
                f"headBase: {observation.head or 'none'} -> {observation.base or 'none'}",
                f"title: {observation.title}",
                f"draft: {str(observation.draft).lower()}",
                f"aheadBehind: {observation.ahead}/{observation.behind}",
                f"commits: {observation.commits}{url}",
            ]
        )
    if observation.kind != "github_pr_context":
        return None
    parts = [
        f"{index}. github_pr_context: {observation.message}",
        f"ok: {str(observation.ok).lower()}",
        f"repository: {observation.repository or 'none'}",
    ]
    if not observation.ok:
        return "\n".join(parts)
    parts.extend(
        [
            f"pr: #{observation.number} {observation.url}",
            f"title: {observation.title}",
            f"authorState: {observation.author or 'unknown'} {observation.state or 'unknown'} draft={str(observation.is_draft).lower()}",
            f"headBase: {observation.head} -> {observation.base}",
            f"changes: +{observation.additions}/-{observation.deletions} files={observation.changed_files}",
            f"merge: mergeable={observation.mergeable or 'unknown'} state={observation.merge_state or 'unknown'} review={observation.review_decision or 'none'}",
            f"body:\n{truncate(observation.body, 4_000)}",
            f"comments: {len(observation.comments)}/{observation.comments_total} truncated={str(observation.comments_truncated).lower()}",
        ]
    )
    for comment in observation.comments[:30]:
        location = f" {comment.path}:{comment.line or '?'}" if comment.path else ""
        parts.append(
            f"comment[{comment.kind}]{location} by {comment.author or 'unknown'} at {comment.created_at}:\n"
            f"{truncate(comment.body, 1_000)}"
        )
    parts.append(
        f"reviews: {len(observation.reviews)}/{observation.reviews_total} truncated={str(observation.reviews_truncated).lower()}"
    )
    for review in observation.reviews[:20]:
        parts.append(
            f"review[{review.state or 'unknown'}] by {review.author or 'unknown'} at {review.submitted_at}:\n"
            f"{truncate(review.body, 1_000)}"
        )
    parts.append(
        f"checks: {len(observation.checks)}/{observation.checks_total} truncated={str(observation.checks_truncated).lower()}"
    )
    for check in observation.checks[:50]:
        parts.append(
            f"check[{check.bucket}] {check.name or 'unnamed'} state={check.state or 'unknown'} workflow={check.workflow or 'none'}"
        )
    parts.append(f"files: {len(observation.files)}/{observation.files_total} truncated={str(observation.files_truncated).lower()}")
    for file in observation.files[:50]:
        parts.append(f"file: {file.path} +{file.additions}/-{file.deletions}")
    return "\n".join(parts)


__all__ = ["format_github_observation"]
