from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .background_agent_types import BackgroundAgentView
from .background_agent_approval import BackgroundApproval


STATUS_GROUPS = (
    (
        "Needs attention",
        frozenset(
            {"needs-input", "approval-error", "attaching", "attached", "attachment-error"}
        ),
    ),
    ("Working", frozenset({"running"})),
    ("Stopped", frozenset({"stopped", "lost", "failed"})),
    ("Completed", frozenset({"completed"})),
)


def ordered_agent_views(
    views: Iterable[BackgroundAgentView],
) -> tuple[BackgroundAgentView, ...]:
    values = tuple(views)
    rank = {
        status: index
        for index, (_label, statuses) in enumerate(STATUS_GROUPS)
        for status in statuses
    }
    return tuple(
        sorted(
            values,
            key=lambda view: rank.get(view.status, len(STATUS_GROUPS)),
        )
    )


def render_agent_view(
    project_root: Path,
    views: Iterable[BackgroundAgentView],
    *,
    selected_id: str | None,
    pending_counts: dict[str, int],
    peek_stdout: str = "",
    peek_stderr: str = "",
    approval: BackgroundApproval | None = None,
    message: str = "",
    show_help: bool = False,
    width: int = 100,
    height: int = 30,
) -> list[str]:
    bounded_width = max(20, width)
    bounded_height = max(6, height)
    ordered = ordered_agent_views(views)
    lines = [
        _fit("VibeAgent Agent View", bounded_width),
        _fit(f"Project: {project_root}", bounded_width),
        "-" * bounded_width,
    ]
    if show_help:
        lines.extend(_help_lines())
    elif not ordered:
        lines.extend(["", "  No background agents. Press n to dispatch a task."])
    else:
        for label, statuses in STATUS_GROUPS:
            grouped = [view for view in ordered if view.status in statuses]
            if not grouped:
                continue
            lines.append(f"{label} ({len(grouped)})")
            for view in grouped:
                lines.append(
                    _render_row(
                        view,
                        selected=view.record.id == selected_id,
                        pending=pending_counts.get(view.record.id, 0),
                        width=bounded_width,
                    )
                )
        ungrouped = [
            view
            for view in ordered
            if all(view.status not in statuses for _label, statuses in STATUS_GROUPS)
        ]
        if ungrouped:
            lines.append(f"Other ({len(ungrouped)})")
            lines.extend(
                _render_row(
                    view,
                    selected=view.record.id == selected_id,
                    pending=pending_counts.get(view.record.id, 0),
                    width=bounded_width,
                )
                for view in ungrouped
            )

    key_help = (
        "q quit  ? help  Enter attach"
        if bounded_width < 60
        else (
            "Up/Down select  Space peek  Enter attach  n dispatch  m reply  "
            "y approve  A always  N deny  s stop  R respawn  x remove  ? help  q quit"
        )
    )
    footer = [
        "-" * bounded_width,
        _fit(key_help, bounded_width),
        _fit(message or "Auto-refreshing every 0.5s.", bounded_width),
    ]
    available = bounded_height - len(footer)
    if (
        not show_help
        and selected_id is not None
        and (approval is not None or peek_stdout or peek_stderr)
    ):
        peek_lines = (
            _render_approval(approval, bounded_width)
            if approval is not None
            else _render_peek(peek_stdout, peek_stderr, bounded_width)
        )
        peek_slots = min(8, len(peek_lines), max(0, available - 3))
        body_limit = available - peek_slots
        lines = lines[:body_limit]
        if peek_slots:
            lines.extend(peek_lines[-peek_slots:])
    else:
        lines = lines[:available]
    lines.extend(footer)
    return [_fit(line, bounded_width) for line in lines[:bounded_height]]


def _render_row(
    view: BackgroundAgentView,
    *,
    selected: bool,
    pending: int,
    width: int,
) -> str:
    record = view.record
    marker = ">" if selected else " "
    session = record.session_name or "."
    text = (
        f"{marker} {view.status:<16} {record.id}  pending={pending:<3} "
        f"{session}  {record.task_summary or '.'}"
    )
    return _fit(text, width)


def _render_peek(stdout: str, stderr: str, width: int) -> list[str]:
    lines = ["", "Recent output"]
    combined = []
    if stdout.strip():
        combined.extend(stdout.rstrip().splitlines())
    if stderr.strip():
        combined.append("[stderr]")
        combined.extend(stderr.rstrip().splitlines())
    if not combined:
        combined.append("(empty)")
    lines.extend(f"  {_fit(line, max(1, width - 2))}" for line in combined[-6:])
    return lines


def _render_approval(approval: BackgroundApproval, width: int) -> list[str]:
    lines = ["", f"Approval required: {approval.action_type}"]
    lines.append(f"  Target: {_fit(approval.target, max(1, width - 10))}")
    lines.append(f"  Risk: {_fit(approval.risk, max(1, width - 8))}")
    if approval.preview:
        lines.append(f"  Preview: {_fit(approval.preview, max(1, width - 11))}")
    lines.append("  Press y to approve once, A for this session, or N to deny.")
    return lines


def _help_lines() -> list[str]:
    return [
        "",
        "  Agent view keys",
        "  Up/Down or j/k   Move selection",
        "  Space            Toggle recent stdout/stderr",
        "  Enter or Right   Attach selected session",
        "  y / A / N        Approve once / session / deny pending action",
        "  n                 Dispatch a new background task",
        "  m                 Send a follow-up message",
        "  s / R             Stop / respawn selected session",
        "  x                 Remove a non-running session after confirmation",
        "  c                 Refresh now",
        "  q or Esc          Exit; background sessions keep running",
        "",
        "  Press ? again to close help.",
    ]


def _fit(value: str, width: int) -> str:
    sanitized = value.replace("\t", "    ").replace("\r", " ").replace("\n", " ")
    if len(sanitized) <= width:
        return sanitized
    if width <= 3:
        return sanitized[:width]
    return sanitized[: width - 3] + "..."


__all__ = ["ordered_agent_views", "render_agent_view"]
