from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .session import summarize_session
from .session_id import is_valid_session_id
from .session_readiness_commands import get_resume_context as _get_resume_context
from .session_rewind import (
    SessionRewindCheck,
    check_session_rewind,
    list_session_rewind_points,
    rewind_session,
)


ResumeContextLoader = Callable[..., tuple[str | None, str | None, str]]
MAX_SESSION_REWIND_POINTS = 100


def get_session_rewind_points_report(
    project_root: str | Path,
    run_id: str,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    error = _session_error(root, run_id)
    if error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "exists": False,
            "session": run_id,
            "total": 0,
            "truncated": False,
            "points": [],
            "message": error,
        }
    points = list_session_rewind_points(root, run_id)
    shown = points[:MAX_SESSION_REWIND_POINTS]
    return {
        "projectRoot": str(root),
        "ok": True,
        "exists": True,
        "session": run_id,
        "total": len(points),
        "truncated": len(points) > len(shown),
        "points": [
            {
                "checkpointId": point.checkpoint_id,
                "label": point.label,
                "createdAt": point.created_at,
                "eventLine": point.event_line,
            }
            for point in shown
        ],
        "message": f"Found {len(points)} rewind point(s) for session {run_id}.",
    }


def get_check_session_rewind_report(
    project_root: str | Path,
    run_id: str,
    checkpoint_id: str,
    mode: str,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    error = _session_error(root, run_id)
    if error:
        return _empty_check_report(root, run_id, checkpoint_id, mode, error)
    check = check_session_rewind(root, run_id, checkpoint_id, mode)
    return _serialize_check(root, run_id, check)


def get_session_rewind_report(
    project_root: str | Path,
    run_id: str,
    checkpoint_id: str,
    mode: str,
    *,
    get_resume_context_fn: ResumeContextLoader = _get_resume_context,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    error = _session_error(root, run_id)
    if error:
        return _empty_rewind_report(root, run_id, checkpoint_id, mode, error)
    result = rewind_session(
        root,
        run_id,
        checkpoint_id,
        mode,  # type: ignore[arg-type]
        get_resume_context=lambda target: get_resume_context_fn(target, root),
    )
    return {
        "projectRoot": str(root),
        "ok": result.error is None and result.changed,
        "rewound": result.error is None and result.changed,
        "changed": result.changed,
        "sourceSession": run_id,
        "newSession": result.workspace.run_id if result.workspace is not None else None,
        "checkpointId": result.checkpoint_id or checkpoint_id,
        "mode": mode,
        "codeRestored": result.error is None and result.changed and mode in {"code", "both"},
        "conversationBranched": result.workspace is not None and mode in {"conversation", "both"},
        "message": result.text,
        "error": result.error,
    }


def format_session_rewind_points_report_text(report: dict[str, object]) -> str:
    if not bool(report.get("ok")):
        return str(report.get("message") or "Session rewind points are unavailable.")
    points = report.get("points") if isinstance(report.get("points"), list) else []
    lines = [
        "Session rewind points:",
        f"  ok: yes",
        f"  session: {report.get('session')}",
        f"  total: {report.get('total', 0)}",
    ]
    if bool(report.get("truncated")):
        lines.append(f"  shown: {len(points)} newest points")
    if not points:
        lines.append("  points: none")
        return "\n".join(lines)
    lines.append("  points:")
    for point in points:
        if not isinstance(point, dict):
            continue
        label = f" label={point.get('label')}" if point.get("label") else ""
        lines.append(
            f"    - {point.get('checkpointId')} created={point.get('createdAt')}"
            f"{label} eventLine={point.get('eventLine')}"
        )
    return "\n".join(lines)


def format_check_session_rewind_report_text(report: dict[str, object]) -> str:
    lines = [
        "Check session rewind:",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  canRewind: {'yes' if bool(report.get('canRewind')) else 'no'}",
        f"  session: {report.get('session')}",
        f"  checkpointId: {report.get('checkpointId')}",
        f"  mode: {report.get('mode')}",
        f"  eventLine: {report.get('eventLine', 0)}",
        f"  codeWillChange: {'yes' if bool(report.get('codeWillChange')) else 'no'}",
        f"  conversationWillBranch: {'yes' if bool(report.get('conversationWillBranch')) else 'no'}",
        f"  message: {report.get('message')}",
    ]
    return "\n".join(lines)


def format_session_rewind_report_text(report: dict[str, object]) -> str:
    return "\n".join(
        [
            "Session rewind:",
            f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
            f"  rewound: {'yes' if bool(report.get('rewound')) else 'no'}",
            f"  sourceSession: {report.get('sourceSession')}",
            f"  newSession: {report.get('newSession') or ''}",
            f"  checkpointId: {report.get('checkpointId')}",
            f"  mode: {report.get('mode')}",
            f"  codeRestored: {'yes' if bool(report.get('codeRestored')) else 'no'}",
            f"  conversationBranched: {'yes' if bool(report.get('conversationBranched')) else 'no'}",
            f"  message: {report.get('message')}",
        ]
    )


def _serialize_check(root: Path, run_id: str, check: SessionRewindCheck) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": check.can_rewind,
        "canRewind": check.can_rewind,
        "session": run_id,
        "checkpointId": check.checkpoint_id,
        "mode": check.mode,
        "eventLine": check.event_line,
        "codeWillChange": check.code_will_change,
        "conversationWillBranch": check.conversation_will_branch,
        "restorePreview": check.restore_preview,
        "message": "Session rewind preflight passed." if check.can_rewind else check.error,
        "error": check.error,
    }


def _empty_check_report(root: Path, run_id: str, checkpoint_id: str, mode: str, error: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "canRewind": False,
        "session": run_id,
        "checkpointId": checkpoint_id,
        "mode": mode,
        "eventLine": 0,
        "codeWillChange": mode in {"code", "both"},
        "conversationWillBranch": mode in {"conversation", "both"},
        "restorePreview": None,
        "message": error,
        "error": error,
    }


def _empty_rewind_report(root: Path, run_id: str, checkpoint_id: str, mode: str, error: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "rewound": False,
        "changed": False,
        "sourceSession": run_id,
        "newSession": None,
        "checkpointId": checkpoint_id,
        "mode": mode,
        "codeRestored": False,
        "conversationBranched": False,
        "message": error,
        "error": error,
    }


def _session_error(root: Path, run_id: str) -> str | None:
    if not is_valid_session_id(run_id):
        return f"Invalid session id: {run_id}"
    try:
        summary = summarize_session(root, run_id)
    except ValueError as error:
        return str(error)
    if not summary.exists:
        return f"Session not found: {run_id}"
    return None


__all__ = [
    "format_check_session_rewind_report_text",
    "format_session_rewind_points_report_text",
    "format_session_rewind_report_text",
    "get_check_session_rewind_report",
    "get_session_rewind_points_report",
    "get_session_rewind_report",
]
