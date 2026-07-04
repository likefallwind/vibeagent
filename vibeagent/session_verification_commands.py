from __future__ import annotations

from pathlib import Path

from .local_runtime_reports import (
    indent_block,
    serialize_command_result,
    sum_command_result_duration_ms,
)
from .session import build_session_verification_report, get_last_session_id
from .session_audit_reports import format_session_verification_report_text as _format_session_verification_report_text
from .session_input import normalize_optional_run_id
from .session_verification_action_executor import execute_run_session_verification_action
from .types import RunSessionVerificationAction
from .workspace_core import RunWorkspace


def get_session_verification_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_checks: int = 50,
) -> str:
    return format_session_verification_report_text(
        get_session_verification_report(project_root, run_id, max_checks=max_checks)
    )


def get_session_verification_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_checks: int = 50,
    max_text: int = 160,
) -> dict[str, object]:
    selected = normalize_optional_run_id(run_id) or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_verification_report(
            project_root,
            selected,
            max_checks=max_checks,
            max_text=max_text,
        )
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "invalid",
            "message": str(error),
        }


def format_session_verification_report_text(report: dict[str, object]) -> str:
    return _format_session_verification_report_text(report)


def get_run_session_verification_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_checks: int = 10,
    include_failed: bool = True,
    include_pending: bool = True,
    timeout_ms: int = 30_000,
    max_output_chars: int = 12_000,
    stop_on_failure: bool = True,
) -> str:
    return format_run_session_verification_report_text(
        get_run_session_verification_report(
            project_root,
            run_id,
            max_checks=max_checks,
            include_failed=include_failed,
            include_pending=include_pending,
            timeout_ms=timeout_ms,
            max_output_chars=max_output_chars,
            stop_on_failure=stop_on_failure,
        )
    )


def get_run_session_verification_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_checks: int = 10,
    include_failed: bool = True,
    include_pending: bool = True,
    timeout_ms: int = 30_000,
    max_output_chars: int = 12_000,
    stop_on_failure: bool = True,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    selected = normalize_optional_run_id(run_id)

    def failure(message: str, selected: str | None = selected) -> dict[str, object]:
        return {
            "projectRoot": str(root),
            "session": selected,
            "exists": False,
            "ok": False,
            "selectedCommands": [],
            "selectedCount": 0,
            "pendingCount": 0,
            "failedCount": 0,
            "commands": {"shown": 0, "total": 0},
            "includeFailed": include_failed,
            "includePending": include_pending,
            "stopOnFailure": stop_on_failure,
            "stoppedEarly": False,
            "durationMs": 0,
            "results": [],
            "message": message,
        }

    selected = selected or get_last_session_id(project_root)
    if not selected:
        return failure("No sessions found.", None)
    if max_checks < 1:
        return failure("Usage: /run-session-verification [run-id]\nError: max_checks must be at least 1.", selected)
    if max_checks > 10:
        return failure("Usage: /run-session-verification [run-id]\nError: max_checks must be at most 10.", selected)
    if timeout_ms < 100:
        return failure("Usage: /run-session-verification [run-id]\nError: timeout_ms must be at least 100.", selected)
    if timeout_ms > 600_000:
        return failure("Usage: /run-session-verification [run-id]\nError: timeout_ms must be at most 600000.", selected)
    if max_output_chars < 1_000:
        return failure("Usage: /run-session-verification [run-id]\nError: max_output_chars must be at least 1000.", selected)
    if max_output_chars > 50_000:
        return failure("Usage: /run-session-verification [run-id]\nError: max_output_chars must be at most 50000.", selected)
    if not include_failed and not include_pending:
        return failure(
            "Usage: /run-session-verification [run-id]\nError: include_failed and include_pending cannot both be false.",
            selected,
        )

    workspace = RunWorkspace(
        root=root,
        run_id="local-run-session-verification",
        session_dir=root / ".vibeagent" / "sessions" / "local-run-session-verification",
    )
    observation = execute_run_session_verification_action(
        workspace,
        RunSessionVerificationAction(
            type="run_session_verification",
            run_id=selected,
            max_checks=max_checks,
            include_failed=include_failed,
            include_pending=include_pending,
            timeout_ms=timeout_ms,
            max_output_chars=max_output_chars,
            stop_on_failure=stop_on_failure,
        ),
        command_timeout_ms=timeout_ms,
    )
    results = [serialize_command_result(result, index=index) for index, result in enumerate(observation.results, start=1)]
    return {
        "projectRoot": str(root),
        "session": observation.run_id,
        "exists": observation.message != f"Session not found: {selected}",
        "ok": observation.ok,
        "selectedCommands": observation.selected_commands,
        "selectedCount": observation.selected_count,
        "pendingCount": observation.pending_count,
        "failedCount": observation.failed_count,
        "commands": {"shown": len(results), "total": observation.selected_count},
        "includeFailed": include_failed,
        "includePending": include_pending,
        "stopOnFailure": stop_on_failure,
        "stoppedEarly": observation.stopped_early,
        "durationMs": sum_command_result_duration_ms(list(observation.results)),
        "results": results,
        "message": observation.message,
    }


def format_run_session_verification_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    results = [item for item in report.get("results", []) if isinstance(item, dict)] if isinstance(report.get("results"), list) else []
    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    lines = [
        "Run session verification:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  session: {report.get('session') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  selected: {int(report.get('selectedCount', 0) or 0)}",
        f"  commands: {int(commands.get('shown', len(results)) or 0)}/{int(commands.get('total', len(results)) or 0)}",
        f"  pendingTotal: {int(report.get('pendingCount', 0) or 0)}",
        f"  failedTotal: {int(report.get('failedCount', 0) or 0)}",
        f"  includeFailed: {'yes' if bool(report.get('includeFailed')) else 'no'}",
        f"  includePending: {'yes' if bool(report.get('includePending')) else 'no'}",
        f"  stopOnFailure: {'yes' if bool(report.get('stopOnFailure')) else 'no'}",
        f"  stoppedEarly: {'yes' if bool(report.get('stoppedEarly')) else 'no'}",
        f"  durationMs: {report.get('durationMs', 0)}",
        f"  message: {message}",
    ]
    if results:
        lines.append("  results:")
        for position, result in enumerate(results, start=1):
            index = result.get("index", position)
            lines.extend(
                [
                    f"    - index: {index}",
                    f"      command: {result.get('command') or ''}",
                    f"      cwd: {result.get('cwd') or '.'}",
                    f"      ok: {'yes' if bool(result.get('ok')) else 'no'}",
                    f"      exitCode: {result.get('exitCode') if result.get('exitCode') is not None else '.'}",
                    f"      timedOut: {'yes' if bool(result.get('timedOut')) else 'no'}",
                    f"      durationMs: {result.get('durationMs', 0)}",
                    f"      stdoutTruncated: {'yes' if bool(result.get('stdoutTruncated')) else 'no'}",
                    f"      stderrTruncated: {'yes' if bool(result.get('stderrTruncated')) else 'no'}",
                ]
            )
            stdout = str(result.get("stdout") or "")
            stderr = str(result.get("stderr") or "")
            if stdout:
                lines.append("      stdout:")
                lines.append(indent_block(stdout.rstrip(), spaces=8))
            else:
                lines.append("      stdout: none")
            if stderr:
                lines.append("      stderr:")
                lines.append(indent_block(stderr.rstrip(), spaces=8))
            else:
                lines.append("      stderr: none")
    else:
        lines.append("  results: none")
    return "\n".join(lines)
