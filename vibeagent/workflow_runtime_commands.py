from __future__ import annotations

from .command_hard_blocks import blocked_command_examples, get_command_hard_block_report
from .workflow_context_commands import format_context_report_text, get_context_report, get_context_text
from .workflow_doctor_commands import format_doctor_report_text, get_doctor_report, get_doctor_text
from .workflow_init_commands import (
    build_project_instructions_template,
    format_init_report_text,
    get_init_report,
    init_project_instructions,
    normalize_project_instructions_file_name,
)


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
