from __future__ import annotations

from pathlib import Path
import shlex

from .actions import execute_action
from .command_parsing import parse_local_path_args, parse_optional_single_path_argument
from .read_command_parsing import parse_read_request
from .types import CheckGitCommitAction, CheckGitFetchAction, CheckGitPullAction, CheckGitPushAction, CheckGitRestoreAction, CheckGitStageAction, CheckGitStashAction, CheckGitStashApplyAction, CheckGitStashDropAction, CheckGitSwitchAction, CheckGitUnstageAction, GitBlameAction, GitBranchesAction, GitCommitAction, GitConflictsAction, GitFetchAction, GitInfoAction, GitLogAction, GitPullAction, GitPushAction, GitRestoreAction, GitShowAction, GitStageAction, GitStashAction, GitStashApplyAction, GitStashDropAction, GitStashesAction, GitStatusAction, GitSwitchAction, GitUnstageAction
from .workspace_core import RunWorkspace


def _clip(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    if max_length <= 3:
        return value[:max_length]
    return value[: max_length - 3] + "..."


def _indent_block(value: str, spaces: int = 2) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in value.splitlines())


def clip_with_flag(value: str, max_chars: int) -> tuple[str, bool]:
    if len(value) <= max_chars:
        return value, False
    if max_chars <= 0:
        return "", True
    if max_chars <= 20:
        return value[:max_chars], True
    suffix = "\n... [truncated]"
    return value[: max_chars - len(suffix)] + suffix, True


def _split_nonempty_lines(value: str) -> list[str]:
    return [line for line in value.splitlines() if line.strip()]


def _git_status_payload(status: str) -> dict[str, object]:
    lines = _split_nonempty_lines(status)
    return {"text": status, "lines": lines, "count": len(lines)}


def _git_output_payload(output: str, *, truncated: bool, max_output_chars: int) -> dict[str, object]:
    lines = output.splitlines()
    return {
        "text": output,
        "chars": len(output),
        "lines": len(lines),
        "truncated": truncated,
        "maxOutputChars": max_output_chars,
    }


def _git_log_items(log: str) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for line in _split_nonempty_lines(log):
        short_hash, _, subject = line.partition(" ")
        items.append(
            {
                "hash": short_hash,
                "subject": subject,
                "raw": line,
            }
        )
    return items


def get_git_status_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-git-status", session_dir=root / ".vibeagent" / "sessions" / "local-git-status")
    observation = execute_action(workspace, GitStatusAction(type="git_status"))
    if observation.kind != "git_status":
        return {
            "projectRoot": str(root),
            "ok": False,
            "status": _git_status_payload(""),
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "status": _git_status_payload(observation.status),
        "message": observation.message,
    }


def format_git_status_report_text(report: dict[str, object]) -> str:
    status = report.get("status") if isinstance(report.get("status"), dict) else {}
    status_text = str(status.get("text") or "") if isinstance(status, dict) else ""
    lines = [
        "Git status:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]
    if status_text.strip():
        lines.append("  status:")
        lines.append(_indent_block(status_text.strip(), spaces=4))
    else:
        lines.append("  status: none")
    return "\n".join(lines)


def get_git_status_text(project_root: str | Path = ".") -> str:
    return format_git_status_report_text(get_git_status_report(project_root))


def get_git_conflicts_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_markers: int = 200,
    max_files: int = 5000,
) -> str:
    return format_git_conflicts_report_text(get_git_conflicts_report(project_root, argument, max_markers, max_files))


def get_git_conflicts_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_markers: int = 200,
    max_files: int = 5000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        path = parse_optional_single_path_argument(argument)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": "",
            "unmerged": {"shown": 0, "total": 0, "items": []},
            "markers": {"shown": 0, "total": 0, "items": []},
            "scannedFiles": 0,
            "totalFiles": 0,
            "truncated": False,
            "message": f"Usage: /conflicts [path]\n  message: {error}",
        }

    workspace = RunWorkspace(root=root, run_id="local-git-conflicts", session_dir=root / ".vibeagent" / "sessions" / "local-git-conflicts")
    observation = execute_action(
        workspace,
        GitConflictsAction(
            type="git_conflicts",
            path=path,
            max_markers=max_markers,
            max_files=max_files,
        ),
    )
    if observation.kind != "git_conflicts":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path or "",
            "unmerged": {"shown": 0, "total": 0, "items": []},
            "markers": {"shown": 0, "total": 0, "items": []},
            "scannedFiles": 0,
            "totalFiles": 0,
            "truncated": False,
            "message": f"Unexpected observation: {observation.kind}",
        }

    unmerged_items = [
        {"status": item.status, "path": item.path}
        for item in observation.unmerged
    ]
    marker_items = [
        {"path": item.path, "line": item.line, "marker": item.marker, "text": item.text}
        for item in observation.markers
    ]
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path,
        "unmerged": {"shown": len(unmerged_items), "total": observation.unmerged_total, "items": unmerged_items},
        "markers": {"shown": len(marker_items), "total": observation.markers_total, "items": marker_items},
        "scannedFiles": observation.scanned_files,
        "totalFiles": observation.total_files,
        "truncated": observation.truncated,
        "message": observation.message,
    }


def format_git_conflicts_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    unmerged = report.get("unmerged") if isinstance(report.get("unmerged"), dict) else {}
    markers = report.get("markers") if isinstance(report.get("markers"), dict) else {}
    unmerged_items = [item for item in unmerged.get("items", []) if isinstance(item, dict)] if isinstance(unmerged.get("items"), list) else []
    marker_items = [item for item in markers.get("items", []) if isinstance(item, dict)] if isinstance(markers.get("items"), list) else []
    lines = [
        "Git conflicts:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or ''}",
        f"  unmerged: {len(unmerged_items)}/{int(unmerged.get('total', 0) or 0)}",
        f"  markers: {len(marker_items)}/{int(markers.get('total', 0) or 0)}",
        f"  scannedFiles: {int(report.get('scannedFiles', 0) or 0)}/{int(report.get('totalFiles', 0) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if not bool(report.get("ok")):
        return "\n".join(lines)

    if unmerged_items:
        lines.append("  unmergedFiles:")
        for item in unmerged_items:
            lines.append(f"    - {item.get('status') or ''} {item.get('path') or ''}")
    else:
        lines.append("  unmergedFiles: none")

    if marker_items:
        lines.append("  markerLines:")
        for item in marker_items:
            lines.append(f"    - {item.get('path') or ''}:{item.get('line') or ''} [{item.get('marker') or ''}] {item.get('text') or ''}")
    else:
        lines.append("  markerLines: none")
    return "\n".join(lines)


def get_git_info_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-git-info", session_dir=root / ".vibeagent" / "sessions" / "local-git-info")
    observation = execute_action(workspace, GitInfoAction(type="git_info"))
    if observation.kind != "git_info":
        return {
            "projectRoot": str(root),
            "ok": False,
            "isGitRepo": False,
            "branch": "",
            "head": "",
            "upstream": "",
            "ahead": 0,
            "behind": 0,
            "remotes": [],
            "status": _git_status_payload(""),
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "isGitRepo": observation.is_git_repo,
        "branch": observation.branch,
        "head": observation.head,
        "upstream": observation.upstream,
        "ahead": observation.ahead,
        "behind": observation.behind,
        "remotes": [
            {"name": remote.name, "kind": remote.kind, "url": remote.url}
            for remote in observation.remotes
        ],
        "status": _git_status_payload(observation.status),
        "message": observation.message,
    }


def format_git_info_report_text(report: dict[str, object]) -> str:
    remotes = report.get("remotes") if isinstance(report.get("remotes"), list) else []
    status = report.get("status") if isinstance(report.get("status"), dict) else {}
    status_text = str(status.get("text") or "") if isinstance(status, dict) else ""
    lines = [
        "Git info:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  isGitRepo: {'yes' if bool(report.get('isGitRepo')) else 'no'}",
        f"  branch: {report.get('branch') or '.'}",
        f"  head: {report.get('head') or '.'}",
        f"  upstream: {report.get('upstream') or '.'}",
        f"  ahead: {report.get('ahead', 0)}",
        f"  behind: {report.get('behind', 0)}",
    ]
    if remotes:
        lines.append("  remotes:")
        for remote in remotes:
            if isinstance(remote, dict):
                lines.append(f"    - {remote.get('name')} ({remote.get('kind')}): {remote.get('url')}")
    else:
        lines.append("  remotes: none")
    if status_text.strip():
        lines.append("  status:")
        lines.append(_indent_block(status_text.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def get_git_info_text(project_root: str | Path = ".") -> str:
    return format_git_info_report_text(get_git_info_report(project_root))


def get_branches_report(project_root: str | Path = ".", max_branches: int = 100) -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-branches", session_dir=root / ".vibeagent" / "sessions" / "local-branches")
    observation = execute_action(
        workspace,
        GitBranchesAction(type="git_branches", max_branches=max_branches),
    )
    if observation.kind != "git_branches":
        return {
            "projectRoot": str(root),
            "ok": False,
            "current": "",
            "branches": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "gitStatus": _git_status_payload(""),
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "current": observation.current,
        "branches": {
            "shown": len(observation.branches),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": [
                {"name": branch.name, "current": branch.current}
                for branch in observation.branches
            ],
        },
        "gitStatus": _git_status_payload(observation.status),
        "message": observation.message,
    }


def format_branches_report_text(report: dict[str, object]) -> str:
    branches = report.get("branches") if isinstance(report.get("branches"), dict) else {}
    items = branches.get("items") if isinstance(branches, dict) and isinstance(branches.get("items"), list) else []
    status = report.get("gitStatus") if isinstance(report.get("gitStatus"), dict) else {}
    status_text = str(status.get("text") or "") if isinstance(status, dict) else ""
    lines = [
        "Branches:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  current: {report.get('current') or 'detached-or-none'}",
        f"  branches: {branches.get('shown', 0)}/{branches.get('total', 0)}",
        f"  truncated: {'yes' if bool(branches.get('truncated')) else 'no'}",
    ]
    if items:
        lines.append("  items:")
        for branch in items:
            if isinstance(branch, dict):
                marker = "*" if branch.get("current") else "-"
                lines.append(f"    {marker} {branch.get('name')}")
    else:
        lines.append("  items: none")
    if status_text.strip():
        lines.append("  gitStatus:")
        lines.append(_indent_block(_clip(status_text.strip(), 2_000), spaces=4))
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def get_branches_text(project_root: str | Path = ".", max_branches: int = 100) -> str:
    return format_branches_report_text(get_branches_report(project_root, max_branches=max_branches))


def get_log_text(project_root: str | Path = ".", argument: str | None = None, max_count: int = 5) -> str:
    return format_log_report_text(get_log_report(project_root, argument, max_count=max_count))


def parse_log_request(argument: str | None, max_count: int = 5) -> tuple[str | None, int]:
    path: str | None = None
    selected_count = max_count
    if argument and argument.strip():
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if len(parts) > 2:
            raise ValueError("expected optional path and optional count.")
        if len(parts) == 1:
            if parts[0].isdigit():
                selected_count = int(parts[0])
            else:
                path = parts[0]
        elif len(parts) == 2:
            path = parts[0]
            if not parts[1].isdigit():
                raise ValueError(f"invalid count: {parts[1]}")
            selected_count = int(parts[1])
    if selected_count < 1:
        raise ValueError("count must be at least 1.")
    if selected_count > 50:
        raise ValueError("count must be at most 50.")
    return path, selected_count


def get_log_report(project_root: str | Path = ".", argument: str | None = None, max_count: int = 5) -> dict[str, object]:
    try:
        path, selected_count = parse_log_request(argument, max_count)
    except ValueError as error:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "path": ".",
            "maxCount": max_count,
            "commits": {"shown": 0, "items": []},
            "log": "",
            "message": f"Usage: /log [path] [count]\nError: {error}",
        }

    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-log", session_dir=root / ".vibeagent" / "sessions" / "local-log")
    observation = execute_action(
        workspace,
        GitLogAction(type="git_log", path=path, max_count=selected_count),
    )
    if observation.kind != "git_log":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path or ".",
            "maxCount": selected_count,
            "commits": {"shown": 0, "items": []},
            "log": "",
            "message": f"Unexpected observation: {observation.kind}",
        }
    items = _git_log_items(observation.log)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path or ".",
        "maxCount": observation.max_count,
        "commits": {"shown": len(items), "items": items},
        "log": observation.log,
        "message": observation.message,
    }


def format_log_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    commits = report.get("commits") if isinstance(report.get("commits"), dict) else {}
    log_text = str(report.get("log") or "")
    lines = [
        "Log:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or '.'}",
        f"  maxCount: {report.get('maxCount', 0)}",
        f"  commits: {commits.get('shown', 0)}",
        f"  message: {message}",
    ]
    if log_text.strip():
        lines.append("  items:")
        lines.append(_indent_block(log_text.strip(), spaces=4))
    else:
        lines.append("  items: none")
    return "\n".join(lines)


def get_show_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    rev: str | None = None,
    path: str | None = None,
    max_output_chars: int = 12_000,
) -> str:
    return format_show_report_text(
        get_show_report(
            project_root,
            argument,
            rev=rev,
            path=path,
            max_output_chars=max_output_chars,
        )
    )


def parse_show_request(argument: str | None = None, rev: str | None = None, path: str | None = None) -> tuple[str, str | None]:
    if argument and argument.strip():
        if rev is not None or path is not None:
            raise ValueError("show argument cannot be combined with explicit rev or path.")
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if len(parts) > 2:
            raise ValueError("expected optional rev and optional path.")
        if not parts:
            return "HEAD", None
        if len(parts) == 1:
            return parts[0], None
        return parts[0], parts[1]

    selected_rev = (rev or "HEAD").strip()
    if not selected_rev:
        raise ValueError("rev must be a non-empty string.")
    selected_path = path.strip() if path else None
    return selected_rev, selected_path


def get_show_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    rev: str | None = None,
    path: str | None = None,
    max_output_chars: int = 12_000,
) -> dict[str, object]:
    if max_output_chars < 1_000:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "rev": rev or "HEAD",
            "path": path or ".",
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": "Usage: /show [rev] [path]\nError: max_output_chars must be at least 1000.",
        }
    if max_output_chars > 50_000:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "rev": rev or "HEAD",
            "path": path or ".",
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": "Usage: /show [rev] [path]\nError: max_output_chars must be at most 50000.",
        }
    try:
        selected_rev, selected_path = parse_show_request(argument, rev, path)
    except ValueError as error:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "rev": rev or "HEAD",
            "path": path or ".",
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": f"Usage: /show [rev] [path]\nError: {error}",
        }

    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-show", session_dir=root / ".vibeagent" / "sessions" / "local-show")
    observation = execute_action(
        workspace,
        GitShowAction(type="git_show", rev=selected_rev, path=selected_path, max_output_chars=max_output_chars),
    )
    if observation.kind != "git_show":
        return {
            "projectRoot": str(root),
            "ok": False,
            "rev": selected_rev,
            "path": selected_path or ".",
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "rev": observation.rev,
        "path": observation.path or ".",
        "output": _git_output_payload(
            observation.output,
            truncated=observation.truncated,
            max_output_chars=observation.max_output_chars,
        ),
        "message": observation.message,
    }


def format_show_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    output = report.get("output") if isinstance(report.get("output"), dict) else {}
    output_text = str(output.get("text") or "") if isinstance(output, dict) else ""
    lines = [
        "Show:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  rev: {report.get('rev') or 'HEAD'}",
        f"  path: {report.get('path') or '.'}",
        f"  maxOutputChars: {output.get('maxOutputChars', 0) if isinstance(output, dict) else 0}",
        f"  truncated: {'yes' if bool(output.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if output_text.strip():
        lines.append("  output:")
        lines.append(_indent_block(output_text.strip(), spaces=4))
    else:
        lines.append("  output: none")
    return "\n".join(lines)


def get_blame_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    line_range: str | None = None,
    max_output_chars: int = 12_000,
) -> str:
    return format_blame_report_text(
        get_blame_report(
            project_root,
            argument,
            line_range=line_range,
            max_output_chars=max_output_chars,
        )
    )


def get_blame_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    line_range: str | None = None,
    max_output_chars: int = 12_000,
) -> dict[str, object]:
    if max_output_chars < 1_000:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "path": "",
            "range": ".",
            "startLine": None,
            "lineCount": None,
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": "Usage: /blame <path> [start[:end]]\nError: max_output_chars must be at least 1000.",
        }
    if max_output_chars > 50_000:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "path": "",
            "range": ".",
            "startLine": None,
            "lineCount": None,
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": "Usage: /blame <path> [start[:end]]\nError: max_output_chars must be at most 50000.",
        }
    if argument is None or not argument.strip():
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "path": "",
            "range": ".",
            "startLine": None,
            "lineCount": None,
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": "Usage: /blame <path> [start[:end]]",
        }
    try:
        path, start_line, line_count, range_label = parse_read_request(argument, line_range)
    except ValueError as error:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "path": argument,
            "range": line_range or ".",
            "startLine": None,
            "lineCount": None,
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": f"Usage: /blame <path> [start[:end]]\nError: {error}",
        }

    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-blame", session_dir=root / ".vibeagent" / "sessions" / "local-blame")
    observation = execute_action(
        workspace,
        GitBlameAction(
            type="git_blame",
            path=path,
            start_line=start_line,
            line_count=line_count,
            max_output_chars=max_output_chars,
        ),
    )
    if observation.kind != "git_blame":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path,
            "range": range_label or ".",
            "startLine": start_line,
            "lineCount": line_count,
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path,
        "range": range_label or ".",
        "startLine": observation.start_line,
        "lineCount": observation.line_count,
        "output": _git_output_payload(
            observation.blame,
            truncated=observation.truncated,
            max_output_chars=observation.max_output_chars,
        ),
        "message": observation.message,
    }


def format_blame_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    output = report.get("output") if isinstance(report.get("output"), dict) else {}
    output_text = str(output.get("text") or "") if isinstance(output, dict) else ""
    lines = [
        "Blame:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or ''}",
        f"  range: {report.get('range') or '.'}",
        f"  maxOutputChars: {output.get('maxOutputChars', 0) if isinstance(output, dict) else 0}",
        f"  truncated: {'yes' if bool(output.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if output_text.strip():
        lines.append("  output:")
        lines.append(_indent_block(output_text.strip(), spaces=4))
    else:
        lines.append("  output: none")
    return "\n".join(lines)


def get_stashes_report(project_root: str | Path = ".", argument: str | None = None, max_entries: int = 20) -> dict[str, object]:
    try:
        selected_max = parse_stashes_request(argument, max_entries)
    except ValueError as error:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "maxEntries": max_entries,
            "entries": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "message": f"Usage: /stashes [count]\nError: {error}",
        }

    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-stashes", session_dir=root / ".vibeagent" / "sessions" / "local-stashes")
    observation = execute_action(
        workspace,
        GitStashesAction(type="git_stashes", max_entries=selected_max),
    )
    if observation.kind != "git_stashes":
        return {
            "projectRoot": str(root),
            "ok": False,
            "maxEntries": selected_max,
            "entries": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "maxEntries": selected_max,
        "entries": {
            "shown": len(observation.entries),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": [
                {"name": entry.name, "summary": entry.summary}
                for entry in observation.entries
            ],
        },
        "message": observation.message,
    }


def format_stashes_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    entries = report.get("entries") if isinstance(report.get("entries"), dict) else {}
    items = entries.get("items") if isinstance(entries, dict) and isinstance(entries.get("items"), list) else []
    lines = [
        "Stashes:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  entries: {entries.get('shown', 0)}/{entries.get('total', 0)}",
        f"  maxEntries: {report.get('maxEntries', 0)}",
        f"  truncated: {'yes' if bool(entries.get('truncated')) else 'no'}",
    ]
    if items:
        lines.append("  items:")
        for entry in items:
            if isinstance(entry, dict):
                lines.append(f"    - {entry.get('name')}: {entry.get('summary')}")
    else:
        lines.append("  items: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def get_stashes_text(project_root: str | Path = ".", argument: str | None = None, max_entries: int = 20) -> str:
    return format_stashes_report_text(get_stashes_report(project_root, argument, max_entries=max_entries))


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


def parse_stashes_request(argument: str | None, max_entries: int = 20) -> int:
    selected = max_entries
    if argument and argument.strip():
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if len(parts) > 1:
            raise ValueError("expected optional count.")
        if not parts[0].isdigit():
            raise ValueError(f"invalid count: {parts[0]}")
        selected = int(parts[0])
    if selected < 1:
        raise ValueError("count must be at least 1.")
    if selected > 100:
        raise ValueError("count must be at most 100.")
    return selected


def get_check_stash_text(project_root: str | Path = ".", argument: str | None = None, max_diff_chars: int = 12_000) -> str:
    return format_git_stash_report_text("Check stash", get_check_stash_report(project_root, argument, max_diff_chars=max_diff_chars))


def get_check_stash_report(project_root: str | Path = ".", argument: str | None = None, max_diff_chars: int = 12_000) -> dict[str, object]:
    _validate_git_stash_max_chars(max_diff_chars)
    root = Path(project_root).resolve()
    try:
        message, include_untracked = parse_stash_argument(argument)
    except ValueError as error:
        return _git_stash_usage_report(root, "/check-stash [--include-untracked] [message]", str(error), max_diff_chars)

    workspace = RunWorkspace(root=root, run_id="local-check-stash", session_dir=root / ".vibeagent" / "sessions" / "local-check-stash")
    observation = execute_action(
        workspace,
        CheckGitStashAction(type="check_git_stash", message=message, include_untracked=include_untracked),
    )
    if observation.kind != "check_git_stash":
        return _git_stash_unexpected_report(root, f"Unexpected observation: {observation.kind}", max_diff_chars)
    return _git_stash_observation_report(root, observation, "", max_diff_chars)


def get_stash_text(project_root: str | Path = ".", argument: str | None = None, max_diff_chars: int = 12_000) -> str:
    return format_git_stash_report_text("Stash", get_stash_report(project_root, argument, max_diff_chars=max_diff_chars))


def get_stash_report(project_root: str | Path = ".", argument: str | None = None, max_diff_chars: int = 12_000) -> dict[str, object]:
    _validate_git_stash_max_chars(max_diff_chars)
    root = Path(project_root).resolve()
    try:
        message, include_untracked = parse_stash_argument(argument)
    except ValueError as error:
        return _git_stash_usage_report(root, "/stash [--include-untracked] [message]", str(error), max_diff_chars)

    workspace = RunWorkspace(root=root, run_id="local-stash", session_dir=root / ".vibeagent" / "sessions" / "local-stash")
    observation = execute_action(
        workspace,
        GitStashAction(type="git_stash", message=message, include_untracked=include_untracked),
    )
    if observation.kind != "git_stash":
        return _git_stash_unexpected_report(root, f"Unexpected observation: {observation.kind}", max_diff_chars)
    return _git_stash_observation_report(root, observation, observation.stash_ref, max_diff_chars)


def get_check_stash_apply_text(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> str:
    return format_git_stash_apply_report_text("Check stash apply", get_check_stash_apply_report(project_root, argument, max_patch_chars=max_patch_chars))


def get_check_stash_apply_report(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> dict[str, object]:
    _validate_git_stash_max_chars(max_patch_chars)
    root = Path(project_root).resolve()
    stash_ref = (argument or "").strip()
    if not stash_ref:
        return _git_stash_apply_usage_report(root, "/check-stash-apply <stash@{N}>", "stash ref is required.", max_patch_chars)

    workspace = RunWorkspace(root=root, run_id="local-check-stash-apply", session_dir=root / ".vibeagent" / "sessions" / "local-check-stash-apply")
    observation = execute_action(
        workspace,
        CheckGitStashApplyAction(type="check_git_stash_apply", stash_ref=stash_ref),
    )
    if observation.kind != "check_git_stash_apply":
        return _git_stash_apply_unexpected_report(root, stash_ref, f"Unexpected observation: {observation.kind}", max_patch_chars)
    return _git_stash_apply_observation_report(root, observation, max_patch_chars)


def get_stash_apply_text(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> str:
    return format_git_stash_apply_report_text("Stash apply", get_stash_apply_report(project_root, argument, max_patch_chars=max_patch_chars))


def get_stash_apply_report(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> dict[str, object]:
    _validate_git_stash_max_chars(max_patch_chars)
    root = Path(project_root).resolve()
    stash_ref = (argument or "").strip()
    if not stash_ref:
        return _git_stash_apply_usage_report(root, "/stash-apply <stash@{N}>", "stash ref is required.", max_patch_chars)

    workspace = RunWorkspace(root=root, run_id="local-stash-apply", session_dir=root / ".vibeagent" / "sessions" / "local-stash-apply")
    observation = execute_action(
        workspace,
        GitStashApplyAction(type="git_stash_apply", stash_ref=stash_ref),
    )
    if observation.kind != "git_stash_apply":
        return _git_stash_apply_unexpected_report(root, stash_ref, f"Unexpected observation: {observation.kind}", max_patch_chars)
    return _git_stash_apply_observation_report(root, observation, max_patch_chars)


def get_check_stash_drop_text(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> str:
    return format_git_stash_drop_report_text("Check stash drop", get_check_stash_drop_report(project_root, argument, max_patch_chars=max_patch_chars))


def get_check_stash_drop_report(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> dict[str, object]:
    _validate_git_stash_max_chars(max_patch_chars)
    root = Path(project_root).resolve()
    stash_ref = (argument or "").strip()
    if not stash_ref:
        return _git_stash_drop_usage_report(root, "/check-stash-drop <stash@{N}>", "stash ref is required.", max_patch_chars)

    workspace = RunWorkspace(root=root, run_id="local-check-stash-drop", session_dir=root / ".vibeagent" / "sessions" / "local-check-stash-drop")
    observation = execute_action(
        workspace,
        CheckGitStashDropAction(type="check_git_stash_drop", stash_ref=stash_ref),
    )
    if observation.kind != "check_git_stash_drop":
        return _git_stash_drop_unexpected_report(root, stash_ref, f"Unexpected observation: {observation.kind}", max_patch_chars)
    return _git_stash_drop_observation_report(root, observation, max_patch_chars)


def get_stash_drop_text(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> str:
    return format_git_stash_drop_report_text("Stash drop", get_stash_drop_report(project_root, argument, max_patch_chars=max_patch_chars))


def get_stash_drop_report(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> dict[str, object]:
    _validate_git_stash_max_chars(max_patch_chars)
    root = Path(project_root).resolve()
    stash_ref = (argument or "").strip()
    if not stash_ref:
        return _git_stash_drop_usage_report(root, "/stash-drop <stash@{N}>", "stash ref is required.", max_patch_chars)

    workspace = RunWorkspace(root=root, run_id="local-stash-drop", session_dir=root / ".vibeagent" / "sessions" / "local-stash-drop")
    observation = execute_action(
        workspace,
        GitStashDropAction(type="git_stash_drop", stash_ref=stash_ref),
    )
    if observation.kind != "git_stash_drop":
        return _git_stash_drop_unexpected_report(root, stash_ref, f"Unexpected observation: {observation.kind}", max_patch_chars)
    return _git_stash_drop_observation_report(root, observation, max_patch_chars)


def parse_stash_argument(argument: str | None) -> tuple[str | None, bool]:
    if not argument or not argument.strip():
        return None, False
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    include_untracked = False
    message_parts: list[str] = []
    for part in parts:
        if part in {"--include-untracked", "-u"}:
            include_untracked = True
        elif part.startswith("-"):
            raise ValueError(f"unsupported option: {part}")
        else:
            message_parts.append(part)
    message = " ".join(message_parts).strip() or None
    return message, include_untracked


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


def format_git_stash_text(
    title: str,
    root: Path,
    ok: bool,
    message_text: str,
    include_untracked: bool,
    stash_ref: str,
    status: str,
    diff: str,
    message: str,
    max_diff_chars: int,
) -> str:
    _validate_git_stash_max_chars(max_diff_chars)
    diff_text, diff_truncated = clip_with_flag(diff, max_diff_chars)
    report = {
        "projectRoot": str(root),
        "ok": ok,
        "messageText": message_text,
        "includeUntracked": include_untracked,
        "stashRef": stash_ref,
        "statusText": status,
        "diff": {"text": diff_text, "chars": len(diff), "truncated": diff_truncated, "maxChars": max_diff_chars},
        "message": message,
    }
    return format_git_stash_report_text(title, report)


def _validate_git_stash_max_chars(max_chars: int) -> None:
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100.")
    if max_chars > 200_000:
        raise ValueError("max_chars must be at most 200000.")


def _empty_clip_report(max_chars: int) -> dict[str, object]:
    return {"text": "", "chars": 0, "truncated": False, "maxChars": max_chars}


def _clip_report(value: str, max_chars: int) -> dict[str, object]:
    text, truncated = clip_with_flag(value, max_chars)
    return {"text": text, "chars": len(value), "truncated": truncated, "maxChars": max_chars}


def _git_stash_usage_report(root: Path, usage: str, error: str, max_diff_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "messageText": "",
        "includeUntracked": False,
        "stashRef": "",
        "statusText": "",
        "diff": _empty_clip_report(max_diff_chars),
        "message": f"Usage: {usage}\nError: {error}",
    }


def _git_stash_unexpected_report(root: Path, message: str, max_diff_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "messageText": "",
        "includeUntracked": False,
        "stashRef": "",
        "statusText": "",
        "diff": _empty_clip_report(max_diff_chars),
        "message": message,
    }


def _git_stash_observation_report(root: Path, observation: object, stash_ref: str, max_diff_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "messageText": str(getattr(observation, "message_text")),
        "includeUntracked": bool(getattr(observation, "include_untracked")),
        "stashRef": stash_ref,
        "statusText": str(getattr(observation, "status")),
        "diff": _clip_report(str(getattr(observation, "diff")), max_diff_chars),
        "message": str(getattr(observation, "message")),
    }


def format_git_stash_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    diff = report.get("diff") if isinstance(report.get("diff"), dict) else {}
    diff_text = str(diff.get("text") or "")
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  messageText: {report.get('messageText') or '.'}",
        f"  includeUntracked: {'yes' if bool(report.get('includeUntracked')) else 'no'}",
    ]
    if report.get("stashRef"):
        lines.append(f"  stashRef: {report.get('stashRef')}")
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


def format_git_stash_apply_text(
    title: str,
    root: Path,
    ok: bool,
    stash_ref: str,
    worktree_clean: bool | None,
    patch: str,
    status: str,
    message: str,
    max_patch_chars: int,
) -> str:
    _validate_git_stash_max_chars(max_patch_chars)
    patch_text, patch_truncated = clip_with_flag(patch, max_patch_chars)
    report: dict[str, object] = {
        "projectRoot": str(root),
        "ok": ok,
        "stashRef": stash_ref,
        "patch": {"text": patch_text, "chars": len(patch), "truncated": patch_truncated, "maxChars": max_patch_chars},
        "statusText": status,
        "message": message,
    }
    if worktree_clean is not None:
        report["worktreeClean"] = worktree_clean
    return format_git_stash_apply_report_text(title, report)


def _git_stash_apply_usage_report(root: Path, usage: str, error: str, max_patch_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "stashRef": "",
        "patch": _empty_clip_report(max_patch_chars),
        "statusText": "",
        "message": f"Usage: {usage}\nError: {error}",
    }


def _git_stash_apply_unexpected_report(root: Path, stash_ref: str, message: str, max_patch_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "stashRef": stash_ref,
        "patch": _empty_clip_report(max_patch_chars),
        "statusText": "",
        "message": message,
    }


def _git_stash_apply_observation_report(root: Path, observation: object, max_patch_chars: int) -> dict[str, object]:
    report: dict[str, object] = {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "stashRef": str(getattr(observation, "stash_ref")),
        "patch": _clip_report(str(getattr(observation, "patch")), max_patch_chars),
        "statusText": str(getattr(observation, "status")),
        "message": str(getattr(observation, "message")),
    }
    if hasattr(observation, "worktree_clean"):
        report["worktreeClean"] = bool(getattr(observation, "worktree_clean"))
    return report


def format_git_stash_apply_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    patch = report.get("patch") if isinstance(report.get("patch"), dict) else {}
    patch_text = str(patch.get("text") or "")
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  stashRef: {report.get('stashRef') or '.'}",
    ]
    if "worktreeClean" in report:
        lines.append(f"  worktreeClean: {'yes' if bool(report.get('worktreeClean')) else 'no'}")
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  patchChars: {patch.get('chars', 0)}")
    lines.append(f"  patchTruncated: {'yes' if bool(patch.get('truncated')) else 'no'}")
    lines.append(f"  message: {message}")
    if patch_text:
        lines.append("")
        lines.append(patch_text)
    return "\n".join(lines)


def format_git_stash_drop_text(
    title: str,
    root: Path,
    ok: bool,
    stash_ref: str,
    summary: str,
    patch: str,
    remaining_total: int | None,
    message: str,
    max_patch_chars: int,
) -> str:
    _validate_git_stash_max_chars(max_patch_chars)
    patch_text, patch_truncated = clip_with_flag(patch, max_patch_chars)
    report: dict[str, object] = {
        "projectRoot": str(root),
        "ok": ok,
        "stashRef": stash_ref,
        "summary": summary,
        "patch": {"text": patch_text, "chars": len(patch), "truncated": patch_truncated, "maxChars": max_patch_chars},
        "message": message,
    }
    if remaining_total is not None:
        report["remainingTotal"] = remaining_total
    return format_git_stash_drop_report_text(title, report)


def _git_stash_drop_usage_report(root: Path, usage: str, error: str, max_patch_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "stashRef": "",
        "summary": "",
        "patch": _empty_clip_report(max_patch_chars),
        "message": f"Usage: {usage}\nError: {error}",
    }


def _git_stash_drop_unexpected_report(root: Path, stash_ref: str, message: str, max_patch_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "stashRef": stash_ref,
        "summary": "",
        "patch": _empty_clip_report(max_patch_chars),
        "message": message,
    }


def _git_stash_drop_observation_report(root: Path, observation: object, max_patch_chars: int) -> dict[str, object]:
    report: dict[str, object] = {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "stashRef": str(getattr(observation, "stash_ref")),
        "summary": str(getattr(observation, "summary")),
        "patch": _clip_report(str(getattr(observation, "patch")), max_patch_chars),
        "message": str(getattr(observation, "message")),
    }
    if hasattr(observation, "remaining_total"):
        report["remainingTotal"] = int(getattr(observation, "remaining_total"))
    return report


def format_git_stash_drop_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    patch = report.get("patch") if isinstance(report.get("patch"), dict) else {}
    patch_text = str(patch.get("text") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  stashRef: {report.get('stashRef') or '.'}",
        f"  summary: {report.get('summary') or '.'}",
    ]
    if "remainingTotal" in report:
        lines.append(f"  remainingTotal: {report.get('remainingTotal')}")
    lines.append(f"  patchChars: {patch.get('chars', 0)}")
    lines.append(f"  patchTruncated: {'yes' if bool(patch.get('truncated')) else 'no'}")
    lines.append(f"  message: {message}")
    if patch_text:
        lines.append("")
        lines.append(patch_text)
    return "\n".join(lines)


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
