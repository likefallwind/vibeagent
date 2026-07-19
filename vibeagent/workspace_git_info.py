from __future__ import annotations


def git_not_repo_info(message: str) -> dict[str, object]:
    return {
        "ok": False,
        "is_git_repo": False,
        "branch": "",
        "head": "",
        "upstream": "",
        "ahead": 0,
        "behind": 0,
        "remotes": [],
        "status": "",
        "message": message,
    }


def parse_ahead_behind_counts(output: str) -> tuple[int, int]:
    parts = output.strip().split()
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        return int(parts[0]), int(parts[1])
    return 0, 0


def git_info_payload(
    *,
    branch: str,
    head: str,
    upstream: str,
    ahead: int,
    behind: int,
    remotes: list[dict[str, str]],
    status: str,
) -> dict[str, object]:
    message = f"Git repository on {branch or 'detached HEAD'} at {head or 'unknown'}."
    if upstream:
        message += f" Upstream {upstream}, ahead {ahead}, behind {behind}."
    else:
        message += " No upstream configured."
    return {
        "ok": True,
        "is_git_repo": True,
        "branch": branch,
        "head": head,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "remotes": remotes,
        "status": status,
        "message": message,
    }
