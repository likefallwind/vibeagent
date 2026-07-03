from __future__ import annotations


def get_status_report(mode: str, approval_policy: str, resume_run_id: str | None = None, chat_turns: int = 0) -> dict[str, object]:
    return {
        "mode": mode,
        "approval": approval_policy,
        "resume": resume_run_id or "",
        "chatTurns": chat_turns,
        "message": "Runtime status resolved.",
    }


def format_status_report_text(report: dict[str, object]) -> str:
    resume = str(report.get("resume") or "none")
    return "\n".join(
        [
            "Status:",
            f"  mode: {report.get('mode') or ''}",
            f"  approval: {report.get('approval') or ''}",
            f"  resume: {resume}",
            f"  chatTurns: {int(report.get('chatTurns', 0) or 0)}",
        ]
    )


def get_status_text(mode: str, approval_policy: str, resume_run_id: str | None = None, chat_turns: int = 0) -> str:
    return format_status_report_text(get_status_report(mode, approval_policy, resume_run_id, chat_turns))
