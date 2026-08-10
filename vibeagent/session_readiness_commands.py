from __future__ import annotations

from pathlib import Path

from .session import build_session_audit_report, build_session_handoff_report, build_session_resume_context, get_last_session_id
from .session_input import normalize_optional_run_id
from .session_branching import resolve_session_reference


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
        return _missing_readiness_report()
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
        return _invalid_readiness_report(selected, error)


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
        return _missing_readiness_report()
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
        return _invalid_readiness_report(selected, error)


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


def _missing_readiness_report() -> dict[str, object]:
    return {
        "session": None,
        "exists": False,
        "ok": False,
        "ready": False,
        "status": "missing",
        "message": "No sessions found.",
    }


def _invalid_readiness_report(session_id: str, error: ValueError) -> dict[str, object]:
    return {
        "session": session_id,
        "exists": False,
        "ok": False,
        "ready": False,
        "status": "invalid",
        "message": str(error),
    }


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
        selected = resolve_session_reference(Path(project_root), selected)
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
