from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path

from .actions import execute_action
from .session import list_sessions, session_dir, summarize_session
from .session_commands import format_session_plan_report_text, get_plan_report, get_plan_text
from .types import FinalReviewAction, ProcessInfo
from .workflow_checkpoint_commands import (
    build_checkpoint_create_report,
    checkpoint_status_error_report,
    create_local_checkpoint_metadata,
    get_check_checkpoint_delete_report,
    get_check_checkpoint_prune_report,
    get_check_checkpoint_restore_report,
    get_checkpoint_delete_report,
    get_checkpoint_delete_text,
    get_checkpoint_diff_report,
    get_checkpoint_diff_text,
    get_checkpoint_prune_report,
    get_checkpoint_report,
    get_checkpoint_restore_report,
    get_checkpoint_show_report,
    get_checkpoint_show_text,
    get_checkpoint_status_report,
    get_checkpoint_status_text,
    get_checkpoint_text,
    get_checkpoints_report,
    get_checkpoints_text,
    read_local_checkpoint_metadata,
    serialize_checkpoint_info,
    serialize_checkpoint_metadata,
)
from .workflow_diff_commands import (
    clip_with_flag,
    format_diff_contexts_report_text,
    format_diff_hunk_lines,
    format_diff_hunks_report_text,
    format_diff_report_text,
    get_diff_contexts_report,
    get_diff_contexts_text,
    get_diff_hunks_report,
    get_diff_hunks_text,
    get_diff_report,
    get_diff_text,
    parse_diff_argument,
    serialize_diff_hunk,
    serialize_file_context_result,
    validate_diff_contexts_limits,
    validate_diff_hunks_limits,
)
from .workflow_runtime_commands import (
    blocked_command_examples,
    build_project_instructions_template,
    format_context_report_text,
    format_doctor_report_text,
    format_init_report_text,
    format_status_report_text,
    get_command_hard_block_report,
    get_context_report,
    get_context_text,
    get_doctor_report,
    get_doctor_text,
    get_init_report,
    get_status_report,
    get_status_text,
    init_project_instructions,
    normalize_project_instructions_file_name,
)
from .workflow_checkpoint_utils import (
    CHECKPOINT_UNTRACKED_SHOW_LIMIT,
    checkpoint_root,
    clip_local_checkpoint_untracked_paths,
    count_status_kinds,
    display_checkpoint_file,
    format_checkpoint_created,
    is_runtime_checkpoint_path,
    is_safe_checkpoint_relative_path,
    local_checkpoint_untracked_files_match,
    local_checkpoint_untracked_paths,
    normalize_checkpoint_label,
    parse_checkpoint_keep_last,
    read_checkpoint_patch,
    read_checkpoints,
    read_git_head,
    read_local_checkpoint_untracked_manifest,
    resolve_checkpoint_dir,
    restore_local_checkpoint_untracked_files,
    run_git_checkpoint_command,
    save_local_checkpoint_untracked_files,
    short_head,
)
from .workflow_checkpoint_formatting import (
    format_check_checkpoint_delete_report_text,
    format_check_checkpoint_prune_report_text,
    format_check_checkpoint_restore_report_text,
    format_checkpoint_create_report_text,
    format_checkpoint_delete_report_text,
    format_checkpoint_diff_report_text,
    format_checkpoint_prune_report_text,
    format_checkpoint_restore_report_text,
    format_checkpoint_restore_report_text_with_title,
    format_checkpoint_show_report_text,
    format_checkpoint_status_report_text,
    format_checkpoints_report_text,
)
from .workflow_review_formatting import (
    clip_text as _clip,
    filter_handoff_status,
    format_check_location,
    format_focused_test_command,
    format_review_check,
    format_review_file,
    format_review_process,
    format_review_syntax_check,
    indent_block as _indent_block,
    is_runtime_status_path,
    pass_text as _pass_text,
)
from .workspace_core import RunWorkspace
from .workspace import make_run_id, read_git_changes, read_git_diff, read_git_status


def _plain_data(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, list):
        return [_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _plain_data(item) for key, item in value.items()}
    return value


def final_review_status_checks(blocking_issues: list[str]) -> dict[str, bool]:
    return {
        "changes": "Could not read git changes." not in blocking_issues,
        "diff": "Unstaged diff whitespace check failed." not in blocking_issues,
        "stagedDiff": "Staged diff whitespace check failed." not in blocking_issues,
        "python": (
            "Changed Python files have syntax errors." not in blocking_issues
            and "Python syntax check was incomplete." not in blocking_issues
        ),
        "config": (
            "Changed config files have syntax errors." not in blocking_issues
            and "Config syntax check was incomplete." not in blocking_issues
        ),
    }


def final_review_common_report(root: Path, observation: object, *, max_files: int | None = None) -> dict[str, object]:
    blocking_issues = list(getattr(observation, "blocking_issues", []))
    files = list(getattr(observation, "files", []))
    if max_files is not None:
        files = files[:max_files]
    running_processes = list(getattr(observation, "running_processes", []))
    suggested_checks = list(getattr(observation, "suggested_checks", []))
    focused_tests = list(getattr(observation, "focused_test_commands", []))
    python_results = list(getattr(observation, "python", []))
    config_results = list(getattr(observation, "config", []))
    status_checks = final_review_status_checks(blocking_issues)
    return {
        "projectRoot": str(root),
        "ready": bool(getattr(observation, "ready", False)),
        "ok": bool(getattr(observation, "ok", False)),
        "blockingIssues": blocking_issues,
        "warnings": list(getattr(observation, "warnings", [])),
        "changedFiles": {
            "shown": len(files),
            "total": int(getattr(observation, "total_files", 0)),
            "files": [_plain_data(item) for item in files],
        },
        "runningProcesses": {
            "count": len(running_processes),
            "processes": [_plain_data(process) for process in running_processes],
        },
        "suggestedChecks": {
            "shown": len(suggested_checks),
            "total": int(getattr(observation, "suggested_checks_total", 0)),
            "truncated": bool(getattr(observation, "suggested_checks_truncated", False)),
            "commands": [_plain_data(item) for item in suggested_checks],
        },
        "focusedTests": {
            "shown": len(focused_tests),
            "total": int(getattr(observation, "focused_test_commands_total", 0)),
            "truncated": bool(getattr(observation, "focused_test_commands_truncated", False)),
            "relatedTestsTotal": int(getattr(observation, "focused_test_related_tests_total", 0)),
            "commands": [serialize_focused_review_command(item) for item in focused_tests],
        },
        "syntaxChecks": {
            "python": {
                "ok": bool(status_checks["python"]),
                "shown": len(python_results),
                "total": int(getattr(observation, "python_total", 0)),
                "truncated": bool(getattr(observation, "python_truncated", False)),
                "results": [_plain_data(item) for item in python_results],
            },
            "config": {
                "ok": bool(status_checks["config"]),
                "shown": len(config_results),
                "total": int(getattr(observation, "config_total", 0)),
                "truncated": bool(getattr(observation, "config_truncated", False)),
                "results": [_plain_data(item) for item in config_results],
            },
        },
    }


def serialize_focused_review_command(command: object) -> dict[str, object]:
    return {
        "command": str(getattr(command, "command", "") or ""),
        "cwd": str(getattr(command, "cwd", ".") or "."),
        "test": str(getattr(command, "test_path", "") or ""),
        "source": str(getattr(command, "source", "") or ""),
        "reason": str(getattr(command, "reason", "") or ""),
        "available": bool(getattr(command, "available", False)),
        "missingTool": getattr(command, "missing_tool", None),
    }


def local_final_review_workspace(root: Path, prefix: str, run_id: str | None = None) -> RunWorkspace:
    effective_run_id = run_id.strip() if isinstance(run_id, str) and run_id.strip() else f"{prefix}-{make_run_id()}"
    return RunWorkspace(
        root=root,
        run_id=effective_run_id,
        session_dir=session_dir(root, effective_run_id),
    )


def get_review_report(project_root: str | Path = ".", max_files: int = 200, max_checks: int = 5) -> dict[str, object]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    if max_checks < 1:
        raise ValueError("max_checks must be at least 1.")
    if max_checks > 50:
        raise ValueError("max_checks must be at most 50.")
    root = Path(project_root).resolve()
    workspace = local_final_review_workspace(root, "local-review")
    observation = execute_action(
        workspace,
        FinalReviewAction(type="final_review", max_files=max_files, max_checks=max_checks),
    )
    if observation.kind != "final_review":
        return {
            "projectRoot": str(root),
            "ready": False,
            "ok": False,
            "blockingIssues": [f"Unexpected observation: {observation.kind}"],
            "warnings": [],
            "changedFiles": {"shown": 0, "total": 0, "files": []},
            "runningProcesses": {"count": 0, "processes": []},
            "checks": {"changes": False, "diff": False, "stagedDiff": False, "python": False, "config": False},
            "syntaxChecks": {
                "python": {"ok": False, "shown": 0, "total": 0, "truncated": False, "results": []},
                "config": {"ok": False, "shown": 0, "total": 0, "truncated": False, "results": []},
            },
            "suggestedChecks": {"shown": 0, "total": 0, "truncated": False, "commands": []},
            "focusedTests": {"shown": 0, "total": 0, "truncated": False, "relatedTestsTotal": 0, "commands": []},
            "diffCheckOutput": "",
            "stagedDiffCheckOutput": "",
            "status": "",
            "message": f"Unexpected observation: {observation.kind}",
        }
    report = final_review_common_report(root, observation)
    report.update(
        {
            "checks": final_review_status_checks(list(observation.blocking_issues)),
            "diffCheckOutput": str(observation.diff_check),
            "stagedDiffCheckOutput": str(observation.staged_diff_check),
            "status": str(observation.status),
            "message": str(observation.message),
        }
    )
    return report


def format_review_report_text(report: dict[str, object]) -> str:
    changed_files = report["changedFiles"] if isinstance(report["changedFiles"], dict) else {}
    files = changed_files.get("files", []) if isinstance(changed_files, dict) else []
    running = report["runningProcesses"] if isinstance(report["runningProcesses"], dict) else {}
    running_processes = running.get("processes", []) if isinstance(running, dict) else []
    checks_report = report["suggestedChecks"] if isinstance(report["suggestedChecks"], dict) else {}
    checks = checks_report.get("commands", []) if isinstance(checks_report, dict) else []
    focused_report = report["focusedTests"] if isinstance(report.get("focusedTests"), dict) else {}
    focused_tests = focused_report.get("commands", []) if isinstance(focused_report, dict) else []
    syntax_checks = report["syntaxChecks"] if isinstance(report["syntaxChecks"], dict) else {}
    python_report = syntax_checks.get("python", {}) if isinstance(syntax_checks, dict) else {}
    config_report = syntax_checks.get("config", {}) if isinstance(syntax_checks, dict) else {}
    status_checks = report["checks"] if isinstance(report["checks"], dict) else {}
    blocking_issues = report["blockingIssues"] if isinstance(report["blockingIssues"], list) else []
    warnings = report["warnings"] if isinstance(report["warnings"], list) else []
    lines = [
        "Review:",
        f"  ready: {'yes' if bool(report['ready']) else 'no'}",
        f"  changedFiles: {changed_files.get('total', 0)}",
        f"  diffCheck: {_pass_text(bool(status_checks.get('diff')))}",
        f"  stagedDiffCheck: {_pass_text(bool(status_checks.get('stagedDiff')))}",
        f"  python: {_pass_text(bool(python_report.get('ok')))} ({python_report.get('shown', 0)}/{python_report.get('total', 0)})",
        f"  config: {_pass_text(bool(config_report.get('ok')))} ({config_report.get('shown', 0)}/{config_report.get('total', 0)})",
    ]
    if blocking_issues:
        lines.append("  blockingIssues:")
        lines.extend(f"    - {issue}" for issue in blocking_issues)
    if warnings:
        lines.append("  warnings:")
        lines.extend(f"    - {warning}" for warning in warnings)
    if files:
        lines.append("  files:")
        lines.extend(format_review_file(item) for item in files if isinstance(item, dict))
    if running_processes:
        lines.append("  runningProcesses:")
        lines.extend(format_review_process(ProcessInfo(**process)) for process in running_processes if isinstance(process, dict))
    if checks:
        lines.append("  suggestedChecks:")
        lines.extend(format_review_check(item) for item in checks if isinstance(item, dict))
    if focused_tests:
        lines.append("  focusedTests:")
        lines.extend(format_focused_test_command(item) for item in focused_tests if isinstance(item, dict))
    if str(report.get("diffCheckOutput", "")).strip():
        lines.append("  diffCheckOutput:")
        lines.append(_indent_block(_clip(str(report["diffCheckOutput"]).strip(), 2_000), spaces=4))
    if str(report.get("stagedDiffCheckOutput", "")).strip():
        lines.append("  stagedDiffCheckOutput:")
        lines.append(_indent_block(_clip(str(report["stagedDiffCheckOutput"]).strip(), 2_000), spaces=4))
    python_results = python_report.get("results", []) if isinstance(python_report, dict) else []
    failed_python = [item for item in python_results if isinstance(item, dict) and item.get("ok") is False]
    if failed_python:
        lines.append("  pythonFailures:")
        lines.extend(format_review_syntax_check(item) for item in failed_python[:10])
    config_results = config_report.get("results", []) if isinstance(config_report, dict) else []
    failed_config = [item for item in config_results if isinstance(item, dict) and item.get("ok") is False]
    if failed_config:
        lines.append("  configFailures:")
        lines.extend(format_review_syntax_check(item) for item in failed_config[:10])
    lines.append(f"  message: {report['message']}")
    return "\n".join(lines)


def get_review_text(project_root: str | Path = ".", max_files: int = 200, max_checks: int = 5) -> str:
    return format_review_report_text(get_review_report(project_root, max_files=max_files, max_checks=max_checks))


def get_handoff_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_files: int = 200,
    max_checks: int = 10,
    max_status_chars: int = 4_000,
    max_plan_chars: int = 4_000,
) -> dict[str, object]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    if max_checks < 1:
        raise ValueError("max_checks must be at least 1.")
    if max_checks > 50:
        raise ValueError("max_checks must be at most 50.")
    root = Path(project_root).resolve()
    workspace = local_final_review_workspace(root, "local-handoff", run_id=run_id)
    observation = execute_action(
        workspace,
        FinalReviewAction(type="final_review", max_files=max_files, max_checks=max_checks),
    )
    if observation.kind != "final_review":
        return {
            "projectRoot": str(root),
            "ready": False,
            "ok": False,
            "blockingIssues": [f"Unexpected observation: {observation.kind}"],
            "warnings": [],
            "changedFiles": {"shown": 0, "total": 0, "files": []},
            "runningProcesses": {"count": 0, "processes": []},
            "suggestedChecks": {"shown": 0, "total": 0, "truncated": False, "commands": []},
            "focusedTests": {"shown": 0, "total": 0, "truncated": False, "relatedTestsTotal": 0, "commands": []},
            "syntaxChecks": {
                "python": {"shown": 0, "total": 0, "truncated": False, "results": []},
                "config": {"shown": 0, "total": 0, "truncated": False, "results": []},
            },
            "gitStatus": {"text": "", "truncated": False},
            "latestPlan": {"text": "", "truncated": False},
            "message": f"Unexpected observation: {observation.kind}",
        }

    status = filter_handoff_status(observation.status)
    plan_text = get_handoff_plan_text(root, run_id)
    report = final_review_common_report(root, observation, max_files=max_files)
    report.update(
        {
            "gitStatus": {
                "text": _clip(status, max_status_chars),
                "truncated": len(status.strip()) > max_status_chars,
            },
            "latestPlan": {
                "text": _clip(plan_text, max_plan_chars),
                "truncated": len(plan_text.strip()) > max_plan_chars,
            },
            "message": str(observation.message),
        }
    )
    return report


def format_handoff_report_text(report: dict[str, object]) -> str:
    changed_files = report["changedFiles"] if isinstance(report["changedFiles"], dict) else {}
    files = changed_files.get("files", []) if isinstance(changed_files, dict) else []
    running = report["runningProcesses"] if isinstance(report["runningProcesses"], dict) else {}
    running_processes = running.get("processes", []) if isinstance(running, dict) else []
    suggested = report["suggestedChecks"] if isinstance(report["suggestedChecks"], dict) else {}
    suggested_checks = suggested.get("commands", []) if isinstance(suggested, dict) else []
    focused = report["focusedTests"] if isinstance(report.get("focusedTests"), dict) else {}
    focused_tests = focused.get("commands", []) if isinstance(focused, dict) else []
    syntax = report["syntaxChecks"] if isinstance(report["syntaxChecks"], dict) else {}
    python_report = syntax.get("python", {}) if isinstance(syntax, dict) else {}
    config_report = syntax.get("config", {}) if isinstance(syntax, dict) else {}
    git_status = report["gitStatus"] if isinstance(report["gitStatus"], dict) else {}
    latest_plan = report["latestPlan"] if isinstance(report["latestPlan"], dict) else {}
    blocking_issues = report["blockingIssues"] if isinstance(report["blockingIssues"], list) else []
    warnings = report["warnings"] if isinstance(report["warnings"], list) else []

    lines = [
        "Handoff:",
        f"  projectRoot: {report['projectRoot']}",
        f"  ready: {'yes' if bool(report['ready']) else 'no'}",
        f"  changedFiles: {changed_files.get('total', 0)}",
        f"  suggestedChecks: {suggested.get('shown', 0)}/{suggested.get('total', 0)}",
        f"  focusedTests: {focused.get('shown', 0)}/{focused.get('total', 0)}",
        f"  checksTruncated: {'yes' if bool(suggested.get('truncated')) else 'no'}",
    ]
    if blocking_issues:
        lines.append("  blockingIssues:")
        lines.extend(f"    - {issue}" for issue in blocking_issues)
    if warnings:
        lines.append("  warnings:")
        lines.extend(f"    - {warning}" for warning in warnings)
    if running_processes:
        lines.append("  runningProcesses:")
        lines.extend(format_review_process(ProcessInfo(**process)) for process in running_processes if isinstance(process, dict))
    if files:
        lines.append("  files:")
        lines.extend(format_review_file(item) for item in files if isinstance(item, dict))
    else:
        lines.append("  files: none")
    python_results = python_report.get("results", []) if isinstance(python_report, dict) else []
    failed_python = [item for item in python_results if isinstance(item, dict) and item.get("ok") is False]
    if failed_python:
        lines.append("  pythonFailures:")
        lines.extend(format_review_syntax_check(item) for item in failed_python[:10])
    config_results = config_report.get("results", []) if isinstance(config_report, dict) else []
    failed_config = [item for item in config_results if isinstance(item, dict) and item.get("ok") is False]
    if failed_config:
        lines.append("  configFailures:")
        lines.extend(format_review_syntax_check(item) for item in failed_config[:10])
    if suggested_checks:
        lines.append("  suggestedChecks:")
        lines.extend(format_review_check(item) for item in suggested_checks if isinstance(item, dict))
    else:
        lines.append("  suggestedChecks: none")
    if focused_tests:
        lines.append("  focusedTests:")
        lines.extend(format_focused_test_command(item) for item in focused_tests if isinstance(item, dict))
    else:
        lines.append("  focusedTests: none")
    status = str(git_status.get("text", ""))
    if status.strip():
        lines.append("  gitStatus:")
        lines.append(_indent_block(status, spaces=4))
    lines.append("")
    lines.append("Latest plan:")
    lines.append(_indent_block(str(latest_plan.get("text", "")), spaces=2))
    lines.append("")
    lines.append(f"Message: {report['message']}")
    return "\n".join(lines)


def get_handoff_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_files: int = 200,
    max_checks: int = 10,
    max_status_chars: int = 4_000,
    max_plan_chars: int = 4_000,
) -> str:
    return format_handoff_report_text(
        get_handoff_report(
            project_root,
            run_id=run_id,
            max_files=max_files,
            max_checks=max_checks,
            max_status_chars=max_status_chars,
            max_plan_chars=max_plan_chars,
        )
    )


def get_handoff_plan_text(project_root: str | Path = ".", run_id: str | None = None) -> str:
    if run_id:
        return get_plan_text(project_root, run_id)
    for session in list_sessions(project_root, limit=50):
        if session.run_id.startswith("local-"):
            continue
        summary = summarize_session(project_root, session.run_id)
        if summary.latest_plan:
            return format_session_plan_report_text(get_plan_report(project_root, session.run_id))
    return "No sessions with plans found."


def get_changes_report(project_root: str | Path = ".", max_files: int = 200) -> dict[str, object]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-changes", session_dir=root / ".vibeagent" / "sessions" / "local-changes")
    changes = read_git_changes(workspace)
    if not bool(changes["ok"]):
        return {
            "projectRoot": str(root),
            "ok": False,
            "changedFiles": {"shown": 0, "total": 0, "truncated": False, "files": []},
            "counts": {
                "staged": 0,
                "unstaged": 0,
                "untracked": 0,
                "binary": 0,
                "insertions": 0,
                "deletions": 0,
            },
            "message": str(changes["message"]),
        }

    files = [item for item in changes["files"] if isinstance(item, dict)]
    shown = files[:max_files]
    staged = sum(1 for item in files if item.get("staged") is True)
    unstaged = sum(1 for item in files if item.get("unstaged") is True and item.get("untracked") is not True)
    untracked = sum(1 for item in files if item.get("untracked") is True)
    binary = sum(1 for item in files if item.get("binary") is True)
    insertions = sum(int(item.get("staged_insertions") or 0) + int(item.get("unstaged_insertions") or 0) for item in files)
    deletions = sum(int(item.get("staged_deletions") or 0) + int(item.get("unstaged_deletions") or 0) for item in files)
    return {
        "projectRoot": str(root),
        "ok": True,
        "changedFiles": {
            "shown": len(shown),
            "total": len(files),
            "truncated": len(shown) < len(files),
            "files": shown,
        },
        "counts": {
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "binary": binary,
            "insertions": insertions,
            "deletions": deletions,
        },
        "message": str(changes["message"]),
    }


def format_changes_report_text(report: dict[str, object]) -> str:
    changed_files = report["changedFiles"] if isinstance(report["changedFiles"], dict) else {}
    files = changed_files.get("files", []) if isinstance(changed_files, dict) else []
    counts = report["counts"] if isinstance(report["counts"], dict) else {}
    lines = [
        "Changes:",
        f"  projectRoot: {report['projectRoot']}",
        f"  ok: {'yes' if bool(report['ok']) else 'no'}",
    ]
    if bool(report["ok"]):
        lines.extend(
            [
                f"  changedFiles: {changed_files.get('total', 0)}",
                f"  shownFiles: {changed_files.get('shown', 0)}/{changed_files.get('total', 0)}",
                f"  stagedFiles: {counts.get('staged', 0)}",
                f"  unstagedFiles: {counts.get('unstaged', 0)}",
                f"  untrackedFiles: {counts.get('untracked', 0)}",
                f"  binaryFiles: {counts.get('binary', 0)}",
                f"  insertions: {counts.get('insertions', 0)}",
                f"  deletions: {counts.get('deletions', 0)}",
                f"  truncated: {'yes' if bool(changed_files.get('truncated')) else 'no'}",
            ]
        )
    if files:
        lines.append("  files:")
        lines.extend(format_review_file(item) for item in files if isinstance(item, dict))
    elif bool(report["ok"]):
        lines.append("  files: none")
    lines.append(f"  message: {report['message']}")
    return "\n".join(lines)


def get_changes_text(project_root: str | Path = ".", max_files: int = 200) -> str:
    return format_changes_report_text(get_changes_report(project_root, max_files=max_files))


def get_check_checkpoint_restore_text(checkpoint_id: str | None, project_root: str | Path = ".") -> str:
    return format_check_checkpoint_restore_report_text(get_check_checkpoint_restore_report(checkpoint_id, project_root))


def get_checkpoint_restore_text(checkpoint_id: str | None, project_root: str | Path = ".") -> str:
    return format_checkpoint_restore_report_text(get_checkpoint_restore_report(checkpoint_id, project_root))


def get_check_checkpoint_delete_text(checkpoint_id: str | None, project_root: str | Path = ".") -> str:
    report = get_check_checkpoint_delete_report(checkpoint_id, project_root)
    if str(report.get("message") or "").startswith("Usage:"):
        return str(report["message"])
    return format_check_checkpoint_delete_report_text(report)


def get_check_checkpoint_prune_text(keep_last: str | int | None, project_root: str | Path = ".") -> str:
    return format_check_checkpoint_prune_report_text(get_check_checkpoint_prune_report(keep_last, project_root))


def get_checkpoint_prune_text(keep_last: str | int | None, project_root: str | Path = ".") -> str:
    return format_checkpoint_prune_report_text(get_checkpoint_prune_report(keep_last, project_root))
