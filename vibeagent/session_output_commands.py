from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .local_command_workspace import local_command_workspace
from .output_serialization import serialize_output_context_result, serialize_output_diagnostic
from .session import get_last_session_id
from .session_input import normalize_optional_run_id
from .session_output_formatting import (
    format_output_context_item_text as _format_output_context_item_text,
    format_session_output_contexts_report_text,
    format_session_output_diagnostics_report_text,
    indent_block as _indent_block,
)
from .types import SessionOutputContextsAction, SessionOutputDiagnosticsAction


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
    workspace = local_command_workspace(root, "local-session-output-contexts")
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
    workspace = local_command_workspace(root, "local-session-output-diagnostics")
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
