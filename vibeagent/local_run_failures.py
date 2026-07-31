from __future__ import annotations

from pathlib import Path

from .local_runtime_reports import empty_command_output_analysis


RUN_USAGE = "Usage: /run <shell command>"
RUN_SEQUENCE_USAGE = "Usage: /run-seq <cmd> ;; <cmd>"
CHECK_RUN_SEQUENCE_USAGE = "Usage: /check-run-seq <cmd> ;; <cmd>"


def run_failure_report(
    root: Path,
    message: str,
    *,
    command: str | None,
    cwd: str | None,
    timeout_ms: int,
    max_output_chars: int,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "command": (command or "").strip(),
        "cwd": cwd or ".",
        "exitCode": None,
        "timedOut": False,
        "signal": None,
        "sandboxed": False,
        "sandboxWarning": None,
        "timeoutMs": timeout_ms,
        "maxOutputChars": max_output_chars,
        "stdout": "",
        "stderr": "",
        "stdoutTruncated": False,
        "stderrTruncated": False,
        "analysis": empty_command_output_analysis(),
        "message": message,
    }


def usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def run_sequence_failure_report(
    root: Path,
    message: str,
    *,
    selected_commands: list[str] | None = None,
    stop_on_failure: bool = True,
) -> dict[str, object]:
    selected = list(selected_commands or [])
    return {
        "projectRoot": str(root),
        "ok": False,
        "clean": False,
        "commands": {"shown": 0, "total": len(selected), "requested": selected},
        "stopOnFailure": stop_on_failure,
        "stoppedEarly": False,
        "results": [],
        "message": message,
    }


def check_run_sequence_failure_report(
    root: Path,
    message: str,
    *,
    selected_commands: list[str] | None = None,
) -> dict[str, object]:
    selected = list(selected_commands or [])
    return {
        "projectRoot": str(root),
        "ok": False,
        "commands": {"shown": 0, "total": len(selected), "requested": selected},
        "checks": [],
        "message": message,
    }
