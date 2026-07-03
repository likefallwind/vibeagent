from __future__ import annotations

from typing import Any

from .session_types import SessionSummary
from .session_utils import compact


def validate_session_verification_limit(max_checks: int) -> None:
    if max_checks < 1:
        raise ValueError("max_checks must be at least 1.")
    if max_checks > 500:
        raise ValueError("max_checks must be at most 500.")


def validate_session_verification_report_limits(max_checks: int, max_text: int) -> None:
    validate_session_verification_limit(max_checks)
    if max_text < 80:
        raise ValueError("max_text must be at least 80.")
    if max_text > 5000:
        raise ValueError("max_text must be at most 5000.")


def format_session_verification_summary(summary: SessionSummary, max_checks: int = 50) -> str:
    if not summary.exists:
        return f"Session not found: {summary.run_id}"
    validate_session_verification_limit(max_checks)

    def add_check_group(lines: list[str], label: str, checks: list[str]) -> bool:
        shown = checks[:max_checks]
        truncated = len(checks) > len(shown)
        if shown:
            lines.append(f"  {label}: {len(shown)}/{len(checks)}")
            lines.extend(f"    - {compact(check, 160)}" for check in shown)
        else:
            lines.append(f"  {label}: none")
        return truncated

    lines = ["Session verification:"]
    truncated = any(
        (
            add_check_group(lines, "verified", summary.verification_checks),
            add_check_group(lines, "pendingChecks", summary.pending_verification_checks),
            add_check_group(lines, "failedChecks", summary.failed_verification_checks),
        )
    )
    lines.append(f"  truncated: {'yes' if truncated else 'no'}")
    return "\n".join(lines)


def build_session_verification_report_from_summary(
    summary: SessionSummary,
    max_checks: int = 50,
    max_text: int = 160,
) -> dict[str, Any]:
    verified = limited_string_group(summary.verification_checks, max_checks, max_text, status="verified")
    pending = limited_string_group(summary.pending_verification_checks, max_checks, max_text, status="pending")
    failed = limited_string_group(summary.failed_verification_checks, max_checks, max_text, status="failed")
    ok = pending["total"] == 0 and failed["total"] == 0
    truncated = bool(verified["truncated"] or pending["truncated"] or failed["truncated"])
    return {
        "session": summary.run_id,
        "exists": True,
        "ok": ok,
        "ready": ok,
        "status": "ready" if ok else "blocked",
        "verified": verified,
        "pending": pending,
        "failed": failed,
        "truncated": truncated,
        "message": "All verification checks are complete." if ok else "Verification checks are pending or failed.",
    }


def limited_string_group(items: list[str], limit: int, max_text: int, status: str | None = None) -> dict[str, Any]:
    shown = items[:limit]
    group: dict[str, Any] = {
        "total": len(items),
        "shown": len(shown),
        "truncated": len(items) > len(shown),
        "items": [compact(item, max_text) for item in shown],
    }
    if status is not None:
        group["commands"] = [
            parse_verification_check_label(item, status=status, max_text=max_text)
            for item in shown
        ]
    return group


def parse_verification_check_label(label: str, *, status: str, max_text: int) -> dict[str, Any]:
    body = label
    failure_reason: str | None = None
    if status == "failed" and body.endswith(")") and " (" in body:
        prefix, suffix = body.rsplit(" (", 1)
        reason = suffix[:-1]
        if reason == "timed out" or reason == "no exit code" or reason.startswith("exit="):
            body = prefix
            failure_reason = reason

    command = body
    cwd = "."
    if body.endswith(")") and " (cwd: " in body:
        prefix, suffix = body.rsplit(" (cwd: ", 1)
        cwd = suffix[:-1] or "."
        command = prefix

    item: dict[str, Any] = {
        "status": status,
        "command": compact(command, max_text),
        "cwd": compact(cwd, max_text),
        "label": compact(label, max_text),
    }
    if failure_reason is not None:
        item["failureReason"] = compact(failure_reason, max_text)
    return item
