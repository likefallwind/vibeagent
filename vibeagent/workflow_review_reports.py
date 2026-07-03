from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path

from .session import session_dir
from .workspace import make_run_id
from .workspace_core import RunWorkspace


def plain_data(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, list):
        return [plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): plain_data(item) for key, item in value.items()}
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
            "files": [plain_data(item) for item in files],
        },
        "runningProcesses": {
            "count": len(running_processes),
            "processes": [plain_data(process) for process in running_processes],
        },
        "suggestedChecks": {
            "shown": len(suggested_checks),
            "total": int(getattr(observation, "suggested_checks_total", 0)),
            "truncated": bool(getattr(observation, "suggested_checks_truncated", False)),
            "commands": [plain_data(item) for item in suggested_checks],
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
                "results": [plain_data(item) for item in python_results],
            },
            "config": {
                "ok": bool(status_checks["config"]),
                "shown": len(config_results),
                "total": int(getattr(observation, "config_total", 0)),
                "truncated": bool(getattr(observation, "config_truncated", False)),
                "results": [plain_data(item) for item in config_results],
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
