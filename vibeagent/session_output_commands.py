from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .output_serialization import serialize_output_context_result, serialize_output_diagnostic
from .session import get_last_session_id
from .session_input import normalize_optional_run_id
from .types import SessionOutputContextsAction, SessionOutputDiagnosticsAction
from .workspace_core import RunWorkspace


def _indent_block(value: str, spaces: int = 2) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in value.splitlines())


def get_session_output_contexts_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 20_000,
    context_lines: int = 5,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    return format_session_output_contexts_report_text(
        get_session_output_contexts_report(
            project_root,
            run_id,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
            context_lines=context_lines,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )
    )


def get_session_output_contexts_observation(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 20_000,
    context_lines: int = 5,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
):
    selected = normalize_optional_run_id(run_id) or get_last_session_id(project_root)
    if not selected:
        return None
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-session-output-contexts", session_dir=root / ".vibeagent" / "sessions" / "local-session-output-contexts")
    return execute_action(
        workspace,
        SessionOutputContextsAction(
            type="session_output_contexts",
            run_id=selected,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
            context_lines=context_lines,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )


def get_session_output_contexts_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 20_000,
    context_lines: int = 5,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    selected = normalize_optional_run_id(run_id) or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    observation = get_session_output_contexts_observation(
        project_root,
        selected,
        max_commands=max_commands,
        max_output_chars=max_output_chars,
        context_lines=context_lines,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
    )
    if observation is None:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    if observation.kind != "session_output_contexts":
        return {
            "session": selected,
            "exists": True,
            "ok": False,
            "status": "invalid",
            "message": f"Unexpected observation: {observation.kind}",
        }

    ok_contexts = sum(1 for item in observation.contexts if item.ok)
    exists = not observation.message.startswith("Session not found:")
    return {
        "session": observation.run_id,
        "exists": exists,
        "ok": observation.ok,
        "status": "ready" if observation.ok else ("failed" if exists else "missing"),
        "commands": {
            "total": observation.command_count,
            "shown": observation.shown_commands,
        },
        "contexts": {
            "total": len(observation.contexts),
            "ok": ok_contexts,
            "failed": len(observation.contexts) - ok_contexts,
            "totalRefs": observation.total_refs,
            "truncated": observation.truncated,
            "items": [serialize_output_context_result(item) for item in observation.contexts],
        },
        "message": observation.message,
    }


def format_session_output_contexts_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    contexts = report.get("contexts") if isinstance(report.get("contexts"), dict) else {}
    items = [item for item in contexts.get("items", []) if isinstance(item, dict)] if isinstance(contexts.get("items"), list) else []
    lines = [
        "Session output contexts:",
        f"  session: {session}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  commands: {int(commands.get('shown', 0) or 0)}/{int(commands.get('total', 0) or 0)}",
        f"  contexts: {int(contexts.get('ok', 0) or 0)}/{int(contexts.get('total', 0) or 0)}",
        f"  totalRefs: {int(contexts.get('totalRefs', 0) or 0)}",
        f"  truncated: {'yes' if bool(contexts.get('truncated')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]
    for item in items:
        lines.extend(_format_output_context_item_text(item))
    return "\n".join(lines)


def _format_output_context_item_text(item: dict[str, object]) -> list[str]:
    column = f":{item.get('column')}" if item.get("column") is not None else ""
    total_lines = item.get("totalLines") if item.get("totalLines") is not None else "unknown"
    lines = [
        "",
        f"Context: {item.get('path') or ''}:{item.get('line')}{column}",
        f"  raw: {item.get('raw') or ''}",
        f"  ok: {'yes' if bool(item.get('ok')) else 'no'}",
        f"  range: {item.get('startLine')}:{item.get('endLine')}",
        f"  contextLines: {item.get('contextLines')}",
        f"  targetLineExists: {'yes' if bool(item.get('targetLineExists')) else 'no'}",
        f"  lines: {item.get('lineCount')}/{total_lines}",
        f"  maxBytes: {item.get('maxBytes')}",
        f"  truncated: {'yes' if bool(item.get('truncated')) else 'no'}",
        f"  message: {item.get('message') or ''}",
    ]
    content = item.get("content") if isinstance(item.get("content"), str) else ""
    if content:
        lines.append("  content:")
        lines.append(_indent_block(content.rstrip("\n"), spaces=4))
    else:
        lines.append("  content: none")
    return lines


def get_session_output_diagnostics_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 20_000,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    return format_session_output_diagnostics_report_text(
        get_session_output_diagnostics_report(
            project_root,
            run_id,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )
    )


def format_session_output_diagnostics_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    diagnostics = report.get("diagnostics") if isinstance(report.get("diagnostics"), dict) else {}
    contexts = report.get("contexts") if isinstance(report.get("contexts"), dict) else {}
    diagnostic_items = [item for item in diagnostics.get("items", []) if isinstance(item, dict)] if isinstance(diagnostics.get("items"), list) else []
    context_items = [item for item in contexts.get("items", []) if isinstance(item, dict)] if isinstance(contexts.get("items"), list) else []
    lines = [
        "Session output diagnostics:",
        f"  session: {session}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  commands: {int(commands.get('shown', 0) or 0)}/{int(commands.get('total', 0) or 0)}",
        f"  diagnostics: {int(diagnostics.get('shown', 0) or 0)}/{int(diagnostics.get('total', 0) or 0)}",
        f"  contexts: {int(contexts.get('ok', 0) or 0)}/{int(contexts.get('total', 0) or 0)}",
        f"  totalRefs: {int(contexts.get('totalRefs', 0) or 0)}",
        f"  diagnosticsTruncated: {'yes' if bool(diagnostics.get('truncated')) else 'no'}",
        f"  contextsTruncated: {'yes' if bool(contexts.get('truncated')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]
    for diagnostic in diagnostic_items:
        location = ""
        if diagnostic.get("path") and diagnostic.get("line") is not None:
            column = f":{diagnostic.get('column')}" if diagnostic.get("column") is not None else ""
            location = f" {diagnostic.get('path')}:{diagnostic.get('line')}{column}"
        lines.append(
            f"  - {diagnostic.get('severity')} outputLine={diagnostic.get('outputLine')}{location}: {diagnostic.get('text') or ''}"
        )
    for item in context_items:
        lines.extend(_format_output_context_item_text(item))
    return "\n".join(lines)


def get_session_output_diagnostics_observation(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 20_000,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
):
    selected = normalize_optional_run_id(run_id) or get_last_session_id(project_root)
    if not selected:
        return None
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-session-output-diagnostics", session_dir=root / ".vibeagent" / "sessions" / "local-session-output-diagnostics")
    return execute_action(
        workspace,
        SessionOutputDiagnosticsAction(
            type="session_output_diagnostics",
            run_id=selected,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )


def get_session_output_diagnostics_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 20_000,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    selected = normalize_optional_run_id(run_id) or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    observation = get_session_output_diagnostics_observation(
        project_root,
        selected,
        max_commands=max_commands,
        max_output_chars=max_output_chars,
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
    )
    if observation is None:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    if observation.kind != "session_output_diagnostics":
        return {
            "session": selected,
            "exists": True,
            "ok": False,
            "status": "invalid",
            "message": f"Unexpected observation: {observation.kind}",
        }

    ok_contexts = sum(1 for item in observation.contexts if item.ok)
    exists = not observation.message.startswith("Session not found:")
    return {
        "session": observation.run_id,
        "exists": exists,
        "ok": observation.ok,
        "status": "ready" if observation.ok else ("failed" if exists else "missing"),
        "commands": {
            "total": observation.command_count,
            "shown": observation.shown_commands,
        },
        "diagnostics": {
            "total": observation.total_diagnostics,
            "shown": len(observation.diagnostics),
            "truncated": observation.diagnostics_truncated,
            "items": [serialize_output_diagnostic(item) for item in observation.diagnostics],
        },
        "contexts": {
            "total": len(observation.contexts),
            "ok": ok_contexts,
            "failed": len(observation.contexts) - ok_contexts,
            "totalRefs": observation.total_refs,
            "truncated": observation.contexts_truncated,
            "items": [serialize_output_context_result(item) for item in observation.contexts],
        },
        "message": observation.message,
    }
