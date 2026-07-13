from __future__ import annotations

from .output_conversion import output_context_results_from_dicts, output_diagnostics_from_dicts
from .process_io_runtime import read_background_process
from .types import (
    ProcessOutputContextsAction,
    ProcessOutputContextsObservation,
    ProcessOutputDiagnosticsAction,
    ProcessOutputDiagnosticsObservation,
)
from .workspace import read_output_contexts_result, read_output_diagnostics_result
from .workspace_core import RunWorkspace


def read_background_process_output_contexts(
    workspace: RunWorkspace,
    action: ProcessOutputContextsAction,
) -> ProcessOutputContextsObservation:
    process = read_background_process(
        workspace.root,
        action.process_id,
        max_output_chars=action.max_output_chars,
    )
    if not process.ok:
        return ProcessOutputContextsObservation(
            kind="process_output_contexts",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=False,
            exit_code=process.exit_code,
            signal=process.signal,
            contexts=[],
            total_refs=0,
            truncated=False,
            stdout_chars=0,
            stderr_chars=0,
            max_output_chars=action.max_output_chars,
            message=process.message,
        )

    text = "\n".join(part for part in [process.stdout, process.stderr] if part)
    if not text.strip():
        return ProcessOutputContextsObservation(
            kind="process_output_contexts",
            process_id=action.process_id,
            pid=process.pid,
            ok=True,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            contexts=[],
            total_refs=0,
            truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=f"Process {action.process_id} output contained no file:line references.",
        )

    try:
        result = read_output_contexts_result(
            workspace,
            text,
            context_lines=action.context_lines,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
    except ValueError as error:
        return ProcessOutputContextsObservation(
            kind="process_output_contexts",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            contexts=[],
            total_refs=0,
            truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=str(error),
        )

    contexts = output_context_results_from_dicts(result["contexts"])
    total_refs = int(result["total_refs"])
    return ProcessOutputContextsObservation(
        kind="process_output_contexts",
        process_id=action.process_id,
        pid=process.pid,
        ok=True,
        running=process.running,
        exit_code=process.exit_code,
        signal=process.signal,
        contexts=contexts,
        total_refs=total_refs,
        truncated=bool(result["truncated"]),
        stdout_chars=len(process.stdout),
        stderr_chars=len(process.stderr),
        max_output_chars=action.max_output_chars,
        message=f"Extracted {len(contexts)}/{total_refs} output context(s) from process {action.process_id}.",
    )


def read_background_process_output_diagnostics(
    workspace: RunWorkspace,
    action: ProcessOutputDiagnosticsAction,
) -> ProcessOutputDiagnosticsObservation:
    process = read_background_process(
        workspace.root,
        action.process_id,
        max_output_chars=action.max_output_chars,
    )
    if not process.ok:
        return ProcessOutputDiagnosticsObservation(
            kind="process_output_diagnostics",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=False,
            exit_code=process.exit_code,
            signal=process.signal,
            diagnostics=[],
            contexts=[],
            total_diagnostics=0,
            total_refs=0,
            diagnostics_truncated=False,
            contexts_truncated=False,
            stdout_chars=0,
            stderr_chars=0,
            max_output_chars=action.max_output_chars,
            message=process.message,
        )

    text = "\n".join(part for part in [process.stdout, process.stderr] if part)
    if not text.strip():
        return ProcessOutputDiagnosticsObservation(
            kind="process_output_diagnostics",
            process_id=action.process_id,
            pid=process.pid,
            ok=True,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            diagnostics=[],
            contexts=[],
            total_diagnostics=0,
            total_refs=0,
            diagnostics_truncated=False,
            contexts_truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=f"Process {action.process_id} output contained no diagnostic lines.",
        )

    try:
        result = read_output_diagnostics_result(
            workspace,
            text,
            context_lines=action.context_lines,
            max_diagnostics=action.max_diagnostics,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
    except ValueError as error:
        return ProcessOutputDiagnosticsObservation(
            kind="process_output_diagnostics",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            diagnostics=[],
            contexts=[],
            total_diagnostics=0,
            total_refs=0,
            diagnostics_truncated=False,
            contexts_truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=str(error),
        )

    diagnostics = output_diagnostics_from_dicts(result["diagnostics"])
    contexts = output_context_results_from_dicts(result["contexts"])
    total_diagnostics = int(result["total_diagnostics"])
    total_refs = int(result["total_refs"])
    return ProcessOutputDiagnosticsObservation(
        kind="process_output_diagnostics",
        process_id=action.process_id,
        pid=process.pid,
        ok=True,
        running=process.running,
        exit_code=process.exit_code,
        signal=process.signal,
        diagnostics=diagnostics,
        contexts=contexts,
        total_diagnostics=total_diagnostics,
        total_refs=total_refs,
        diagnostics_truncated=bool(result["diagnostics_truncated"]),
        contexts_truncated=bool(result["contexts_truncated"]),
        stdout_chars=len(process.stdout),
        stderr_chars=len(process.stderr),
        max_output_chars=action.max_output_chars,
        message=(
            f"Extracted {len(diagnostics)}/{total_diagnostics} diagnostic(s) "
            f"and {len(contexts)}/{total_refs} source context(s) from process {action.process_id}."
        ),
    )
