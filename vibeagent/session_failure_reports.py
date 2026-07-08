from __future__ import annotations

from pathlib import Path
from typing import Any

from .session_audit_serialization import serialize_session_failure
from .session_store import read_session_events
from .session_types import SessionEvent
from .session_utils import compact, is_failed_tool_result, session_dir


def format_session_failures(
    project_root: str | Path,
    run_id: str,
    max_failures: int = 50,
    max_text: int = 500,
) -> str:
    validate_session_failures_limits(max_failures, max_text)

    current_session_dir = session_dir(project_root, run_id)
    if not current_session_dir.is_dir():
        return f"Session not found: {run_id}"

    failures = session_failure_entries(read_session_events(project_root, run_id), max_text=max_text)
    shown_failures = failures[-max_failures:]
    omitted = len(failures) - len(shown_failures)
    lines = [
        "Session failures:",
        f"  session: {run_id}",
        f"  failures: {len(failures)}",
        f"  shown: {len(shown_failures)}/{len(failures)}",
        "  entries:",
    ]
    if omitted > 0:
        lines.append(f"    - [{omitted} older failure(s) omitted]")
    if not shown_failures:
        lines.append("    - none")
        return "\n".join(lines)
    for failure in shown_failures:
        lines.append(f"    - #{failure['line_number']} {failure['type']}: {failure['name']}")
        if failure["message"]:
            lines.append(f"      message: {failure['message']}")
        if failure["detail"]:
            lines.append(f"      detail: {failure['detail']}")
    return "\n".join(lines)


def validate_session_failures_limits(max_failures: int, max_text: int) -> None:
    if max_failures < 1:
        raise ValueError("max_failures must be at least 1.")
    if max_failures > 200:
        raise ValueError("max_failures must be at most 200.")
    if max_text < 80:
        raise ValueError("max_text must be at least 80.")
    if max_text > 5_000:
        raise ValueError("max_text must be at most 5000.")


def build_session_failures_report(
    project_root: str | Path,
    run_id: str,
    max_failures: int = 50,
    max_text: int = 500,
) -> dict[str, Any]:
    validate_session_failures_limits(max_failures, max_text)

    current_session_dir = session_dir(project_root, run_id)
    if not current_session_dir.is_dir():
        return {
            "session": run_id,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": f"Session not found: {run_id}",
        }

    failures = session_failure_entries(read_session_events(project_root, run_id), max_text=max_text)
    shown_failures = failures[-max_failures:]
    omitted = len(failures) - len(shown_failures)
    ok = len(failures) == 0
    return {
        "session": run_id,
        "exists": True,
        "ok": ok,
        "status": "ready" if ok else "failed",
        "failures": {
            "total": len(failures),
            "shown": len(shown_failures),
            "omitted": omitted,
            "truncated": omitted > 0,
            "items": [serialize_session_failure(failure, max_text) for failure in shown_failures],
        },
        "message": "No session failures found." if ok else f"Found {len(failures)} session failure(s).",
    }


def session_failure_entries(events: list[SessionEvent], max_text: int) -> list[dict[str, str | int]]:
    failures: list[dict[str, str | int]] = []
    last_approval_request: dict[str, Any] | None = None
    for event in events:
        if event.malformed:
            failures.append(
                {
                    "line_number": event.line_number,
                    "type": "malformed",
                    "name": "event",
                    "message": compact(event.error or "Malformed event row.", max_text),
                    "detail": "",
                }
            )
            continue
        if event.type == "approval_requested":
            request = event.payload.get("request")
            last_approval_request = request if isinstance(request, dict) else None
            continue
        if event.type == "approval_decision":
            failure = approval_failure_entry(event, request=last_approval_request, max_text=max_text)
            if failure is not None:
                failures.append(failure)
            continue
        if event.type == "model_error":
            failures.append(model_error_failure_entry(event, max_text=max_text))
            continue
        if event.type == "result":
            failure = result_failure_entry(event, max_text=max_text)
            if failure is not None:
                failures.append(failure)
            continue
        if event.type != "tool_result":
            continue
        result = event.payload.get("result")
        if not isinstance(result, dict) or not session_failure_result_failed(result):
            continue
        failures.extend(tool_result_failure_entries(event, result, max_text=max_text))
    return failures


def approval_failure_entry(
    event: SessionEvent,
    request: dict[str, Any] | None,
    max_text: int,
) -> dict[str, str | int] | None:
    decision = event.payload.get("decision")
    if not isinstance(decision, dict) or decision.get("approved") is not False:
        return None
    message = decision.get("message")
    detail = approval_request_failure_detail(request, max_text=max_text)
    return {
        "line_number": event.line_number,
        "type": "approval",
        "name": "denied",
        "message": compact(message, max_text) if isinstance(message, str) and message.strip() else "Approval denied.",
        "detail": detail,
    }


def approval_request_failure_detail(request: dict[str, Any] | None, max_text: int) -> str:
    if not isinstance(request, dict):
        return ""
    parts = []
    action_type = request.get("action_type")
    target = request.get("target")
    preview = request.get("preview")
    if isinstance(action_type, str) and action_type.strip():
        parts.append(f"action={compact(action_type, max_text)}")
    if isinstance(target, str) and target.strip():
        parts.append(f"target={compact(target, max_text)}")
    if isinstance(preview, str) and preview.strip():
        parts.append(f"preview={compact(preview, max_text)}")
    return "; ".join(parts)


def model_error_failure_entry(event: SessionEvent, max_text: int) -> dict[str, str | int]:
    error_type = event.payload.get("error_type")
    message = event.payload.get("message")
    iteration = event.payload.get("iteration")
    attempt = event.payload.get("attempt")
    attempts = event.payload.get("attempts")
    will_retry = event.payload.get("will_retry")
    details = []
    if isinstance(iteration, int):
        details.append(f"iteration={iteration}")
    if isinstance(attempt, int) and isinstance(attempts, int):
        details.append(f"attempt={attempt}/{attempts}")
    if isinstance(will_retry, bool):
        details.append(f"willRetry={'yes' if will_retry else 'no'}")
    return {
        "line_number": event.line_number,
        "type": "model_error",
        "name": compact(error_type, max_text) if isinstance(error_type, str) and error_type.strip() else "provider",
        "message": compact(message, max_text) if isinstance(message, str) and message.strip() else "Model request failed.",
        "detail": "; ".join(details),
    }


def result_failure_entry(event: SessionEvent, max_text: int) -> dict[str, str | int] | None:
    success = event.payload.get("success")
    status = event.payload.get("status")
    completion_ready = event.payload.get("completion_ready")
    if success is not False and status not in {"failed", "blocked"} and completion_ready is not False:
        return None
    message = event.payload.get("message")
    blockers = event.payload.get("completion_blockers")
    detail = result_failure_detail(blockers, max_text=max_text)
    fallback_status = "blocked" if completion_ready is False else "failed"
    return {
        "line_number": event.line_number,
        "type": "result",
        "name": str(status) if isinstance(status, str) and status.strip() else fallback_status,
        "message": compact(message, max_text) if isinstance(message, str) and message.strip() else result_failure_message(success, completion_ready),
        "detail": detail,
    }


def result_failure_message(success: object, completion_ready: object) -> str:
    if success is True and completion_ready is False:
        return "Agent run finished before completion was ready."
    return "Agent run failed."


def result_failure_detail(blockers: object, max_text: int) -> str:
    if not isinstance(blockers, list):
        return ""
    clean_blockers = [item for item in blockers if isinstance(item, str) and item.strip()]
    if not clean_blockers:
        return ""
    return "completionBlockers=" + compact("; ".join(clean_blockers), max_text)


def tool_result_failure_entries(event: SessionEvent, result: dict[str, Any], max_text: int) -> list[dict[str, str | int]]:
    kind = result.get("kind")
    name = event.payload.get("name") if isinstance(event.payload.get("name"), str) else kind
    if kind == "run_command":
        command_result = result.get("result")
        if isinstance(command_result, dict):
            return [command_failure_entry(event.line_number, str(name or kind), command_result, max_text)]
    if kind in {"run_commands", "run_suggested_checks", "run_focused_test_commands"}:
        entries = []
        command_results = result.get("results")
        if isinstance(command_results, list):
            for index, command_result in enumerate(command_results, start=1):
                if isinstance(command_result, dict) and command_result_failed(command_result):
                    entries.append(command_failure_entry(event.line_number, f"{name or kind}[{index}]", command_result, max_text))
        if entries:
            return entries
    message = result.get("message")
    return [
        {
            "line_number": event.line_number,
            "type": "tool_result",
            "name": str(name or "unknown"),
            "message": compact(message, max_text) if isinstance(message, str) and message.strip() else "Tool result failed.",
            "detail": "",
        }
    ]


def command_failure_entry(line_number: int, name: str, command_result: dict[str, Any], max_text: int) -> dict[str, str | int]:
    command = command_result.get("command")
    exit_code = command_result.get("exit_code")
    timed_out = command_result.get("timed_out")
    stderr = command_result.get("stderr")
    detail_parts = [
        f"exit={exit_code if isinstance(exit_code, int) else 'unknown'}",
        f"timedOut={'yes' if timed_out is True else 'no'}",
    ]
    return {
        "line_number": line_number,
        "type": "command",
        "name": name,
        "message": compact(command, max_text) if isinstance(command, str) and command.strip() else "Command failed.",
        "detail": "; ".join(detail_parts + ([f"stderr={compact(stderr, max_text)}"] if isinstance(stderr, str) and stderr.strip() else [])),
    }


def command_result_failed(command_result: dict[str, Any]) -> bool:
    return command_result.get("exit_code") != 0 or command_result.get("timed_out") is True


def session_failure_result_failed(result: dict[str, Any]) -> bool:
    if result.get("ok") is False:
        return True
    return is_failed_tool_result(result)
