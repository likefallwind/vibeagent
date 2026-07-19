from __future__ import annotations

import json
from pathlib import Path
import sys
from threading import Lock
from typing import Any, TextIO

from . import MACHINE_OUTPUT_SCHEMA_VERSION, __version__
from .agent_result import AgentResult


CODE_RESULT_SNAKE_CASE_ALIAS_KEYS = {
    "priorContext": "prior_context",
    "runDir": "run_dir",
    "completionReady": "completion_ready",
    "completionBlockers": "completion_blockers",
    "completionWarnings": "completion_warnings",
    "completionBlockedCount": "completion_blocked_count",
    "latestCompletionBlockers": "latest_completion_blockers",
    "latestCompletionPendingChecks": "latest_completion_pending_checks",
    "latestCompletionFailedChecks": "latest_completion_failed_checks",
    "latestCompletionFinalReviewIssues": "latest_completion_final_review_issues",
    "latestCompletionFinalReviewChangedFiles": "latest_completion_final_review_changed_files",
    "latestCompletionToolErrors": "latest_completion_tool_errors",
    "latestCompletionCheckpointFailures": "latest_completion_checkpoint_failures",
    "latestCompletionActiveProcesses": "latest_completion_active_processes",
    "latestCompletionDeniedApprovals": "latest_completion_denied_approvals",
    "changedFiles": "changed_files",
    "verificationChecks": "verification_checks",
    "pendingVerificationChecks": "pending_verification_checks",
    "failedVerificationChecks": "failed_verification_checks",
    "pendingUserInput": "pending_user_input",
    "userInputRequests": "user_input_requests",
}


class JsonEventStream:
    def __init__(self, output: TextIO | None = None) -> None:
        self.output = output if output is not None else sys.stdout
        self.sequence = 0
        self._lock = Lock()

    def session_event(self, session_dir: Path, event: dict[str, Any]) -> None:
        self.emit(
            {
                "type": "event",
                "runId": session_dir.name,
                "sessionId": session_dir.name,
                "session_id": session_dir.name,
                "event": event,
            }
        )

    def result(self, payload: dict[str, object]) -> None:
        self.emit({"type": "result", **payload})

    def emit(self, payload: dict[str, object]) -> None:
        with self._lock:
            self.sequence += 1
            record = {
                "sequence": self.sequence,
                "schemaVersion": MACHINE_OUTPUT_SCHEMA_VERSION,
                "version": __version__,
                **payload,
            }
            self.output.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            self.output.flush()


def build_code_result_payload(result: AgentResult, prior_context: object) -> dict[str, object]:
    user_input_requests = code_result_user_input_requests(result)
    pending_user_input = code_result_has_pending_user_input(result)
    stop_reason = code_result_stop_reason(result)
    exit_code = code_result_exit_code(result)
    payload = {
        "kind": "code",
        "schemaVersion": MACHINE_OUTPUT_SCHEMA_VERSION,
        "version": __version__,
        "success": result.success,
        **machine_result_status_fields(status=result.status, stop_reason=stop_reason, exit_code=exit_code),
        "message": result.message,
        "result": result.message,
        "runId": result.run_id,
        "sessionId": result.run_id,
        "session_id": result.run_id,
        "runDir": str(result.run_dir),
        "iterations": result.iterations,
        "numTurns": result.iterations,
        "num_turns": result.iterations,
        "steps": len(result.steps),
        "priorContext": prior_context.to_json(),
        "plan": [{"status": item.status, "step": item.step} for item in result.plan],
        "completionReady": result.completion_ready,
        "completionBlockers": result.completion_blockers,
        "completionWarnings": result.completion_warnings,
        "completionBlockedCount": result.completion_blocked_count,
        "latestCompletionBlockers": result.latest_completion_blockers,
        "latestCompletionPendingChecks": result.latest_completion_pending_verification_checks,
        "latestCompletionFailedChecks": result.latest_completion_failed_verification_checks,
        "latestCompletionFinalReviewIssues": result.latest_completion_final_review_issues,
        "latestCompletionFinalReviewChangedFiles": result.latest_completion_final_review_changed_files,
        "latestCompletionToolErrors": result.latest_completion_tool_errors,
        "latestCompletionCheckpointFailures": result.latest_completion_checkpoint_failures,
        "latestCompletionActiveProcesses": result.latest_completion_active_background_processes,
        "latestCompletionDeniedApprovals": result.latest_completion_denied_approvals,
        "changedFiles": result.final_review_changed_files,
        "verificationChecks": result.verification_checks,
        "pendingVerificationChecks": result.pending_verification_checks,
        "failedVerificationChecks": result.failed_verification_checks,
        "pendingUserInput": pending_user_input,
        "pending_user_input": pending_user_input,
        "userInputRequests": user_input_requests,
        "user_input_requests": user_input_requests,
    }
    payload.update(code_result_snake_case_aliases(payload))
    return payload


def build_chat_result_payload(message: str) -> dict[str, object]:
    return {
        "kind": "chat",
        "schemaVersion": MACHINE_OUTPUT_SCHEMA_VERSION,
        "version": __version__,
        "success": True,
        **machine_result_status_fields(status="completed", stop_reason="completed", exit_code=0),
        "message": message,
        "result": message,
    }


def code_result_snake_case_aliases(payload: dict[str, object]) -> dict[str, object]:
    return {
        alias: payload[key]
        for key, alias in CODE_RESULT_SNAKE_CASE_ALIAS_KEYS.items()
        if key in payload and alias not in payload
    }


def code_result_exit_code(result: AgentResult) -> int:
    return 0 if result.success and result.completion_ready else 1


def machine_result_status_fields(
    *,
    status: str,
    stop_reason: str,
    exit_code: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "stopReason": stop_reason,
        "stop_reason": stop_reason,
    }
    if exit_code is not None:
        payload["exitCode"] = exit_code
        payload["exit_code"] = exit_code
    return payload


def error_result_payload(
    error: str,
    *,
    kind: str = "error",
    status: str = "failed",
    exit_code: int | None = None,
) -> dict[str, object]:
    stop_reason = "interrupted" if status == "interrupted" else "failed"
    payload: dict[str, object] = {
        "kind": kind,
        "schemaVersion": MACHINE_OUTPUT_SCHEMA_VERSION,
        "version": __version__,
        "success": False,
        **machine_result_status_fields(status=status, stop_reason=stop_reason, exit_code=exit_code),
        "error": error,
    }
    return payload


def add_duration_fields(payload: dict[str, object], duration_ms: int) -> None:
    payload["durationMs"] = duration_ms
    payload["duration_ms"] = duration_ms


def code_result_stop_reason(result: AgentResult) -> str:
    if code_result_has_pending_user_input(result):
        return "user_input"
    if result.success and result.completion_ready:
        return "completed"
    if result.success and not result.completion_ready:
        return "blocked"
    return "failed"


def code_result_has_pending_user_input(result: AgentResult) -> bool:
    return any(
        getattr(observation, "kind", None) == "ask_user" and bool(getattr(observation, "cancelled", False))
        for observation in result.observations
    )


def code_result_user_input_requests(result: AgentResult) -> list[dict[str, object]]:
    requests: list[dict[str, object]] = []
    for observation in result.observations:
        if getattr(observation, "kind", None) != "ask_user":
            continue
        answer = getattr(observation, "answer", None)
        request = {
            "question": str(getattr(observation, "question", "")),
            "options": list(getattr(observation, "options", [])),
            "answer": answer,
            "cancelled": bool(getattr(observation, "cancelled", False)),
            "message": str(getattr(observation, "message", "")),
        }
        requests.append(request)
    return requests


__all__ = [
    "CODE_RESULT_SNAKE_CASE_ALIAS_KEYS",
    "JsonEventStream",
    "add_duration_fields",
    "build_chat_result_payload",
    "build_code_result_payload",
    "code_result_snake_case_aliases",
    "code_result_has_pending_user_input",
    "code_result_stop_reason",
    "code_result_user_input_requests",
    "error_result_payload",
]
