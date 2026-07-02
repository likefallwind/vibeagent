from __future__ import annotations

from pathlib import Path
import shlex

from .actions import execute_action
from .types import CheckGitFetchAction, CheckGitPullAction, CheckGitPushAction, GitFetchAction, GitPullAction, GitPushAction
from .workspace_core import RunWorkspace


def _indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def get_check_fetch_report(project_root: str | Path = ".", argument: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        remote = parse_optional_remote_argument(argument)
    except ValueError as error:
        return _git_fetch_usage_report(root, "/check-fetch [remote]", str(error))
    workspace = RunWorkspace(root=root, run_id="local-check-fetch", session_dir=root / ".vibeagent" / "sessions" / "local-check-fetch")
    observation = execute_action(workspace, CheckGitFetchAction(type="check_git_fetch", remote=remote))
    if observation.kind != "check_git_fetch":
        return _git_fetch_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "remote": observation.remote,
        "remoteUrl": observation.remote_url,
        "branch": observation.branch,
        "upstream": observation.upstream,
        "ahead": observation.ahead,
        "behind": observation.behind,
        "message": observation.message,
    }


def get_fetch_report(project_root: str | Path = ".", argument: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        remote = parse_optional_remote_argument(argument)
    except ValueError as error:
        return _git_fetch_usage_report(root, "/fetch [remote]", str(error))
    workspace = RunWorkspace(root=root, run_id="local-fetch", session_dir=root / ".vibeagent" / "sessions" / "local-fetch")
    observation = execute_action(workspace, GitFetchAction(type="git_fetch", remote=remote))
    if observation.kind != "git_fetch":
        return _git_fetch_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "remote": observation.remote,
        "remoteUrl": observation.remote_url,
        "branch": observation.branch,
        "upstream": observation.upstream,
        "aheadBefore": observation.ahead_before,
        "behindBefore": observation.behind_before,
        "aheadAfter": observation.ahead_after,
        "behindAfter": observation.behind_after,
        "message": observation.message,
    }


def get_check_pull_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-check-pull", session_dir=root / ".vibeagent" / "sessions" / "local-check-pull")
    observation = execute_action(workspace, CheckGitPullAction(type="check_git_pull"))
    if observation.kind != "check_git_pull":
        return _git_sync_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return _git_sync_preview_observation_report(root, observation)


def get_pull_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-pull", session_dir=root / ".vibeagent" / "sessions" / "local-pull")
    observation = execute_action(workspace, GitPullAction(type="git_pull"))
    if observation.kind != "git_pull":
        return _git_sync_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "remote": observation.remote,
        "branch": observation.branch,
        "currentBefore": observation.current_before,
        "currentAfter": observation.current_after,
        "upstream": observation.upstream,
        "aheadBefore": observation.ahead_before,
        "behindBefore": observation.behind_before,
        "aheadAfter": observation.ahead_after,
        "behindAfter": observation.behind_after,
        "statusText": observation.status,
        "message": observation.message,
    }


def get_check_push_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-check-push", session_dir=root / ".vibeagent" / "sessions" / "local-check-push")
    observation = execute_action(workspace, CheckGitPushAction(type="check_git_push"))
    if observation.kind != "check_git_push":
        return _git_sync_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return _git_sync_preview_observation_report(root, observation)


def get_push_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-push", session_dir=root / ".vibeagent" / "sessions" / "local-push")
    observation = execute_action(workspace, GitPushAction(type="git_push"))
    if observation.kind != "git_push":
        return _git_sync_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "remote": observation.remote,
        "branch": observation.branch,
        "current": observation.current,
        "upstream": observation.upstream,
        "aheadBefore": observation.ahead_before,
        "behindBefore": observation.behind_before,
        "statusText": observation.status,
        "message": observation.message,
    }


def parse_optional_remote_argument(argument: str | None) -> str | None:
    if not argument or not argument.strip():
        return None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 1:
        raise ValueError("expected at most one remote name.")
    remote = parts[0].strip()
    if not remote:
        raise ValueError("remote name must be non-empty.")
    return remote


def format_git_fetch_preview_text(
    title: str,
    root: Path,
    ok: bool,
    remote: str,
    remote_url: str,
    branch: str,
    upstream: str,
    ahead: int,
    behind: int,
    message: str,
) -> str:
    return "\n".join(
        [
            f"{title}:",
            f"  projectRoot: {root}",
            f"  ok: {'yes' if ok else 'no'}",
            f"  remote: {remote or '.'}",
            f"  remoteUrl: {remote_url or '.'}",
            f"  branch: {branch or '.'}",
            f"  upstream: {upstream or '.'}",
            f"  ahead: {ahead}",
            f"  behind: {behind}",
            f"  message: {message}",
        ]
    )


def _git_fetch_usage_report(root: Path, usage: str, error: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "remote": "",
        "remoteUrl": "",
        "branch": "",
        "upstream": "",
        "ahead": 0,
        "behind": 0,
        "message": f"Usage: {usage}\nError: {error}",
    }


def _git_fetch_unexpected_report(root: Path, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "remote": "",
        "remoteUrl": "",
        "branch": "",
        "upstream": "",
        "message": message,
    }


def format_git_fetch_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  remote: {report.get('remote') or '.'}",
        f"  remoteUrl: {report.get('remoteUrl') or '.'}",
        f"  branch: {report.get('branch') or '.'}",
        f"  upstream: {report.get('upstream') or '.'}",
    ]
    if "aheadBefore" in report or "behindBefore" in report:
        lines.extend(
            [
                f"  aheadBefore: {report.get('aheadBefore', 0)}",
                f"  behindBefore: {report.get('behindBefore', 0)}",
                f"  aheadAfter: {report.get('aheadAfter', 0)}",
                f"  behindAfter: {report.get('behindAfter', 0)}",
            ]
        )
    else:
        lines.extend(
            [
                f"  ahead: {report.get('ahead', 0)}",
                f"  behind: {report.get('behind', 0)}",
            ]
        )
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_git_fetch_text(
    title: str,
    root: Path,
    ok: bool,
    remote: str,
    remote_url: str,
    branch: str,
    upstream: str,
    ahead_before: int,
    behind_before: int,
    ahead_after: int,
    behind_after: int,
    message: str,
) -> str:
    return "\n".join(
        [
            f"{title}:",
            f"  projectRoot: {root}",
            f"  ok: {'yes' if ok else 'no'}",
            f"  remote: {remote or '.'}",
            f"  remoteUrl: {remote_url or '.'}",
            f"  branch: {branch or '.'}",
            f"  upstream: {upstream or '.'}",
            f"  aheadBefore: {ahead_before}",
            f"  behindBefore: {behind_before}",
            f"  aheadAfter: {ahead_after}",
            f"  behindAfter: {behind_after}",
            f"  message: {message}",
        ]
    )


def format_git_pull_push_preview_text(
    title: str,
    root: Path,
    ok: bool,
    remote: str,
    branch: str,
    current: str,
    upstream: str,
    ahead: int,
    behind: int,
    worktree_clean: bool,
    status: str,
    message: str,
) -> str:
    lines = [
        f"{title}:",
        f"  projectRoot: {root}",
        f"  ok: {'yes' if ok else 'no'}",
        f"  remote: {remote or '.'}",
        f"  branch: {branch or '.'}",
        f"  current: {current or '.'}",
        f"  upstream: {upstream or '.'}",
        f"  ahead: {ahead}",
        f"  behind: {behind}",
        f"  worktreeClean: {'yes' if worktree_clean else 'no'}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def _git_sync_unexpected_report(root: Path, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "remote": "",
        "branch": "",
        "current": "",
        "upstream": "",
        "ahead": 0,
        "behind": 0,
        "worktreeClean": False,
        "statusText": "",
        "message": message,
    }


def _git_sync_preview_observation_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "remote": str(getattr(observation, "remote")),
        "branch": str(getattr(observation, "branch")),
        "current": str(getattr(observation, "current")),
        "upstream": str(getattr(observation, "upstream")),
        "ahead": int(getattr(observation, "ahead")),
        "behind": int(getattr(observation, "behind")),
        "worktreeClean": bool(getattr(observation, "worktree_clean")),
        "statusText": str(getattr(observation, "status")),
        "message": str(getattr(observation, "message")),
    }


def format_git_sync_preview_report_text(title: str, report: dict[str, object]) -> str:
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  remote: {report.get('remote') or '.'}",
        f"  branch: {report.get('branch') or '.'}",
        f"  current: {report.get('current') or '.'}",
        f"  upstream: {report.get('upstream') or '.'}",
        f"  ahead: {report.get('ahead', 0)}",
        f"  behind: {report.get('behind', 0)}",
        f"  worktreeClean: {'yes' if bool(report.get('worktreeClean')) else 'no'}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def format_git_pull_text(
    title: str,
    root: Path,
    ok: bool,
    remote: str,
    branch: str,
    current_before: str,
    current_after: str,
    upstream: str,
    ahead_before: int,
    behind_before: int,
    ahead_after: int,
    behind_after: int,
    status: str,
    message: str,
) -> str:
    lines = [
        f"{title}:",
        f"  projectRoot: {root}",
        f"  ok: {'yes' if ok else 'no'}",
        f"  remote: {remote or '.'}",
        f"  branch: {branch or '.'}",
        f"  currentBefore: {current_before or '.'}",
        f"  currentAfter: {current_after or '.'}",
        f"  upstream: {upstream or '.'}",
        f"  aheadBefore: {ahead_before}",
        f"  behindBefore: {behind_before}",
        f"  aheadAfter: {ahead_after}",
        f"  behindAfter: {behind_after}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_git_pull_report_text(title: str, report: dict[str, object]) -> str:
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  remote: {report.get('remote') or '.'}",
        f"  branch: {report.get('branch') or '.'}",
        f"  currentBefore: {report.get('currentBefore') or '.'}",
        f"  currentAfter: {report.get('currentAfter') or '.'}",
        f"  upstream: {report.get('upstream') or '.'}",
        f"  aheadBefore: {report.get('aheadBefore', 0)}",
        f"  behindBefore: {report.get('behindBefore', 0)}",
        f"  aheadAfter: {report.get('aheadAfter', 0)}",
        f"  behindAfter: {report.get('behindAfter', 0)}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def format_git_push_text(
    title: str,
    root: Path,
    ok: bool,
    remote: str,
    branch: str,
    current: str,
    upstream: str,
    ahead_before: int,
    behind_before: int,
    status: str,
    message: str,
) -> str:
    lines = [
        f"{title}:",
        f"  projectRoot: {root}",
        f"  ok: {'yes' if ok else 'no'}",
        f"  remote: {remote or '.'}",
        f"  branch: {branch or '.'}",
        f"  current: {current or '.'}",
        f"  upstream: {upstream or '.'}",
        f"  aheadBefore: {ahead_before}",
        f"  behindBefore: {behind_before}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_git_push_report_text(title: str, report: dict[str, object]) -> str:
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  remote: {report.get('remote') or '.'}",
        f"  branch: {report.get('branch') or '.'}",
        f"  current: {report.get('current') or '.'}",
        f"  upstream: {report.get('upstream') or '.'}",
        f"  aheadBefore: {report.get('aheadBefore', 0)}",
        f"  behindBefore: {report.get('behindBefore', 0)}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)
