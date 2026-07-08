from __future__ import annotations

from pathlib import Path

from .session import build_session_audit_report, build_session_handoff_report, build_session_resume_context, get_last_session_id
from .session_accounting_commands import (
    format_cost_report_text as _format_cost_report_text,
    format_sessions_report_text as _format_sessions_report_text,
    format_usage_report_text as _format_usage_report_text,
    get_cost_report as _get_cost_report,
    get_sessions_report as _get_sessions_report,
    get_usage_report as _get_usage_report,
)
from .session_activity_commands import (
    format_session_commands_report_text,
    format_session_failures_report_text,
    format_session_files_report_text,
    get_session_commands_report,
    get_session_commands_text,
    get_session_failures_report,
    get_session_failures_text,
    get_session_files_report,
    get_session_files_text,
)
from .session_audit_formatting import (
    format_session_audit_report_text as _format_session_audit_report_text,
    format_session_handoff_report_text as _format_session_handoff_report_text,
    format_session_verification_report_text as _format_session_verification_report_text,
)
from .session_summary_commands import (
    format_session_plan_report_text as _format_session_plan_report_text,
    format_session_search_report_text as _format_session_search_report_text,
    format_session_summary_report_text as _format_session_summary_report_text,
    format_session_transcript_report_text as _format_session_transcript_report_text,
    get_last_session_report as _get_last_session_report,
    get_plan_report as _get_plan_report,
    get_session_report as _get_session_report,
    get_session_search_report as _get_session_search_report,
    get_transcript_report as _get_transcript_report,
)
from .session_output_commands import (
    format_session_output_contexts_report_text,
    format_session_output_diagnostics_report_text,
    get_session_output_contexts_observation,
    get_session_output_contexts_report,
    get_session_output_contexts_text,
    get_session_output_diagnostics_observation,
    get_session_output_diagnostics_report,
    get_session_output_diagnostics_text,
)
from .session_verification_commands import (
    format_run_session_verification_report_text,
    get_run_session_verification_report,
    get_run_session_verification_text,
    get_session_verification_report,
    get_session_verification_text,
)
from .session_input import normalize_optional_run_id


def get_sessions_text(project_root: str | Path = ".") -> str:
    return format_sessions_report_text(get_sessions_report(project_root))


def get_sessions_report(project_root: str | Path = ".") -> dict[str, object]:
    return _get_sessions_report(project_root)


def format_sessions_report_text(report: dict[str, object]) -> str:
    return _format_sessions_report_text(report)


def get_usage_text(project_root: str | Path = ".") -> str:
    return format_usage_report_text(get_usage_report(project_root))


def get_usage_report(project_root: str | Path = ".") -> dict[str, object]:
    return _get_usage_report(project_root)


def format_usage_report_text(report: dict[str, object]) -> str:
    return _format_usage_report_text(report)


def get_cost_text(project_root: str | Path = ".", env: dict[str, str | None] | None = None) -> str:
    return format_cost_report_text(get_cost_report(project_root, env))


def get_cost_report(project_root: str | Path = ".", env: dict[str, str | None] | None = None) -> dict[str, object]:
    return _get_cost_report(project_root, env)


def format_cost_report_text(report: dict[str, object]) -> str:
    return _format_cost_report_text(report)


def get_session_text(run_id: str | None, project_root: str | Path = ".") -> str:
    return format_session_summary_report_text(get_session_report(run_id, project_root))


def get_session_report(run_id: str | None, project_root: str | Path = ".") -> dict[str, object]:
    return _get_session_report(run_id, project_root)


def format_session_summary_report_text(report: dict[str, object]) -> str:
    return _format_session_summary_report_text(report)


def get_last_session_text(project_root: str | Path = ".") -> str:
    return format_session_summary_report_text(get_last_session_report(project_root))


def get_last_session_report(project_root: str | Path = ".") -> dict[str, object]:
    return _get_last_session_report(project_root)


def get_plan_text(project_root: str | Path = ".", run_id: str | None = None) -> str:
    return format_session_plan_report_text(get_plan_report(project_root, run_id))


def get_plan_report(project_root: str | Path = ".", run_id: str | None = None) -> dict[str, object]:
    return _get_plan_report(project_root, run_id)


def format_session_plan_report_text(report: dict[str, object]) -> str:
    return _format_session_plan_report_text(report)


def get_transcript_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_events: int = 80,
    max_text: int = 500,
) -> str:
    return format_session_transcript_report_text(
        get_transcript_report(project_root, run_id, max_events=max_events, max_text=max_text)
    )


def get_transcript_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_events: int = 80,
    max_text: int = 500,
) -> dict[str, object]:
    return _get_transcript_report(project_root, run_id, max_events=max_events, max_text=max_text)


def format_session_transcript_report_text(report: dict[str, object]) -> str:
    return _format_session_transcript_report_text(report)


def get_session_search_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    run_id: str | None = None,
    max_matches: int = 20,
    max_text: int = 500,
    case_sensitive: bool = False,
) -> str:
    return format_session_search_report_text(
        get_session_search_report(
            project_root,
            argument,
            run_id,
            max_matches=max_matches,
            max_text=max_text,
            case_sensitive=case_sensitive,
        )
    )


def get_session_search_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    run_id: str | None = None,
    max_matches: int = 20,
    max_text: int = 500,
    case_sensitive: bool = False,
) -> dict[str, object]:
    return _get_session_search_report(
        project_root,
        argument,
        run_id,
        max_matches=max_matches,
        max_text=max_text,
        case_sensitive=case_sensitive,
    )


def format_session_search_report_text(report: dict[str, object]) -> str:
    return _format_session_search_report_text(report)


def format_session_verification_report_text(report: dict[str, object]) -> str:
    return _format_session_verification_report_text(report)


def get_session_audit_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 10,
    max_files: int = 20,
    max_commands: int = 10,
    max_checks: int = 50,
    max_text: int = 300,
) -> dict[str, object]:
    selected = normalize_optional_run_id(run_id) or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_audit_report(
            project_root,
            selected,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_text=max_text,
        )
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "invalid",
            "message": str(error),
        }


def get_session_audit_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 10,
    max_files: int = 20,
    max_commands: int = 10,
    max_checks: int = 50,
    max_text: int = 300,
) -> str:
    return format_session_audit_report_text(
        get_session_audit_report(
            project_root,
            run_id,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_text=max_text,
        )
    )


def format_session_audit_report_text(report: dict[str, object]) -> str:
    return _format_session_audit_report_text(report)


def get_session_handoff_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 20,
    max_files: int = 50,
    max_commands: int = 10,
    max_checks: int = 50,
    max_output_chars: int = 1_000,
    max_text: int = 500,
) -> str:
    return format_session_handoff_report_text(
        get_session_handoff_report(
            project_root,
            run_id,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_output_chars=max_output_chars,
            max_text=max_text,
        )
    )


def get_session_handoff_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 20,
    max_files: int = 50,
    max_commands: int = 10,
    max_checks: int = 50,
    max_output_chars: int = 1_000,
    max_text: int = 500,
) -> dict[str, object]:
    selected = normalize_optional_run_id(run_id) or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_handoff_report(
            project_root,
            selected,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_output_chars=max_output_chars,
            max_text=max_text,
        )
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "invalid",
            "message": str(error),
        }


def format_session_handoff_report_text(report: dict[str, object]) -> str:
    return _format_session_handoff_report_text(report)


def get_resume_context(
    run_id: str | None,
    project_root: str | Path = ".",
    max_failures: int = 20,
    max_files: int = 50,
    max_commands: int = 10,
    max_checks: int = 50,
    max_output_chars: int = 1_000,
    max_text: int = 500,
) -> tuple[str | None, str | None, str]:
    if run_id and run_id.strip().lower() in {"off", "clear", "none"}:
        return None, None, "Resume context cleared."
    return _load_session_context(
        run_id,
        project_root,
        success_label="Resume context",
        max_failures=max_failures,
        max_files=max_files,
        max_commands=max_commands,
        max_checks=max_checks,
        max_output_chars=max_output_chars,
        max_text=max_text,
    )


def get_compact_context(
    run_id: str | None,
    project_root: str | Path = ".",
    max_failures: int = 20,
    max_files: int = 50,
    max_commands: int = 10,
    max_checks: int = 50,
    max_output_chars: int = 1_000,
    max_text: int = 500,
) -> tuple[str | None, str | None, str]:
    return _load_session_context(
        run_id,
        project_root,
        success_label="Compacted context",
        max_failures=max_failures,
        max_files=max_files,
        max_commands=max_commands,
        max_checks=max_checks,
        max_output_chars=max_output_chars,
        max_text=max_text,
    )


def _load_session_context(
    run_id: str | None,
    project_root: str | Path,
    *,
    success_label: str,
    max_failures: int,
    max_files: int,
    max_commands: int,
    max_checks: int,
    max_output_chars: int,
    max_text: int,
) -> tuple[str | None, str | None, str]:
    selected = normalize_optional_run_id(run_id) or get_last_session_id(project_root)
    if not selected:
        return None, None, "No sessions found."
    try:
        context = build_session_resume_context(
            project_root,
            selected,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_output_chars=max_output_chars,
            max_text=max_text,
        )
    except ValueError as error:
        return None, None, str(error)
    return selected, context, f"{success_label} loaded from session {selected}."
