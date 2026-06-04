from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SessionEvent:
    type: str
    payload: dict[str, Any]
    line_number: int
    raw: dict[str, Any] | None = None
    malformed: bool = False
    error: str | None = None


@dataclass(frozen=True)
class SessionInfo:
    run_id: str
    event_count: int
    malformed_count: int
    last_event_time: datetime | None


@dataclass(frozen=True)
class SessionSummary:
    run_id: str
    exists: bool
    event_count: int
    malformed_count: int
    iterations: int
    tool_calls: list[str]
    approvals_requested: int
    approvals_approved: int
    approvals_denied: int
    final_message: str | None
    completed: bool
    failed: bool


def list_sessions(project_root: str | Path, limit: int = 20) -> list[SessionInfo]:
    sessions_root = sessions_dir(project_root)
    if not sessions_root.is_dir():
        return []

    infos = [read_session_info(path) for path in sessions_root.iterdir() if path.is_dir()]
    infos.sort(key=lambda info: info.last_event_time or datetime.min.replace(tzinfo=UTC), reverse=True)
    return infos[:limit]


def read_session_events(project_root: str | Path, run_id: str) -> list[SessionEvent]:
    return read_events_file(events_path(project_root, run_id))


def summarize_session(project_root: str | Path, run_id: str) -> SessionSummary:
    session_path = session_dir(project_root, run_id)
    events = read_session_events(project_root, run_id)
    valid_events = [event for event in events if not event.malformed]
    malformed_count = len(events) - len(valid_events)
    iterations = max((as_int(event.payload.get("iteration")) or 0 for event in valid_events), default=0)

    tool_calls: list[str] = []
    approvals_requested = 0
    approvals_approved = 0
    approvals_denied = 0
    final_message: str | None = None
    completed = False
    failed = False

    for event in valid_events:
        if event.type == "tool_call":
            name = event.payload.get("name")
            if isinstance(name, str):
                tool_calls.append(name)
        elif event.type == "approval_requested":
            approvals_requested += 1
        elif event.type == "approval_decision":
            decision = event.payload.get("decision")
            approved = decision.get("approved") if isinstance(decision, dict) else None
            if approved is True:
                approvals_approved += 1
            elif approved is False:
                approvals_denied += 1
        elif event.type == "model":
            text = model_text(event.payload.get("content"))
            has_tool_call = has_tool_call_content(event.payload.get("content"))
            if text and not has_tool_call:
                final_message = text
                completed = True
        elif event.type == "tool_result":
            result = event.payload.get("result")
            if isinstance(result, dict):
                kind = result.get("kind")
                if kind == "finish" and isinstance(result.get("message"), str):
                    final_message = result["message"]
                    completed = True
                if is_failed_tool_result(result):
                    failed = True
        elif event.type == "step_completed":
            step = event.payload.get("step")
            status = step.get("status") if isinstance(step, dict) else None
            if status in {"failed", "denied"}:
                failed = True

    return SessionSummary(
        run_id=run_id,
        exists=session_path.is_dir(),
        event_count=len(valid_events),
        malformed_count=malformed_count,
        iterations=iterations,
        tool_calls=tool_calls,
        approvals_requested=approvals_requested,
        approvals_approved=approvals_approved,
        approvals_denied=approvals_denied,
        final_message=final_message,
        completed=completed,
        failed=failed or (session_path.is_dir() and bool(valid_events) and not completed),
    )


def format_sessions(project_root: str | Path, limit: int = 20) -> str:
    sessions = list_sessions(project_root, limit=limit)
    if not sessions:
        return "No sessions found."
    lines = ["Recent sessions:"]
    for info in sessions:
        last = (
            info.last_event_time.isoformat(timespec="seconds").replace("+00:00", "Z")
            if info.last_event_time
            else "unknown"
        )
        malformed = f", {info.malformed_count} malformed" if info.malformed_count else ""
        lines.append(f"  {info.run_id}  events={info.event_count}{malformed}  last={last}")
    return "\n".join(lines)


def format_session_summary(summary: SessionSummary) -> str:
    if not summary.exists:
        return f"Session not found: {summary.run_id}"

    tool_counts = count_names(summary.tool_calls)
    tools = ", ".join(f"{name} x{count}" if count > 1 else name for name, count in tool_counts.items())
    status = "completed" if summary.completed else "failed" if summary.failed else "incomplete"
    lines = [
        f"Session: {summary.run_id}",
        f"  status: {status}",
        f"  events: {summary.event_count}",
        f"  iterations: {summary.iterations}",
        f"  tools: {tools or 'none'}",
        (
            "  approvals: "
            f"{summary.approvals_requested} requested, "
            f"{summary.approvals_approved} approved, "
            f"{summary.approvals_denied} denied"
        ),
    ]
    if summary.malformed_count:
        lines.append(f"  malformedRows: {summary.malformed_count}")
    if summary.final_message:
        lines.append(f"  final: {compact(summary.final_message, 240)}")
    return "\n".join(lines)


def get_last_session_id(project_root: str | Path) -> str | None:
    sessions = list_sessions(project_root, limit=1)
    return sessions[0].run_id if sessions else None


def read_session_info(path: Path) -> SessionInfo:
    events = path / "events.jsonl"
    parsed_events = read_events_file(events)
    event_count = len([event for event in parsed_events if not event.malformed])
    malformed_count = len(parsed_events) - event_count
    if events.exists():
        last_event_time = datetime.fromtimestamp(events.stat().st_mtime, tz=UTC)
    else:
        last_event_time = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return SessionInfo(
        run_id=path.name,
        event_count=event_count,
        malformed_count=malformed_count,
        last_event_time=last_event_time,
    )


def read_events_file(path: Path) -> list[SessionEvent]:
    if not path.is_file():
        return []
    events: list[SessionEvent] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as error:
            events.append(
                SessionEvent(
                    type="malformed",
                    payload={},
                    line_number=line_number,
                    malformed=True,
                    error=f"Invalid JSON: {error.msg}",
                )
            )
            continue
        if not isinstance(parsed, dict) or not isinstance(parsed.get("type"), str):
            events.append(
                SessionEvent(
                    type="malformed",
                    payload={},
                    line_number=line_number,
                    malformed=True,
                    error="Event row must be an object with a string type.",
                )
            )
            continue
        events.append(
            SessionEvent(
                type=parsed["type"],
                payload={key: value for key, value in parsed.items() if key != "type"},
                line_number=line_number,
                raw=parsed,
            )
        )
    return events


def sessions_dir(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / ".vibeagent" / "sessions"


def session_dir(project_root: str | Path, run_id: str) -> Path:
    if not run_id or Path(run_id).name != run_id:
        raise ValueError(f"Invalid session id: {run_id}")
    return sessions_dir(project_root) / run_id


def events_path(project_root: str | Path, run_id: str) -> Path:
    return session_dir(project_root, run_id) / "events.jsonl"


def as_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def model_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    return "".join(
        block["text"]
        for block in content
        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
    ).strip()


def has_tool_call_content(content: Any) -> bool:
    return isinstance(content, list) and any(
        isinstance(block, dict) and block.get("type") == "tool_call" for block in content
    )


def is_failed_tool_result(result: dict[str, Any]) -> bool:
    kind = result.get("kind")
    if kind in {"tool_error", "approval_denied"}:
        return True
    if kind in {"write_file", "edit_file"}:
        return result.get("ok") is False
    if kind == "run_command":
        command_result = result.get("result")
        if not isinstance(command_result, dict):
            return True
        return command_result.get("exit_code") != 0 or command_result.get("timed_out") is True
    return False


def count_names(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def compact(value: str, max_length: int) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) <= max_length:
        return collapsed
    return f"{collapsed[:max_length]}..."
