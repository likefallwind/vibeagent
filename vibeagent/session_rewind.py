from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from .agent_runtime_utils import append_session_event
from .checkpoint_storage import read_checkpoint_infos, read_checkpoint_metadata
from .session_additional_directories import restore_session_additional_directories
from .session_store import read_session_events
from .workspace_core import RunWorkspace, create_run_workspace
from .workflow_checkpoint_restore_commands import (
    get_check_checkpoint_restore_report,
    get_checkpoint_restore_report,
)


RewindMode = Literal["both", "code", "conversation"]
MAX_REWIND_EVENTS = 10_000
_SKIPPED_LINEAGE_EVENTS = {"session_named", "session_branched", "session_rewound"}


@dataclass(frozen=True)
class SessionRewindPoint:
    checkpoint_id: str
    label: str
    created_at: str
    event_line: int


@dataclass(frozen=True)
class SessionRewindResult:
    text: str
    workspace: RunWorkspace | None = None
    context: str | None = None
    changed: bool = False
    error: str | None = None


def list_session_rewind_points(project_root: Path, run_id: str) -> tuple[SessionRewindPoint, ...]:
    root = project_root.resolve()
    points: list[SessionRewindPoint] = []
    for info in read_checkpoint_infos(root):
        metadata, _ = read_checkpoint_metadata(root, info.checkpoint_id)
        if metadata is None or metadata.get("session_run_id") != run_id:
            continue
        event_line = metadata.get("session_event_line")
        if isinstance(event_line, bool) or not isinstance(event_line, int) or event_line < 1:
            continue
        points.append(SessionRewindPoint(info.checkpoint_id, info.label, info.created_at, event_line))
    return tuple(points)


def format_session_rewind_points(project_root: Path, run_id: str | None) -> str:
    if run_id is None:
        return "Rewind error: no active coding session."
    points = list_session_rewind_points(project_root, run_id)
    lines = [f"Rewind points for session {run_id}:", f"  total: {len(points)}"]
    if not points:
        lines.append("  items: none")
        return "\n".join(lines)
    lines.append("  items:")
    for point in points:
        label = f" label={point.label}" if point.label else ""
        lines.append(
            f"    - {point.checkpoint_id} created={point.created_at}{label} eventLine={point.event_line}"
        )
    return "\n".join(lines)


def rewind_session(
    project_root: Path,
    run_id: str | None,
    checkpoint_id: str,
    mode: RewindMode,
    *,
    get_resume_context: Callable[..., tuple[str | None, str | None, str]],
) -> SessionRewindResult:
    root = project_root.resolve()
    if run_id is None:
        return _error("No active coding session.")
    points = list_session_rewind_points(root, run_id)
    selected = points[0].checkpoint_id if checkpoint_id == "latest" and points else checkpoint_id
    metadata, message = read_checkpoint_metadata(root, selected)
    if metadata is None:
        return _error(message)
    if metadata.get("session_run_id") != run_id:
        return _error(f"Checkpoint {selected} does not belong to active session {run_id}.")
    event_line = metadata.get("session_event_line")
    if isinstance(event_line, bool) or not isinstance(event_line, int) or event_line < 1:
        return _error(f"Checkpoint {selected} has no valid session event boundary.")
    if event_line > MAX_REWIND_EVENTS:
        return _error(f"Checkpoint boundary exceeds the {MAX_REWIND_EVENTS}-event rewind limit.")

    source_events = []
    if mode in {"conversation", "both"}:
        try:
            source_events = read_session_events(root, run_id)
        except (OSError, ValueError) as error:
            return _error(str(error))
        if not source_events or event_line > max(event.line_number for event in source_events):
            return _error(f"Checkpoint {selected} points beyond the current session transcript.")

    if mode in {"code", "both"}:
        preview = get_check_checkpoint_restore_report(selected, root)
        if not bool(preview.get("ok")) or not bool(preview.get("canRestore")):
            return _error(str(preview.get("message") or f"Cannot restore checkpoint {selected}."))
        restored = get_checkpoint_restore_report(selected, root)
        if not bool(restored.get("ok")) or not bool(restored.get("restored")):
            return _error(str(restored.get("message") or f"Failed to restore checkpoint {selected}."))
        if mode == "code":
            return SessionRewindResult(
                text=f"Restored code from checkpoint {selected}; conversation remains on session {run_id}.",
                changed=True,
            )

    restored_directories = restore_session_additional_directories(root, run_id)
    try:
        target = create_run_workspace(root, additional_roots=restored_directories.directories)
        copied = 0
        malformed = 0
        for event in source_events:
            if event.line_number > event_line:
                break
            if event.malformed:
                malformed += 1
                continue
            if event.type in _SKIPPED_LINEAGE_EVENTS:
                continue
            append_session_event(target.session_dir, event.type, dict(event.payload))
            copied += 1
        append_session_event(
            target.session_dir,
            "session_rewound",
            {
                "source_run_id": run_id,
                "checkpoint_id": selected,
                "source_event_line": event_line,
                "mode": mode,
                "copied_events": copied,
                "malformed_events_skipped": malformed,
            },
        )
        selected_run_id, context, context_message = get_resume_context(target.run_id)
    except (OSError, ValueError) as error:
        return _error(f"Failed to create rewound session: {error}")
    if selected_run_id != target.run_id or context is None:
        return _error(context_message)

    warning_parts = list(restored_directories.warnings)
    if malformed:
        warning_parts.append(f"skipped {malformed} malformed source event(s)")
    lines = [
        f"Rewound {mode} to checkpoint {selected}.",
        f"  sourceSession: {run_id}",
        f"  newSession: {target.run_id}",
        f"  copiedEvents: {copied}",
    ]
    if warning_parts:
        lines.append("  warnings: " + "; ".join(warning_parts))
    return SessionRewindResult("\n".join(lines), target, context, True)


def _error(message: str) -> SessionRewindResult:
    return SessionRewindResult(text=f"Rewind error: {message}", error=message)


__all__ = [
    "MAX_REWIND_EVENTS",
    "SessionRewindPoint",
    "SessionRewindResult",
    "format_session_rewind_points",
    "list_session_rewind_points",
    "rewind_session",
]
