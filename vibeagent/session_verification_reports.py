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
    verified = limited_string_group(summary.verification_checks, max_checks, max_text)
    pending = limited_string_group(summary.pending_verification_checks, max_checks, max_text)
    failed = limited_string_group(summary.failed_verification_checks, max_checks, max_text)
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


def limited_string_group(items: list[str], limit: int, max_text: int) -> dict[str, Any]:
    shown = items[:limit]
    return {
        "total": len(items),
        "shown": len(shown),
        "truncated": len(items) > len(shown),
        "items": [compact(item, max_text) for item in shown],
    }
