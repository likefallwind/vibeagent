from __future__ import annotations

from pathlib import Path
import shlex

from .actions import execute_action
from .command_parsing import parse_local_path_args
from .types import CheckGitCommitAction, CheckGitFetchAction, CheckGitPullAction, CheckGitPushAction, CheckGitRestoreAction, CheckGitStageAction, CheckGitSwitchAction, CheckGitUnstageAction, GitCommitAction, GitFetchAction, GitPullAction, GitPushAction, GitRestoreAction, GitStageAction, GitSwitchAction, GitUnstageAction
from .workspace_core import RunWorkspace


from .git_stash_commands import (
    format_git_stash_apply_report_text,
    format_git_stash_apply_text,
    format_git_stash_drop_report_text,
    format_git_stash_drop_text,
    format_git_stash_report_text,
    format_git_stash_text,
    format_stashes_report_text,
    get_check_stash_apply_report,
    get_check_stash_apply_text,
    get_check_stash_drop_report,
    get_check_stash_drop_text,
    get_check_stash_report,
    get_check_stash_text,
    get_stash_apply_report,
    get_stash_apply_text,
    get_stash_drop_report,
    get_stash_drop_text,
    get_stash_report,
    get_stash_text,
    get_stashes_report,
    get_stashes_text,
    parse_stash_argument,
    parse_stashes_request,
)
from .git_read_commands import (
    _git_output_payload,
    _git_status_payload,
    _indent_block,
    clip_with_flag,
    format_blame_report_text,
    format_branches_report_text,
    format_git_conflicts_report_text,
    format_git_info_report_text,
    format_git_status_report_text,
    format_log_report_text,
    get_blame_report,
    get_blame_text,
    get_branches_report,
    get_branches_text,
    get_git_conflicts_report,
    get_git_conflicts_text,
    get_git_info_report,
    get_git_info_text,
    get_git_status_report,
    get_git_status_text,
    get_log_report,
    get_log_text,
    get_show_report,
    get_show_text,
    format_show_report_text,
    parse_log_request,
    parse_show_request,
)
from .git_sync_commands import (
    format_git_fetch_preview_text,
    format_git_fetch_report_text,
    format_git_fetch_text,
    format_git_pull_push_preview_text,
    format_git_pull_report_text,
    format_git_pull_text,
    format_git_push_report_text,
    format_git_push_text,
    format_git_sync_preview_report_text,
    get_check_fetch_report,
    get_check_pull_report,
    get_check_push_report,
    get_fetch_report,
    get_pull_report,
    get_push_report,
    parse_optional_remote_argument,
)


def get_check_fetch_text(project_root: str | Path = ".", argument: str | None = None) -> str:
    return format_git_fetch_report_text("Check fetch", get_check_fetch_report(project_root, argument))


def get_fetch_text(project_root: str | Path = ".", argument: str | None = None) -> str:
    return format_git_fetch_report_text("Fetch", get_fetch_report(project_root, argument))


def get_check_pull_text(project_root: str | Path = ".") -> str:
    return format_git_sync_preview_report_text("Check pull", get_check_pull_report(project_root))


def get_pull_text(project_root: str | Path = ".") -> str:
    return format_git_pull_report_text("Pull", get_pull_report(project_root))


def get_check_push_text(project_root: str | Path = ".") -> str:
    return format_git_sync_preview_report_text("Check push", get_check_push_report(project_root))


def get_push_text(project_root: str | Path = ".") -> str:
    return format_git_push_report_text("Push", get_push_report(project_root))


def get_check_stage_text(project_root: str | Path = ".", argument: str | list[str] | None = None) -> str:
    report = get_check_stage_report(project_root, argument)
    return format_git_index_report_text("Check stage", report)


def get_check_stage_report(project_root: str | Path = ".", argument: str | list[str] | None = None) -> dict[str, object]:
    usage = "/check-stage <path...>"
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=100)
    except ValueError as error:
        return _git_index_usage_report(root, usage, str(error))
    if not paths:
        return _git_index_usage_report(root, usage, "path is required.")

    workspace = RunWorkspace(root=root, run_id="local-check-stage", session_dir=root / ".vibeagent" / "sessions" / "local-check-stage")
    observation = execute_action(
        workspace,
        CheckGitStageAction(type="check_git_stage", paths=paths),
    )
    if observation.kind != "check_git_stage":
        return _git_index_unexpected_report(root, paths, f"Unexpected observation: {observation.kind}")
    return _git_index_observation_report(root, observation)


def get_stage_text(project_root: str | Path = ".", argument: str | list[str] | None = None) -> str:
    report = get_stage_report(project_root, argument)
    return format_git_index_report_text("Stage", report)


def get_stage_report(project_root: str | Path = ".", argument: str | list[str] | None = None) -> dict[str, object]:
    usage = "/stage <path...>"
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=100)
    except ValueError as error:
        return _git_index_usage_report(root, usage, str(error))
    if not paths:
        return _git_index_usage_report(root, usage, "path is required.")

    workspace = RunWorkspace(root=root, run_id="local-stage", session_dir=root / ".vibeagent" / "sessions" / "local-stage")
    observation = execute_action(
        workspace,
        GitStageAction(type="git_stage", paths=paths),
    )
    if observation.kind != "git_stage":
        return _git_index_unexpected_report(root, paths, f"Unexpected observation: {observation.kind}")
    return _git_index_observation_report(root, observation)


def get_check_unstage_text(project_root: str | Path = ".", argument: str | list[str] | None = None) -> str:
    report = get_check_unstage_report(project_root, argument)
    return format_git_index_report_text("Check unstage", report)


def get_check_unstage_report(project_root: str | Path = ".", argument: str | list[str] | None = None) -> dict[str, object]:
    usage = "/check-unstage <path...>"
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=100)
    except ValueError as error:
        return _git_index_usage_report(root, usage, str(error))
    if not paths:
        return _git_index_usage_report(root, usage, "path is required.")

    workspace = RunWorkspace(root=root, run_id="local-check-unstage", session_dir=root / ".vibeagent" / "sessions" / "local-check-unstage")
    observation = execute_action(
        workspace,
        CheckGitUnstageAction(type="check_git_unstage", paths=paths),
    )
    if observation.kind != "check_git_unstage":
        return _git_index_unexpected_report(root, paths, f"Unexpected observation: {observation.kind}")
    return _git_index_observation_report(root, observation)


def get_unstage_text(project_root: str | Path = ".", argument: str | list[str] | None = None) -> str:
    report = get_unstage_report(project_root, argument)
    return format_git_index_report_text("Unstage", report)


def get_unstage_report(project_root: str | Path = ".", argument: str | list[str] | None = None) -> dict[str, object]:
    usage = "/unstage <path...>"
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=100)
    except ValueError as error:
        return _git_index_usage_report(root, usage, str(error))
    if not paths:
        return _git_index_usage_report(root, usage, "path is required.")

    workspace = RunWorkspace(root=root, run_id="local-unstage", session_dir=root / ".vibeagent" / "sessions" / "local-unstage")
    observation = execute_action(
        workspace,
        GitUnstageAction(type="git_unstage", paths=paths),
    )
    if observation.kind != "git_unstage":
        return _git_index_unexpected_report(root, paths, f"Unexpected observation: {observation.kind}")
    return _git_index_observation_report(root, observation)


def get_check_commit_text(project_root: str | Path = ".", argument: str | None = None) -> str:
    report = get_check_commit_report(project_root, argument)
    return format_git_commit_report_text("Check commit", report)


def get_check_commit_report(project_root: str | Path = ".", argument: str | None = None) -> dict[str, object]:
    message = (argument or "").strip()
    root = Path(project_root).resolve()
    if not message:
        return _git_commit_usage_report(root, "/check-commit <message>", "message is required.")

    workspace = RunWorkspace(root=root, run_id="local-check-commit", session_dir=root / ".vibeagent" / "sessions" / "local-check-commit")
    observation = execute_action(
        workspace,
        CheckGitCommitAction(type="check_git_commit", message=message),
    )
    if observation.kind != "check_git_commit":
        return _git_commit_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return _git_commit_observation_report(root, observation)


def get_commit_text(project_root: str | Path = ".", argument: str | None = None) -> str:
    report = get_commit_report(project_root, argument)
    return format_git_commit_report_text("Commit", report)


def get_commit_report(project_root: str | Path = ".", argument: str | None = None) -> dict[str, object]:
    message = (argument or "").strip()
    root = Path(project_root).resolve()
    if not message:
        return _git_commit_usage_report(root, "/commit <message>", "message is required.")

    workspace = RunWorkspace(root=root, run_id="local-commit", session_dir=root / ".vibeagent" / "sessions" / "local-commit")
    observation = execute_action(
        workspace,
        GitCommitAction(type="git_commit", message=message),
    )
    if observation.kind != "git_commit":
        return _git_commit_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return _git_commit_observation_report(root, observation)


def get_check_restore_text(project_root: str | Path = ".", argument: str | list[str] | None = None, max_diff_chars: int = 12_000) -> str:
    report = get_check_restore_report(project_root, argument, max_diff_chars=max_diff_chars)
    return format_git_restore_report_text("Check restore", report)


def get_check_restore_report(project_root: str | Path = ".", argument: str | list[str] | None = None, max_diff_chars: int = 12_000) -> dict[str, object]:
    _validate_git_restore_max_diff_chars(max_diff_chars)
    usage = "/check-restore <path...>"
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=100)
    except ValueError as error:
        return _git_restore_usage_report(root, usage, str(error), max_diff_chars)
    if not paths:
        return _git_restore_usage_report(root, usage, "path is required.", max_diff_chars)

    workspace = RunWorkspace(root=root, run_id="local-check-restore", session_dir=root / ".vibeagent" / "sessions" / "local-check-restore")
    observation = execute_action(
        workspace,
        CheckGitRestoreAction(type="check_git_restore", paths=paths),
    )
    if observation.kind != "check_git_restore":
        return _git_restore_unexpected_report(root, paths, f"Unexpected observation: {observation.kind}", max_diff_chars)
    return _git_restore_observation_report(root, observation, max_diff_chars)


def get_restore_text(project_root: str | Path = ".", argument: str | list[str] | None = None, max_diff_chars: int = 12_000) -> str:
    report = get_restore_report(project_root, argument, max_diff_chars=max_diff_chars)
    return format_git_restore_report_text("Restore", report)


def get_restore_report(project_root: str | Path = ".", argument: str | list[str] | None = None, max_diff_chars: int = 12_000) -> dict[str, object]:
    _validate_git_restore_max_diff_chars(max_diff_chars)
    usage = "/restore <path...>"
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=100)
    except ValueError as error:
        return _git_restore_usage_report(root, usage, str(error), max_diff_chars)
    if not paths:
        return _git_restore_usage_report(root, usage, "path is required.", max_diff_chars)

    workspace = RunWorkspace(root=root, run_id="local-restore", session_dir=root / ".vibeagent" / "sessions" / "local-restore")
    observation = execute_action(
        workspace,
        GitRestoreAction(type="git_restore", paths=paths),
    )
    if observation.kind != "git_restore":
        return _git_restore_unexpected_report(root, paths, f"Unexpected observation: {observation.kind}", max_diff_chars)
    return _git_restore_observation_report(root, observation, max_diff_chars)


def get_check_switch_text(project_root: str | Path = ".", argument: str | None = None) -> str:
    return format_git_switch_report_text("Check switch", get_check_switch_report(project_root, argument))


def get_switch_text(project_root: str | Path = ".", argument: str | None = None) -> str:
    return format_git_switch_report_text("Switch", get_switch_report(project_root, argument))


def get_check_switch_report(project_root: str | Path = ".", argument: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        branch, create = parse_switch_argument(argument)
    except ValueError as error:
        return _git_switch_usage_report(root, "/check-switch [--create] <branch>", str(error))
    workspace = RunWorkspace(root=root, run_id="local-check-switch", session_dir=root / ".vibeagent" / "sessions" / "local-check-switch")
    observation = execute_action(
        workspace,
        CheckGitSwitchAction(type="check_git_switch", branch=branch, create=create),
    )
    if observation.kind != "check_git_switch":
        return _git_switch_unexpected_report(root, branch, create, f"Unexpected observation: {observation.kind}")
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "branch": observation.branch,
        "create": observation.create,
        "currentBefore": observation.current_before,
        "branchExists": observation.branch_exists,
        "worktreeClean": observation.worktree_clean,
        "statusText": observation.status,
        "message": observation.message,
    }


def get_switch_report(project_root: str | Path = ".", argument: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        branch, create = parse_switch_argument(argument)
    except ValueError as error:
        return _git_switch_usage_report(root, "/switch [--create] <branch>", str(error))
    workspace = RunWorkspace(root=root, run_id="local-switch", session_dir=root / ".vibeagent" / "sessions" / "local-switch")
    observation = execute_action(
        workspace,
        GitSwitchAction(type="git_switch", branch=branch, create=create),
    )
    if observation.kind != "git_switch":
        return _git_switch_unexpected_report(root, branch, create, f"Unexpected observation: {observation.kind}")
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "branch": observation.branch,
        "create": observation.create,
        "currentBefore": observation.current_before,
        "currentAfter": observation.current_after,
        "statusText": observation.status,
        "message": observation.message,
    }


def parse_switch_argument(argument: str | None) -> tuple[str, bool]:
    if not argument or not argument.strip():
        raise ValueError("branch is required.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    create = False
    branches: list[str] = []
    for part in parts:
        if part in {"--create", "-c"}:
            create = True
        elif part.startswith("-"):
            raise ValueError(f"unsupported option: {part}")
        else:
            branches.append(part)
    if not branches:
        raise ValueError("branch is required.")
    if len(branches) > 1:
        raise ValueError("only one branch is allowed.")
    return branches[0], create


def _git_index_usage_report(root: Path, usage: str, error: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "paths": {"shown": 0, "items": []},
        "statusText": "",
        "message": f"Usage: {usage}\nError: {error}",
    }


def _git_index_unexpected_report(root: Path, paths: list[str], message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "paths": {"shown": len(paths), "items": list(paths)},
        "statusText": "",
        "message": message,
    }


def _git_index_observation_report(root: Path, observation: object) -> dict[str, object]:
    paths = list(getattr(observation, "paths"))
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "paths": {"shown": len(paths), "items": paths},
        "statusText": str(getattr(observation, "status")),
        "message": str(getattr(observation, "message")),
    }


def format_git_index_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    paths = report.get("paths") if isinstance(report.get("paths"), dict) else {}
    items = paths.get("items") if isinstance(paths.get("items"), list) else []
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  paths: {paths.get('shown', len(items))}",
    ]
    if items:
        lines.append("  pathList:")
        lines.extend(f"    - {path}" for path in items)
    else:
        lines.append("  pathList: none")
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_git_index_text(title: str, root: Path, ok: bool, paths: list[str], status: str, message: str) -> str:
    report = {
        "projectRoot": str(root),
        "ok": ok,
        "paths": {"shown": len(paths), "items": paths},
        "statusText": status,
        "message": message,
    }
    return format_git_index_report_text(title, report)


def _validate_git_restore_max_diff_chars(max_diff_chars: int) -> None:
    if max_diff_chars < 100:
        raise ValueError("max_diff_chars must be at least 100.")
    if max_diff_chars > 200_000:
        raise ValueError("max_diff_chars must be at most 200000.")


def _git_restore_usage_report(root: Path, usage: str, error: str, max_diff_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "paths": {"shown": 0, "items": []},
        "statusText": "",
        "diff": {"text": "", "chars": 0, "truncated": False, "maxChars": max_diff_chars},
        "message": f"Usage: {usage}\nError: {error}",
    }


def _git_restore_unexpected_report(root: Path, paths: list[str], message: str, max_diff_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "paths": {"shown": len(paths), "items": list(paths)},
        "statusText": "",
        "diff": {"text": "", "chars": 0, "truncated": False, "maxChars": max_diff_chars},
        "message": message,
    }


def _git_restore_observation_report(root: Path, observation: object, max_diff_chars: int) -> dict[str, object]:
    paths = list(getattr(observation, "paths"))
    diff = str(getattr(observation, "diff"))
    diff_text, diff_truncated = clip_with_flag(diff, max_diff_chars)
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "paths": {"shown": len(paths), "items": paths},
        "statusText": str(getattr(observation, "status")),
        "diff": {"text": diff_text, "chars": len(diff), "truncated": diff_truncated, "maxChars": max_diff_chars},
        "message": str(getattr(observation, "message")),
    }


def format_git_restore_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    paths = report.get("paths") if isinstance(report.get("paths"), dict) else {}
    items = paths.get("items") if isinstance(paths.get("items"), list) else []
    status = str(report.get("statusText") or "")
    diff = report.get("diff") if isinstance(report.get("diff"), dict) else {}
    diff_text = str(diff.get("text") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  paths: {paths.get('shown', len(items))}",
    ]
    if items:
        lines.append("  pathList:")
        lines.extend(f"    - {path}" for path in items)
    else:
        lines.append("  pathList: none")
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  diffChars: {diff.get('chars', 0)}")
    lines.append(f"  diffTruncated: {'yes' if bool(diff.get('truncated')) else 'no'}")
    lines.append(f"  message: {message}")
    if diff_text:
        lines.append("")
        lines.append(diff_text)
    return "\n".join(lines)


def format_check_switch_text(
    root: Path,
    ok: bool,
    branch: str,
    create: bool,
    current_before: str,
    branch_exists: bool,
    worktree_clean: bool,
    status: str,
    message: str,
) -> str:
    lines = [
        "Check switch:",
        f"  projectRoot: {root}",
        f"  ok: {'yes' if ok else 'no'}",
        f"  branch: {branch}",
        f"  create: {'yes' if create else 'no'}",
        f"  currentBefore: {current_before or '.'}",
        f"  branchExists: {'yes' if branch_exists else 'no'}",
        f"  worktreeClean: {'yes' if worktree_clean else 'no'}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def _git_switch_usage_report(root: Path, usage: str, error: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "branch": "",
        "create": False,
        "currentBefore": "",
        "statusText": "",
        "message": f"Usage: {usage}\nError: {error}",
    }


def _git_switch_unexpected_report(root: Path, branch: str, create: bool, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "branch": branch,
        "create": create,
        "currentBefore": "",
        "statusText": "",
        "message": message,
    }


def format_git_switch_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  branch: {report.get('branch') or '.'}",
        f"  create: {'yes' if bool(report.get('create')) else 'no'}",
        f"  currentBefore: {report.get('currentBefore') or '.'}",
    ]
    if "branchExists" in report:
        lines.append(f"  branchExists: {'yes' if bool(report.get('branchExists')) else 'no'}")
    if "worktreeClean" in report:
        lines.append(f"  worktreeClean: {'yes' if bool(report.get('worktreeClean')) else 'no'}")
    if "currentAfter" in report:
        lines.append(f"  currentAfter: {report.get('currentAfter') or '.'}")
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_switch_text(
    root: Path,
    ok: bool,
    branch: str,
    create: bool,
    current_before: str,
    current_after: str,
    status: str,
    message: str,
) -> str:
    lines = [
        "Switch:",
        f"  projectRoot: {root}",
        f"  ok: {'yes' if ok else 'no'}",
        f"  branch: {branch}",
        f"  create: {'yes' if create else 'no'}",
        f"  currentBefore: {current_before or '.'}",
        f"  currentAfter: {current_after or '.'}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_git_restore_text(title: str, root: Path, ok: bool, paths: list[str], diff: str, status: str, message: str, max_diff_chars: int) -> str:
    _validate_git_restore_max_diff_chars(max_diff_chars)
    diff_text, diff_truncated = clip_with_flag(diff, max_diff_chars)
    report = {
        "projectRoot": str(root),
        "ok": ok,
        "paths": {"shown": len(paths), "items": paths},
        "statusText": status,
        "diff": {"text": diff_text, "chars": len(diff), "truncated": diff_truncated, "maxChars": max_diff_chars},
        "message": message,
    }
    return format_git_restore_report_text(title, report)


def _git_commit_usage_report(root: Path, usage: str, error: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "headBefore": "",
        "headAfter": "",
        "statusText": "",
        "message": f"Usage: {usage}\nError: {error}",
    }


def _git_commit_unexpected_report(root: Path, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "headBefore": "",
        "headAfter": "",
        "statusText": "",
        "message": message,
    }


def _git_commit_observation_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "headBefore": str(getattr(observation, "head_before")),
        "headAfter": str(getattr(observation, "head_after")),
        "statusText": str(getattr(observation, "status")),
        "message": str(getattr(observation, "message")),
    }


def format_git_commit_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  headBefore: {report.get('headBefore') or '.'}",
        f"  headAfter: {report.get('headAfter') or '.'}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_git_commit_text(title: str, root: Path, ok: bool, head_before: str, head_after: str, status: str, message: str) -> str:
    report = {
        "projectRoot": str(root),
        "ok": ok,
        "headBefore": head_before,
        "headAfter": head_after,
        "statusText": status,
        "message": message,
    }
    return format_git_commit_report_text(title, report)
