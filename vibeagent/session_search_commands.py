from __future__ import annotations

from pathlib import Path
import shlex

from .session import build_session_search_report, get_last_session_id
from .session_input import normalize_optional_run_id

SESSION_SEARCH_USAGE = "Usage: /session-search [--run run-id] <query>"


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
    selected = normalize_optional_run_id(run_id)
    if not argument or not argument.strip():
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": SESSION_SEARCH_USAGE,
        }
    query = argument.strip()
    if selected is None:
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            return {
                "session": None,
                "exists": False,
                "ok": False,
                "status": "invalid",
                "message": str(error),
            }
        if len(parts) >= 3 and parts[0] == "--run":
            selected = normalize_optional_run_id(parts[1])
            query = " ".join(parts[2:]).strip()
        else:
            query = argument.strip()
    selected = selected or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "query": query,
            "caseSensitive": case_sensitive,
            "message": "No sessions found.",
        }
    try:
        return build_session_search_report(
            project_root,
            selected,
            query,
            max_matches=max_matches,
            max_text=max_text,
            case_sensitive=case_sensitive,
        )
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "query": query,
            "caseSensitive": case_sensitive,
            "message": str(error),
        }


def format_session_search_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    matches = report.get("matches") if isinstance(report.get("matches"), dict) else {}
    total = int(matches.get("total", 0) or 0)
    shown = int(matches.get("shown", 0) or 0)
    omitted = int(matches.get("omitted", 0) or 0)
    lines = [
        "Session search:",
        f"  session: {session}",
        f"  query: {report.get('query') or ''}",
        f"  matches: {total}",
        f"  shown: {shown}/{total}",
        f"  caseSensitive: {'yes' if bool(report.get('caseSensitive')) else 'no'}",
        "  timeline:",
    ]
    items = [item for item in matches.get("items", []) if isinstance(item, dict)] if isinstance(matches.get("items"), list) else []
    if items:
        lines.extend(str(item.get("summary") or "    - unknown") for item in items)
    else:
        lines.append("    - none")
    if omitted > 0:
        lines.append(f"    - [{omitted} later match(es) omitted]")
    return "\n".join(lines)
