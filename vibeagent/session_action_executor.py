from __future__ import annotations

from .session_audit_action_executor import execute_session_audit_action, execute_session_handoff_action
from .session_output_action_executor import execute_session_output_action
from .session_report_action_executor import execute_session_report_action
from .session_verification_action_executor import execute_session_verification_action
from .types import (
    Observation,
    SessionAuditAction,
    SessionHandoffAction,
)
from .workspace import RunWorkspace


def execute_session_action(workspace: RunWorkspace, action: object, command_timeout_ms: int = 30_000) -> Observation | None:
    output_observation = execute_session_output_action(workspace, action)
    if output_observation is not None:
        return output_observation

    report_observation = execute_session_report_action(workspace, action)
    if report_observation is not None:
        return report_observation

    verification_observation = execute_session_verification_action(workspace, action, command_timeout_ms)
    if verification_observation is not None:
        return verification_observation

    if isinstance(action, SessionAuditAction):
        return execute_session_audit_action(workspace, action)

    if isinstance(action, SessionHandoffAction):
        return execute_session_handoff_action(workspace, action)

    return None
