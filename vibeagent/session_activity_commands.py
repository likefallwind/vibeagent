from __future__ import annotations

from pathlib import Path

from .session import get_last_session_id
from .session_event_report_commands import build_session_commands_report
from .session_failure_reports import build_session_failures_report
from .session_file_reports import build_session_files_report


def _missing_session_report() -> dict[str, object]:
    return {
        "session": None,
        "exists": False,
        "ok": False,
        "status": "missing",
        "message": "No sessions found.",
    }


def _invalid_session_report(session_id: str, error: ValueError) -> dict[str, object]:
    return {
        "session": session_id,
        "exists": False,
        "ok": False,
        "status": "invalid",
        "message": str(error),
    }


def get_session_commands_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 2_000,
) -> str:
    return format_session_commands_report_text(
        get_session_commands_report(
            project_root,
            run_id,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
        )
    )


def get_session_commands_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 2_000,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return _missing_session_report()
    try:
        return build_session_commands_report(
            project_root,
            selected,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
        )
    except ValueError as error:
        return _invalid_session_report(selected, error)


def format_session_commands_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    total = int(commands.get("total", 0) or 0)
    shown = int(commands.get("shown", 0) or 0)
    omitted = int(commands.get("omitted", 0) or 0)
    lines = [
        "Command results:",
        f"  session: {session}",
        f"  commands: {total}",
        f"  shown: {shown}/{total}",
        "  entries:",
    ]
    if omitted > 0:
        lines.append(f"    - [{omitted} older command result(s) omitted]")
    items = (
        [item for item in commands.get("items", []) if isinstance(item, dict)]
        if isinstance(commands.get("items"), list)
        else []
    )
    if not items:
        lines.append("    - none")
        return "\n".join(lines)
    for item in items:
        parts = [
            f"exit={item.get('exitCode') if isinstance(item.get('exitCode'), int) else 'unknown'}",
            f"timedOut={'yes' if bool(item.get('timedOut')) else 'no'}",
        ]
        if item.get("signal"):
            parts.append(f"signal={item.get('signal')}")
        if item.get("cwd"):
            parts.append(f"cwd={item.get('cwd')}")
        line_number = item.get("lineNumber") if item.get("lineNumber") is not None else "?"
        kind = item.get("kind") or "command"
        index = item.get("index") if item.get("index") is not None else "?"
        lines.append(f"    - #{line_number} {kind}[{index}]: " + ", ".join(parts))
        lines.append(f"      command: {item.get('command') or 'unknown'}")
        for label, text_key, truncated_key in (
            ("stdout", "stdout", "stdoutStoredTruncated"),
            ("stderr", "stderr", "stderrStoredTruncated"),
        ):
            suffix = " (stored truncated)" if bool(item.get(truncated_key)) else ""
            lines.append(f"      {label}{suffix}:")
            text = item.get(text_key) if isinstance(item.get(text_key), str) else ""
            if not text:
                lines.append("        (empty)")
            else:
                lines.extend(f"        {line}" for line in text.splitlines())
    return "\n".join(lines)


def get_session_files_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_files: int = 100,
) -> str:
    return format_session_files_report_text(get_session_files_report(project_root, run_id, max_files=max_files))


def get_session_files_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_files: int = 100,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return _missing_session_report()
    try:
        return build_session_files_report(project_root, selected, max_files=max_files)
    except ValueError as error:
        return _invalid_session_report(selected, error)


def format_session_files_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    total = int(files.get("total", 0) or 0)
    shown = int(files.get("shown", 0) or 0)
    omitted = int(files.get("omitted", 0) or 0)
    lines = [
        "Session files:",
        f"  session: {session}",
        f"  files: {total}",
        f"  shown: {shown}/{total}",
        "  entries:",
    ]
    items = (
        [item for item in files.get("items", []) if isinstance(item, dict)]
        if isinstance(files.get("items"), list)
        else []
    )
    if not items:
        lines.append("    - none")
        return "\n".join(lines)
    for item in items:
        tools = (
            ", ".join(str(tool) for tool in item.get("tools", []) if isinstance(tool, str))
            if isinstance(item.get("tools"), list)
            else ""
        )
        uses = (
            ", ".join(str(use) for use in item.get("uses", []) if isinstance(use, str))
            if isinstance(item.get("uses"), list)
            else ""
        )
        line_values = (
            [line for line in item.get("lines", []) if isinstance(line, int)]
            if isinstance(item.get("lines"), list)
            else []
        )
        line_numbers = ", ".join(f"#{line}" for line in line_values[:8])
        if len(line_values) > 8:
            line_numbers += f", +{len(line_values) - 8} more"
        lines.append(f"    - {item.get('path') or ''}")
        lines.append(f"      uses: {uses}")
        lines.append(f"      tools: {tools}")
        lines.append(f"      count: {int(item.get('count', 0) or 0)}")
        lines.append(f"      lines: {line_numbers}")
    if omitted > 0:
        lines.append(f"    - [{omitted} file(s) omitted]")
    return "\n".join(lines)


def get_session_failures_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 50,
    max_text: int = 500,
) -> str:
    return format_session_failures_report_text(
        get_session_failures_report(project_root, run_id, max_failures=max_failures, max_text=max_text)
    )


def get_session_failures_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 50,
    max_text: int = 500,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return _missing_session_report()
    try:
        return build_session_failures_report(
            project_root,
            selected,
            max_failures=max_failures,
            max_text=max_text,
        )
    except ValueError as error:
        return _invalid_session_report(selected, error)


def format_session_failures_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    failures = report.get("failures") if isinstance(report.get("failures"), dict) else {}
    total = int(failures.get("total", 0) or 0)
    shown = int(failures.get("shown", 0) or 0)
    omitted = int(failures.get("omitted", 0) or 0)
    lines = [
        "Session failures:",
        f"  session: {session}",
        f"  failures: {total}",
        f"  shown: {shown}/{total}",
        "  entries:",
    ]
    if omitted > 0:
        lines.append(f"    - [{omitted} older failure(s) omitted]")
    items = (
        [item for item in failures.get("items", []) if isinstance(item, dict)]
        if isinstance(failures.get("items"), list)
        else []
    )
    if not items:
        lines.append("    - none")
        return "\n".join(lines)
    for failure in items:
        lines.append(f"    - #{failure.get('lineNumber', '')} {failure.get('type') or ''}: {failure.get('name') or ''}")
        if failure.get("message"):
            lines.append(f"      message: {failure.get('message')}")
        if failure.get("detail"):
            lines.append(f"      detail: {failure.get('detail')}")
    return "\n".join(lines)
