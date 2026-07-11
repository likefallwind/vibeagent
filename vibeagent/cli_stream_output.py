from __future__ import annotations

import json
from pathlib import Path
import sys
from threading import Lock
from typing import Any, TextIO

from .agent_result import AgentResult


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
                "event": event,
            }
        )

    def result(self, payload: dict[str, object]) -> None:
        self.emit({"type": "result", **payload})

    def emit(self, payload: dict[str, object]) -> None:
        with self._lock:
            self.sequence += 1
            record = {"sequence": self.sequence, **payload}
            self.output.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            self.output.flush()


def build_code_result_payload(result: AgentResult, prior_context: object) -> dict[str, object]:
    return {
        "kind": "code",
        "success": result.success,
        "status": result.status,
        "stopReason": code_result_stop_reason(result),
        "message": result.message,
        "runId": result.run_id,
        "sessionId": result.run_id,
        "runDir": str(result.run_dir),
        "iterations": result.iterations,
        "numTurns": result.iterations,
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
    }


def error_result_payload(error: str, *, kind: str = "error", status: str = "failed") -> dict[str, object]:
    return {"kind": kind, "success": False, "status": status, "error": error}


def code_result_stop_reason(result: AgentResult) -> str:
    if result.success and result.completion_ready:
        return "completed"
    if result.success and not result.completion_ready:
        return "blocked"
    return "failed"


__all__ = ["JsonEventStream", "build_code_result_payload", "code_result_stop_reason", "error_result_payload"]
