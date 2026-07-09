from __future__ import annotations

from .action_results import build_session_command_output_scan_text
from .output_conversion import output_context_results_from_dicts, output_diagnostics_from_dicts
from .session_action_helpers import select_session_run_id
from .types import (
    Observation,
    SessionOutputContextsAction,
    SessionOutputContextsObservation,
    SessionOutputDiagnosticsAction,
    SessionOutputDiagnosticsObservation,
)
from .workspace import RunWorkspace, read_output_contexts_result, read_output_diagnostics_result


def execute_session_output_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, SessionOutputContextsAction):
        return session_output_contexts_observation(workspace, action)
    if isinstance(action, SessionOutputDiagnosticsAction):
        return session_output_diagnostics_observation(workspace, action)
    return None


def session_output_contexts_observation(
    workspace: RunWorkspace,
    action: SessionOutputContextsAction,
) -> SessionOutputContextsObservation:
    run_id = select_session_run_id(action.run_id, workspace.run_id)
    try:
        ok, command_count, shown_commands, output_text, scan_message = build_session_command_output_scan_text(
            workspace,
            run_id,
            max_commands=action.max_commands,
            max_output_chars=action.max_output_chars,
        )
        if not ok:
            return SessionOutputContextsObservation(
                kind="session_output_contexts",
                run_id=run_id,
                ok=False,
                contexts=[],
                command_count=0,
                shown_commands=0,
                total_refs=0,
                truncated=False,
                message=scan_message,
            )
        if not output_text.strip():
            return SessionOutputContextsObservation(
                kind="session_output_contexts",
                run_id=run_id,
                ok=True,
                contexts=[],
                command_count=command_count,
                shown_commands=shown_commands,
                total_refs=0,
                truncated=False,
                message=f"{scan_message} No command output references found.",
            )
        result = read_output_contexts_result(
            workspace,
            output_text,
            context_lines=action.context_lines,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
        contexts = output_context_results_from_dicts(result["contexts"])
        failed_contexts = sum(1 for item in contexts if not item.ok)
        return SessionOutputContextsObservation(
            kind="session_output_contexts",
            run_id=run_id,
            ok=failed_contexts == 0,
            contexts=contexts,
            command_count=command_count,
            shown_commands=shown_commands,
            total_refs=int(result["total_refs"]),
            truncated=bool(result["truncated"]),
            message=f"{scan_message} {result['message']}",
        )
    except ValueError as error:
        return SessionOutputContextsObservation(
            kind="session_output_contexts",
            run_id=run_id,
            ok=False,
            contexts=[],
            command_count=0,
            shown_commands=0,
            total_refs=0,
            truncated=False,
            message=str(error),
        )


def session_output_diagnostics_observation(
    workspace: RunWorkspace,
    action: SessionOutputDiagnosticsAction,
) -> SessionOutputDiagnosticsObservation:
    run_id = select_session_run_id(action.run_id, workspace.run_id)
    try:
        ok, command_count, shown_commands, output_text, scan_message = build_session_command_output_scan_text(
            workspace,
            run_id,
            max_commands=action.max_commands,
            max_output_chars=action.max_output_chars,
        )
        if not ok:
            return SessionOutputDiagnosticsObservation(
                kind="session_output_diagnostics",
                run_id=run_id,
                ok=False,
                diagnostics=[],
                contexts=[],
                command_count=0,
                shown_commands=0,
                total_diagnostics=0,
                total_refs=0,
                diagnostics_truncated=False,
                contexts_truncated=False,
                message=scan_message,
            )
        if not output_text.strip():
            return SessionOutputDiagnosticsObservation(
                kind="session_output_diagnostics",
                run_id=run_id,
                ok=True,
                diagnostics=[],
                contexts=[],
                command_count=command_count,
                shown_commands=shown_commands,
                total_diagnostics=0,
                total_refs=0,
                diagnostics_truncated=False,
                contexts_truncated=False,
                message=f"{scan_message} No command output diagnostics found.",
            )
        result = read_output_diagnostics_result(
            workspace,
            output_text,
            context_lines=action.context_lines,
            max_diagnostics=action.max_diagnostics,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
        diagnostics = output_diagnostics_from_dicts(result["diagnostics"])
        contexts = output_context_results_from_dicts(result["contexts"])
        failed_contexts = sum(1 for item in contexts if not item.ok)
        return SessionOutputDiagnosticsObservation(
            kind="session_output_diagnostics",
            run_id=run_id,
            ok=failed_contexts == 0,
            diagnostics=diagnostics,
            contexts=contexts,
            command_count=command_count,
            shown_commands=shown_commands,
            total_diagnostics=int(result["total_diagnostics"]),
            total_refs=int(result["total_refs"]),
            diagnostics_truncated=bool(result["diagnostics_truncated"]),
            contexts_truncated=bool(result["contexts_truncated"]),
            message=f"{scan_message} {result['message']}",
        )
    except ValueError as error:
        return SessionOutputDiagnosticsObservation(
            kind="session_output_diagnostics",
            run_id=run_id,
            ok=False,
            diagnostics=[],
            contexts=[],
            command_count=0,
            shown_commands=0,
            total_diagnostics=0,
            total_refs=0,
            diagnostics_truncated=False,
            contexts_truncated=False,
            message=str(error),
        )
