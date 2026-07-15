from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shlex
import sys

from .actions import execute_action as _default_execute_action
from .output_serialization import serialize_output_context_result, serialize_output_diagnostic
from .process_report_helpers import (
    format_process_output_contexts_report_text,
    format_process_output_diagnostics_report_text,
    process_status_text,
)
from .types import ProcessOutputContextsAction, ProcessOutputDiagnosticsAction
from .workspace_core import RunWorkspace


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.process_commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def _process_command_function(name: str, default: Callable[..., object]) -> Callable[..., object]:
    commands_module = sys.modules.get("vibeagent.process_commands")
    candidate = getattr(commands_module, name, None) if commands_module is not None else None
    return candidate if callable(candidate) else default


def get_process_output_contexts_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    max_output_chars: int | None = None,
    context_lines: int = 5,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    get_report = _process_command_function("get_process_output_contexts_report", get_process_output_contexts_report)
    format_report = _process_command_function(
        "format_process_output_contexts_report_text",
        format_process_output_contexts_report_text,
    )
    return format_report(
        get_report(
            project_root,
            argument,
            process_id,
            max_output_chars,
            context_lines,
            max_contexts,
            max_bytes_per_context,
        )
    )


def get_process_output_contexts_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    max_output_chars: int | None = None,
    context_lines: int = 5,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        selected_process_id, selected_max = parse_process_request(argument, process_id, max_output_chars)
    except ValueError as error:
        return _process_output_contexts_usage_report(
            root,
            process_id or "",
            max_output_chars,
            f"Usage: /process-output-contexts <id> [chars]\nError: {error}",
        )
    message = _validate_process_output_context_limits(
        context_lines=context_lines,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
    )
    if message:
        return _process_output_contexts_usage_report(root, selected_process_id, selected_max, message)

    workspace = RunWorkspace(root=root, run_id="local-process-output-contexts", session_dir=root / ".vibeagent" / "sessions" / "local-process-output-contexts")
    observation = _execute_action(
        workspace,
        ProcessOutputContextsAction(
            type="process_output_contexts",
            process_id=selected_process_id,
            max_output_chars=selected_max,
            context_lines=context_lines,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )
    if observation.kind != "process_output_contexts":
        return _process_output_contexts_usage_report(
            root,
            selected_process_id,
            selected_max,
            f"Unexpected observation: {observation.kind}",
        )

    items = [serialize_output_context_result(item) for item in observation.contexts]
    ok_count = sum(1 for item in items if item["ok"])
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "processId": observation.process_id,
        "pid": observation.pid,
        "status": process_status_text(observation.running, observation.exit_code, observation.signal),
        "running": observation.running,
        "exitCode": observation.exit_code,
        "signal": observation.signal,
        "contexts": {"ok": ok_count, "total": len(items), "items": items},
        "totalRefs": observation.total_refs,
        "maxOutputChars": observation.max_output_chars,
        "stdoutChars": observation.stdout_chars,
        "stderrChars": observation.stderr_chars,
        "truncated": observation.truncated,
        "message": observation.message,
    }


def get_process_output_diagnostics_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    max_output_chars: int | None = None,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    get_report = _process_command_function("get_process_output_diagnostics_report", get_process_output_diagnostics_report)
    format_report = _process_command_function(
        "format_process_output_diagnostics_report_text",
        format_process_output_diagnostics_report_text,
    )
    return format_report(
        get_report(
            project_root,
            argument,
            process_id,
            max_output_chars,
            context_lines,
            max_diagnostics,
            max_contexts,
            max_bytes_per_context,
        )
    )


def get_process_output_diagnostics_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    max_output_chars: int | None = None,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        selected_process_id, selected_max = parse_process_request(argument, process_id, max_output_chars)
    except ValueError as error:
        return _process_output_diagnostics_usage_report(
            root,
            process_id or "",
            max_output_chars,
            context_lines,
            max_diagnostics,
            max_contexts,
            max_bytes_per_context,
            f"Usage: /process-output-diagnostics <id> [chars]\nError: {error}",
        )
    message = _validate_process_output_diagnostic_limits(
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
    )
    if message:
        return _process_output_diagnostics_usage_report(
            root,
            selected_process_id,
            selected_max,
            context_lines,
            max_diagnostics,
            max_contexts,
            max_bytes_per_context,
            message,
        )

    workspace = RunWorkspace(root=root, run_id="local-process-output-diagnostics", session_dir=root / ".vibeagent" / "sessions" / "local-process-output-diagnostics")
    observation = _execute_action(
        workspace,
        ProcessOutputDiagnosticsAction(
            type="process_output_diagnostics",
            process_id=selected_process_id,
            max_output_chars=selected_max,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )
    if observation.kind != "process_output_diagnostics":
        return _process_output_diagnostics_usage_report(
            root,
            selected_process_id,
            selected_max,
            context_lines,
            max_diagnostics,
            max_contexts,
            max_bytes_per_context,
            f"Unexpected observation: {observation.kind}",
        )

    diagnostics = [serialize_output_diagnostic(item) for item in observation.diagnostics]
    contexts = [serialize_output_context_result(item) for item in observation.contexts]
    ok_count = sum(1 for item in contexts if item["ok"])
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "processId": observation.process_id,
        "pid": observation.pid,
        "status": process_status_text(observation.running, observation.exit_code, observation.signal),
        "running": observation.running,
        "exitCode": observation.exit_code,
        "signal": observation.signal,
        "diagnostics": {"shown": len(diagnostics), "total": observation.total_diagnostics, "items": diagnostics},
        "contexts": {"ok": ok_count, "total": len(contexts), "items": contexts},
        "totalRefs": observation.total_refs,
        "maxOutputChars": observation.max_output_chars,
        "stdoutChars": observation.stdout_chars,
        "stderrChars": observation.stderr_chars,
        "contextLines": context_lines,
        "maxDiagnostics": max_diagnostics,
        "maxContexts": max_contexts,
        "maxBytesPerContext": max_bytes_per_context,
        "diagnosticsTruncated": observation.diagnostics_truncated,
        "contextsTruncated": observation.contexts_truncated,
        "message": observation.message,
    }


def parse_process_request(
    argument: str | None = None,
    process_id: str | None = None,
    max_output_chars: int | None = None,
) -> tuple[str, int | None]:
    selected_process_id = process_id.strip() if process_id else None
    selected_max = max_output_chars
    if argument and argument.strip():
        if process_id is not None:
            raise ValueError("process argument cannot be combined with explicit process_id.")
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if len(parts) > 2:
            raise ValueError("expected process id and optional max chars.")
        if parts:
            selected_process_id = parts[0]
        if len(parts) == 2:
            if not parts[1].isdigit():
                raise ValueError(f"invalid max chars: {parts[1]}")
            selected_max = int(parts[1])
    if not selected_process_id:
        raise ValueError("process id is required.")
    if selected_max is not None and selected_max < 1_000:
        raise ValueError("max chars must be at least 1000.")
    if selected_max is not None and selected_max > 50_000:
        raise ValueError("max chars must be at most 50000.")
    return selected_process_id, selected_max


def _validate_process_output_context_limits(
    *,
    context_lines: int,
    max_contexts: int,
    max_bytes_per_context: int,
) -> str:
    usage = "Usage: /process-output-contexts <id> [chars]\nError:"
    if context_lines < 0:
        return f"{usage} context_lines must be at least 0."
    if context_lines > 500:
        return f"{usage} context_lines must be at most 500."
    if max_contexts < 1:
        return f"{usage} max_contexts must be at least 1."
    if max_contexts > 100:
        return f"{usage} max_contexts must be at most 100."
    if max_bytes_per_context < 1_000:
        return f"{usage} max_bytes_per_context must be at least 1000."
    if max_bytes_per_context > 200_000:
        return f"{usage} max_bytes_per_context must be at most 200000."
    return ""


def _validate_process_output_diagnostic_limits(
    *,
    context_lines: int,
    max_diagnostics: int,
    max_contexts: int,
    max_bytes_per_context: int,
) -> str:
    usage = "Usage: /process-output-diagnostics <id> [chars]\nError:"
    if context_lines < 0:
        return f"{usage} context_lines must be at least 0."
    if context_lines > 500:
        return f"{usage} context_lines must be at most 500."
    if max_diagnostics < 1:
        return f"{usage} max_diagnostics must be at least 1."
    if max_diagnostics > 200:
        return f"{usage} max_diagnostics must be at most 200."
    if max_contexts < 1:
        return f"{usage} max_contexts must be at least 1."
    if max_contexts > 100:
        return f"{usage} max_contexts must be at most 100."
    if max_bytes_per_context < 1_000:
        return f"{usage} max_bytes_per_context must be at least 1000."
    if max_bytes_per_context > 200_000:
        return f"{usage} max_bytes_per_context must be at most 200000."
    return ""


def _process_output_contexts_usage_report(
    root: Path,
    process_id: str,
    max_output_chars: int | None,
    message: str,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "processId": process_id,
        "pid": None,
        "status": "unknown",
        "contexts": {"ok": 0, "total": 0, "items": []},
        "totalRefs": 0,
        "maxOutputChars": max_output_chars,
        "stdoutChars": 0,
        "stderrChars": 0,
        "truncated": False,
        "message": message,
    }


def _process_output_diagnostics_usage_report(
    root: Path,
    process_id: str,
    max_output_chars: int | None,
    context_lines: int,
    max_diagnostics: int,
    max_contexts: int,
    max_bytes_per_context: int,
    message: str,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "processId": process_id,
        "pid": None,
        "status": "unknown",
        "diagnostics": {"shown": 0, "total": 0, "items": []},
        "contexts": {"ok": 0, "total": 0, "items": []},
        "totalRefs": 0,
        "maxOutputChars": max_output_chars,
        "stdoutChars": 0,
        "stderrChars": 0,
        "contextLines": context_lines,
        "maxDiagnostics": max_diagnostics,
        "maxContexts": max_contexts,
        "maxBytesPerContext": max_bytes_per_context,
        "diagnosticsTruncated": False,
        "contextsTruncated": False,
        "message": message,
    }
