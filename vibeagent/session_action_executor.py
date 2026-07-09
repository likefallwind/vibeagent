from __future__ import annotations

from .session import (
    build_session_verification_report,
    format_session_verification,
    summarize_session,
)
from .session_action_helpers import select_session_run_id
from .session_audit_action_executor import execute_session_audit_action, execute_session_handoff_action
from .session_output_action_executor import execute_session_output_action
from .session_report_action_executor import execute_session_report_action
from .session_verification_action_executor import (
    execute_run_session_verification_action,
    session_verification_group,
)
from .types import (
    Observation,
    SessionAuditAction,
    SessionHandoffAction,
    RunSessionVerificationAction,
    SessionVerificationAction,
    SessionVerificationObservation,
)
from .workspace import RunWorkspace


def execute_session_action(workspace: RunWorkspace, action: object, command_timeout_ms: int = 30_000) -> Observation | None:
    output_observation = execute_session_output_action(workspace, action)
    if output_observation is not None:
        return output_observation

    report_observation = execute_session_report_action(workspace, action)
    if report_observation is not None:
        return report_observation

    if isinstance(action, SessionVerificationAction):
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

    if isinstance(action, RunSessionVerificationAction):
        return execute_run_session_verification_action(workspace, action, command_timeout_ms)

    if isinstance(action, SessionAuditAction):
        return execute_session_audit_action(workspace, action)

    if isinstance(action, SessionHandoffAction):
        return execute_session_handoff_action(workspace, action)

    return None
