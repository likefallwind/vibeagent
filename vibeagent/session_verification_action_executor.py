from __future__ import annotations

from typing import Any

from .prompt_next_action_runtime_formatting import inline_output_issue_labels
from .process_runtime import execute_run_command_item
from .session import build_session_verification_report, format_session_verification, summarize_session
from .session_action_helpers import select_session_run_id
from .session_input import normalize_optional_run_id
from .types import (
    Observation,
    RunCommandItem,
    RunSessionVerificationAction,
    RunSessionVerificationObservation,
    SessionVerificationAction,
    SessionVerificationObservation,
)
from .workspace import RunWorkspace


def session_verification_group(report: dict[str, Any], name: str) -> tuple[list[dict[str, Any]], int]:
    group = report.get(name) if isinstance(report.get(name), dict) else {}
    commands = group.get("commands") if isinstance(group.get("commands"), list) else []
    return [item for item in commands if isinstance(item, dict)], int(group.get("total", 0) or 0)


def selected_session_verification_commands(
    report: dict[str, Any],
    *,
    include_failed: bool,
    include_pending: bool,
) -> tuple[list[dict[str, Any]], int, int]:
    selected: list[dict[str, Any]] = []
    failed_commands, failed_count = session_verification_group(report, "failed")
    pending_commands, pending_count = session_verification_group(report, "pending")
    if include_failed:
        selected.extend(failed_commands)
    if include_pending:
        selected.extend(pending_commands)

    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for command in selected:
        key = (str(command.get("command") or ""), str(command.get("cwd") or "."))
        if key in seen or not key[0]:
            continue
        seen.add(key)
        deduped.append(command)
    return deduped, pending_count, failed_count


def execute_session_verification_action(
    workspace: RunWorkspace,
    action: object,
    command_timeout_ms: int = 30_000,
) -> Observation | None:
    if isinstance(action, SessionVerificationAction):
        return session_verification_observation(workspace, action)
    if isinstance(action, RunSessionVerificationAction):
        return execute_run_session_verification_action(workspace, action, command_timeout_ms)
    return None


def session_verification_observation(
    workspace: RunWorkspace,
    action: SessionVerificationAction,
) -> SessionVerificationObservation:
    run_id = select_session_run_id(action.run_id, workspace.run_id)
    verified_commands: list[dict[str, object]] = []
    pending_commands: list[dict[str, object]] = []
    failed_commands: list[dict[str, object]] = []
    verified_count = 0
    pending_count = 0
    failed_count = 0
    verification_truncated = False
    try:
        summary = summarize_session(workspace.root, run_id)
        verification = format_session_verification(summary, max_checks=action.max_checks)
        ok = not verification.startswith("Session not found:")
        message = f"Read session verification for {run_id}." if ok else verification
        if ok:
            report = build_session_verification_report(workspace.root, run_id, max_checks=action.max_checks)
            verified_commands, verified_count = session_verification_group(report, "verified")
            pending_commands, pending_count = session_verification_group(report, "pending")
            failed_commands, failed_count = session_verification_group(report, "failed")
            verification_truncated = bool(report.get("truncated"))
    except ValueError as error:
        verification = ""
        ok = False
        message = str(error)
    return SessionVerificationObservation(
        kind="session_verification",
        run_id=run_id,
        ok=ok,
        verification=verification,
        verified_commands=verified_commands,
        pending_commands=pending_commands,
        failed_commands=failed_commands,
        verified_count=verified_count,
        pending_count=pending_count,
        failed_count=failed_count,
        verification_truncated=verification_truncated,
        message=message,
    )


def execute_run_session_verification_action(
    workspace: RunWorkspace,
    action: RunSessionVerificationAction,
    command_timeout_ms: int = 30_000,
) -> RunSessionVerificationObservation:
    run_id = normalize_optional_run_id(action.run_id) or workspace.run_id
    try:
        report = build_session_verification_report(workspace.root, run_id, max_checks=action.max_checks)
        if report.get("exists") is False:
            return RunSessionVerificationObservation(
                kind="run_session_verification",
                run_id=run_id,
                ok=False,
                selected_commands=[],
                selected_count=0,
                pending_count=0,
                failed_count=0,
                results=[],
                stopped_early=False,
                message=str(report.get("message") or f"Session not found: {run_id}"),
            )
        selected, pending_count, failed_count = selected_session_verification_commands(
            report,
            include_failed=action.include_failed,
            include_pending=action.include_pending,
        )
    except ValueError as error:
        return RunSessionVerificationObservation(
            kind="run_session_verification",
            run_id=run_id,
            ok=False,
            selected_commands=[],
            selected_count=0,
            pending_count=0,
            failed_count=0,
            results=[],
            stopped_early=False,
            message=str(error),
        )

    results = []
    stopped_early = False
    for command in selected:
        item = RunCommandItem(
            command=str(command.get("command") or ""),
            cwd=str(command.get("cwd") or "."),
            timeout_ms=action.timeout_ms,
            max_output_chars=action.max_output_chars,
            extract_output_contexts=action.extract_output_contexts,
            extract_output_diagnostics=action.extract_output_diagnostics,
            context_lines=action.context_lines,
            max_diagnostics=action.max_diagnostics,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
        result = execute_run_command_item(workspace, item, command_timeout_ms)
        results.append(result)
        failed = run_session_verification_result_failed(result)
        if failed and action.stop_on_failure:
            stopped_early = len(results) < len(selected)
            break
    ok = len(results) == len(selected) and all(not run_session_verification_result_failed(result) for result in results)
    if selected:
        message = (
            f"Ran {len(results)}/{len(selected)} session verification command(s); "
            f"{'all passed' if ok else 'one or more failed or produced source-linked output diagnostics'}."
        )
    else:
        message = "No pending or failed session verification command(s) selected."
    return RunSessionVerificationObservation(
        kind="run_session_verification",
        run_id=run_id,
        ok=ok,
        selected_commands=selected,
        selected_count=len(selected),
        pending_count=pending_count,
        failed_count=failed_count,
        results=results,
        stopped_early=stopped_early,
        message=message,
    )


def run_session_verification_result_failed(result: object) -> bool:
    return (
        getattr(result, "exit_code", None) != 0
        or bool(getattr(result, "timed_out", False))
        or bool(inline_output_issue_labels(result))
    )
