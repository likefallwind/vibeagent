from __future__ import annotations

from .prompt_observation_utils import truncate


def format_git_fetch_observation(index: int, observation: object) -> str:
    if observation.kind == "check_git_fetch":
        return "\n".join(
            [
                f"{index}. check_git_fetch {observation.remote or 'default remote'}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"remoteUrl: {observation.remote_url or 'none'}",
                f"branch: {observation.branch or 'detached'}",
                f"upstream: {observation.upstream or 'none'}",
                f"aheadBehind: {observation.ahead}/{observation.behind}",
            ]
        )
    return "\n".join(
        [
            f"{index}. git_fetch {observation.remote or 'default remote'}: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
            f"remoteUrl: {observation.remote_url or 'none'}",
            f"branch: {observation.branch or 'detached'}",
            f"upstream: {observation.upstream or 'none'}",
            (
                "aheadBehind: "
                f"{observation.ahead_before}/{observation.behind_before}"
                f" -> {observation.ahead_after}/{observation.behind_after}"
            ),
        ]
    )


def format_git_sync_observation(index: int, observation: object) -> str:
    if observation.kind == "check_git_pull":
        return "\n".join(
            [
                f"{index}. check_git_pull {observation.upstream or 'no upstream'}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"remoteBranch: {observation.remote or 'none'}/{observation.branch or 'none'}",
                f"current: {observation.current or 'detached'}",
                f"aheadBehind: {observation.ahead}/{observation.behind}",
                f"worktreeClean: {str(observation.worktree_clean).lower()}",
                f"status:\n{truncate(observation.status)}",
            ]
        )
    if observation.kind == "git_pull":
        return "\n".join(
            [
                f"{index}. git_pull {observation.upstream or 'no upstream'}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"remoteBranch: {observation.remote or 'none'}/{observation.branch or 'none'}",
                f"current: {observation.current_before or 'detached'} -> {observation.current_after or 'detached'}",
                (
                    "aheadBehind: "
                    f"{observation.ahead_before}/{observation.behind_before}"
                    f" -> {observation.ahead_after}/{observation.behind_after}"
                ),
                f"status:\n{truncate(observation.status)}",
            ]
        )
    if observation.kind == "check_git_push":
        return "\n".join(
            [
                f"{index}. check_git_push {observation.upstream or 'no upstream'}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"remoteBranch: {observation.remote or 'none'}/{observation.branch or 'none'}",
                f"current: {observation.current or 'detached'}",
                f"aheadBehind: {observation.ahead}/{observation.behind}",
                f"worktreeClean: {str(observation.worktree_clean).lower()}",
                f"status:\n{truncate(observation.status)}",
            ]
        )
    return "\n".join(
        [
            f"{index}. git_push {observation.upstream or 'no upstream'}: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
            f"remoteBranch: {observation.remote or 'none'}/{observation.branch or 'none'}",
            f"current: {observation.current or 'detached'}",
            f"aheadBehindBefore: {observation.ahead_before}/{observation.behind_before}",
            f"status:\n{truncate(observation.status)}",
        ]
    )


def format_git_switch_observation(index: int, observation: object) -> str:
    if observation.kind == "check_git_switch":
        return "\n".join(
            [
                f"{index}. check_git_switch {observation.branch}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"create: {str(observation.create).lower()}",
                f"currentBefore: {observation.current_before or 'detached'}",
                f"branchExists: {str(observation.branch_exists).lower()}",
                f"worktreeClean: {str(observation.worktree_clean).lower()}",
                f"status:\n{truncate(observation.status)}",
            ]
        )
    return "\n".join(
        [
            f"{index}. git_switch {observation.branch}: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
            f"create: {str(observation.create).lower()}",
            f"currentBefore: {observation.current_before or 'detached'}",
            f"currentAfter: {observation.current_after or 'detached'}",
            f"status:\n{truncate(observation.status)}",
        ]
    )


__all__ = [
    "format_git_fetch_observation",
    "format_git_switch_observation",
    "format_git_sync_observation",
]
