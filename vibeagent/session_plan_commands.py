from __future__ import annotations

from pathlib import Path

from .session import build_session_plan_report, get_last_session_id, summarize_session
from .session_input import normalize_optional_run_id
from .session_summary_formatting import clip as _clip


def get_plan_text(project_root: str | Path = ".", run_id: str | None = None) -> str:
    return format_session_plan_report_text(get_plan_report(project_root, run_id))


def get_plan_report(project_root: str | Path = ".", run_id: str | None = None) -> dict[str, object]:
    selected = normalize_optional_run_id(run_id) or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_plan_report(summarize_session(project_root, selected))
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": str(error),
        }


def format_session_plan_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    lines = [
        "Plan:",
        f"  session: {session}",
        f"  status: {report.get('status') or 'unknown'}",
    ]
    if report.get("task"):
        lines.append(f"  task: {_clip(str(report.get('task')), 240)}")
    items = [item for item in report.get("items", []) if isinstance(item, dict)] if isinstance(report.get("items"), list) else []
    if items:
        lines.append("  items:")
        lines.extend(f"    - {_format_plan_item_line(item, max_step=200)}" for item in items)
    else:
        lines.append("  items: none")
    return "\n".join(lines)


def _format_plan_item_line(item: dict[str, object], *, max_step: int) -> str:
    text = f"{item.get('status')}: {_clip(str(item.get('step') or ''), max_step)}"
    active_form = item.get("activeForm")
    if isinstance(active_form, str) and active_form.strip():
        text += f" (activeForm: {_clip(active_form, 120)})"
    return text
