from __future__ import annotations

from . import __version__


def get_status_report(
    mode: str,
    approval_policy: str,
    resume_run_id: str | None = None,
    chat_turns: int = 0,
    system_prompt_set: bool = False,
    append_system_prompt_set: bool = False,
) -> dict[str, object]:
    return {
        "version": __version__,
        "mode": mode,
        "approval": approval_policy,
        "resume": resume_run_id or "",
        "chatTurns": chat_turns,
        "systemPrompt": "custom" if system_prompt_set else "default",
        "appendSystemPrompt": "set" if append_system_prompt_set else "none",
        "message": "Runtime status resolved.",
    }


def format_status_report_text(report: dict[str, object]) -> str:
    resume = str(report.get("resume") or "none")
    return "\n".join(
        [
            "Status:",
            f"  version: {report.get('version') or ''}",
            f"  mode: {report.get('mode') or ''}",
            f"  approval: {report.get('approval') or ''}",
            f"  resume: {resume}",
            f"  chatTurns: {int(report.get('chatTurns', 0) or 0)}",
            f"  systemPrompt: {report.get('systemPrompt') or 'default'}",
            f"  appendSystemPrompt: {report.get('appendSystemPrompt') or 'none'}",
        ]
    )


def get_status_text(
    mode: str,
    approval_policy: str,
    resume_run_id: str | None = None,
    chat_turns: int = 0,
    system_prompt_set: bool = False,
    append_system_prompt_set: bool = False,
) -> str:
    return format_status_report_text(
        get_status_report(
            mode,
            approval_policy,
            resume_run_id,
            chat_turns,
            system_prompt_set=system_prompt_set,
            append_system_prompt_set=append_system_prompt_set,
        )
    )
