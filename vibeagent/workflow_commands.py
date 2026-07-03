from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .session import list_sessions, summarize_session
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
from .workflow_change_commands import (
    format_changes_report_text,
    get_changes_report,
    get_changes_text,
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
from .workflow_review_reports import (
    final_review_common_report,
    final_review_status_checks,
    local_final_review_workspace,
    serialize_focused_review_command,
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
