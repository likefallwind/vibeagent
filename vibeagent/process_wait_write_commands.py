from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shlex
import sys

from .actions import execute_action as _default_execute_action
from .output_serialization import serialize_output_context_result, serialize_output_diagnostic
from .types import CheckWriteProcessAction, WaitProcessAction, WriteProcessAction
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


def get_wait_process_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    timeout_ms: int = 5_000,
    max_output_chars: int = 4_000,
    stdout_contains: str | None = None,
    stderr_contains: str | None = None,
    regex: bool = False,
) -> str:
    get_report = _process_command_function("get_wait_process_report", get_wait_process_report)
    format_report = _process_command_function("format_wait_process_report_text", format_wait_process_report_text)
    return format_report(
        get_report(
            project_root,
            argument,
            process_id,
            timeout_ms,
            max_output_chars,
            stdout_contains,
            stderr_contains,
            regex,
        )
    )


def get_wait_process_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    timeout_ms: int = 5_000,
    max_output_chars: int = 4_000,
    stdout_contains: str | None = None,
    stderr_contains: str | None = None,
    regex: bool = False,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        selected_process_id, selected_timeout, selected_max = parse_wait_process_request(
            argument,
            process_id,
            timeout_ms,
            max_output_chars,
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": process_id or "",
            "pid": None,
            "status": "unknown",
            "running": False,
            "timedOut": False,
            "matched": False,
            "matchedStream": None,
            "matchedPattern": None,
            "timeoutMs": timeout_ms,
            "exitCode": None,
            "signal": None,
            "maxOutputChars": max_output_chars,
            "stdout": "",
            "stderr": "",
            "analysis": {"diagnostics": {"shown": 0, "total": 0, "items": []}, "diagnosticsTruncated": False, "contexts": {"shown": 0, "totalRefs": 0, "items": []}, "contextsTruncated": False},
            "message": f"Usage: /wait-process <id> [timeout-ms] [chars]\nError: {error}",
        }

    workspace = RunWorkspace(root=root, run_id="local-wait-process", session_dir=root / ".vibeagent" / "sessions" / "local-wait-process")
    observation = _execute_action(
        workspace,
        WaitProcessAction(
            type="wait_process",
            process_id=selected_process_id,
            timeout_ms=selected_timeout,
            stdout_contains=stdout_contains,
            stderr_contains=stderr_contains,
            regex=regex,
            max_output_chars=selected_max,
        ),
    )
    if observation.kind != "wait_process":
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": selected_process_id,
            "pid": None,
            "status": "unknown",
            "running": False,
            "timedOut": False,
            "matched": False,
            "matchedStream": None,
            "matchedPattern": None,
            "timeoutMs": selected_timeout,
            "exitCode": None,
            "signal": None,
            "maxOutputChars": selected_max,
            "stdout": "",
            "stderr": "",
            "analysis": {"diagnostics": {"shown": 0, "total": 0, "items": []}, "diagnosticsTruncated": False, "contexts": {"shown": 0, "totalRefs": 0, "items": []}, "contextsTruncated": False},
            "message": f"Unexpected observation: {observation.kind}",
        }

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "processId": observation.process_id,
        "pid": observation.pid,
        "status": process_status_text(observation.running, observation.exit_code, observation.signal),
        "running": observation.running,
        "timedOut": observation.timed_out,
        "matched": observation.matched,
        "matchedStream": observation.matched_stream,
        "matchedPattern": observation.matched_pattern,
        "timeoutMs": observation.timeout_ms,
        "exitCode": observation.exit_code,
        "signal": observation.signal,
        "maxOutputChars": observation.max_output_chars,
        "stdout": observation.stdout,
        "stderr": observation.stderr,
        "analysis": serialize_command_output_analysis(observation),
        "message": observation.message,
    }


def format_wait_process_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    analysis = report.get("analysis") if isinstance(report.get("analysis"), dict) else {}
    lines = [
        "Wait process:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  processId: {report.get('processId') or ''}",
        f"  pid: {report.get('pid') if report.get('pid') is not None else '.'}",
        f"  status: {report.get('status') or 'unknown'}",
        f"  timedOut: {'yes' if bool(report.get('timedOut')) else 'no'}",
        f"  matched: {'yes' if bool(report.get('matched')) else 'no'}",
        f"  matchedStream: {report.get('matchedStream') or '.'}",
        f"  matchedPattern: {report.get('matchedPattern') or '.'}",
        f"  timeoutMs: {report.get('timeoutMs', 0)}",
        f"  maxOutputChars: {report.get('maxOutputChars', 0)}",
        f"  message: {message}",
    ]
    stdout = str(report.get("stdout") or "")
    stderr = str(report.get("stderr") or "")
    if stdout:
        lines.append("  stdout:")
        lines.append(_indent_block(stdout.rstrip(), spaces=4))
    else:
        lines.append("  stdout: none")
    if stderr:
        lines.append("  stderr:")
        lines.append(_indent_block(stderr.rstrip(), spaces=4))
    else:
        lines.append("  stderr: none")
    lines.extend(format_structured_command_output_analysis_lines(analysis, spaces=2))
    return "\n".join(lines)


def parse_wait_process_request(
    argument: str | None = None,
    process_id: str | None = None,
    timeout_ms: int = 5_000,
    max_output_chars: int = 4_000,
) -> tuple[str, int, int]:
    selected_process_id = process_id.strip() if process_id else None
    selected_timeout = timeout_ms
    selected_max = max_output_chars
    if argument and argument.strip():
        if process_id is not None:
            raise ValueError("wait-process argument cannot be combined with explicit process_id.")
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if len(parts) > 3:
            raise ValueError("expected process id, optional timeout ms, and optional max chars.")
        if parts:
            selected_process_id = parts[0]
        if len(parts) >= 2:
            if not parts[1].isdigit():
                raise ValueError(f"invalid timeout ms: {parts[1]}")
            selected_timeout = int(parts[1])
        if len(parts) == 3:
            if not parts[2].isdigit():
                raise ValueError(f"invalid max chars: {parts[2]}")
            selected_max = int(parts[2])
    if not selected_process_id:
        raise ValueError("process id is required.")
    if selected_timeout < 100:
        raise ValueError("timeout ms must be at least 100.")
    if selected_timeout > 600_000:
        raise ValueError("timeout ms must be at most 600000.")
    if selected_max < 1_000:
        raise ValueError("max chars must be at least 1000.")
    if selected_max > 50_000:
        raise ValueError("max chars must be at most 50000.")
    return selected_process_id, selected_timeout, selected_max


def get_write_process_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    content: str | None = None,
) -> str:
    get_report = _process_command_function("get_write_process_report", get_write_process_report)
    format_report = _process_command_function("format_write_process_report_text", format_write_process_report_text)
    return format_report(get_report(project_root, argument, process_id, content))


def get_write_process_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    content: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        selected_process_id, selected_content = parse_write_process_request(argument, process_id, content)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": process_id or "",
            "pid": None,
            "running": False,
            "command": "",
            "cwd": "",
            "contentChars": len(content or ""),
            "message": f"Usage: /write-process <id> <text>\nError: {error}",
        }

    workspace = RunWorkspace(root=root, run_id="local-write-process", session_dir=root / ".vibeagent" / "sessions" / "local-write-process")
    observation = _execute_action(
        workspace,
        WriteProcessAction(type="write_process", process_id=selected_process_id, content=selected_content),
    )
    if observation.kind != "write_process":
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": selected_process_id,
            "pid": None,
            "running": False,
            "command": "",
            "cwd": "",
            "contentChars": len(selected_content),
            "message": f"Unexpected observation: {observation.kind}",
        }

    return serialize_write_process_report(root, observation)


def format_write_process_report_text(report: dict[str, object]) -> str:
    lines = [
        "Write process:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  processId: {report.get('processId') or ''}",
        f"  pid: {report.get('pid') if report.get('pid') is not None else '.'}",
        f"  running: {'yes' if bool(report.get('running')) else 'no'}",
        f"  command: {report.get('command') or '.'}",
        f"  cwd: {report.get('cwd') or '.'}",
        f"  contentChars: {int(report.get('contentChars', 0) or 0)}",
        f"  message: {report.get('message') or ''}",
    ]
    return "\n".join(lines)


def get_check_write_process_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    content: str | None = None,
) -> str:
    get_report = _process_command_function("get_check_write_process_report", get_check_write_process_report)
    format_report = _process_command_function("format_check_write_process_report_text", format_check_write_process_report_text)
    return format_report(get_report(project_root, argument, process_id, content))


def get_check_write_process_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    content: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        selected_process_id, selected_content = parse_write_process_request(argument, process_id, content)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": process_id or "",
            "pid": None,
            "running": False,
            "command": "",
            "cwd": "",
            "contentChars": len(content or ""),
            "message": f"Usage: /check-write-process <id> <text>\nError: {error}",
        }

    workspace = RunWorkspace(root=root, run_id="local-check-write-process", session_dir=root / ".vibeagent" / "sessions" / "local-check-write-process")
    observation = _execute_action(
        workspace,
        CheckWriteProcessAction(type="check_write_process", process_id=selected_process_id, content=selected_content),
    )
    if observation.kind != "check_write_process":
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": selected_process_id,
            "pid": None,
            "running": False,
            "command": "",
            "cwd": "",
            "contentChars": len(selected_content),
            "message": f"Unexpected observation: {observation.kind}",
        }

    return serialize_write_process_report(root, observation)


def format_check_write_process_report_text(report: dict[str, object]) -> str:
    lines = [
        "Check write process:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  processId: {report.get('processId') or ''}",
        f"  pid: {report.get('pid') if report.get('pid') is not None else '.'}",
        f"  running: {'yes' if bool(report.get('running')) else 'no'}",
        f"  command: {report.get('command') or '.'}",
        f"  cwd: {report.get('cwd') or '.'}",
        f"  contentChars: {int(report.get('contentChars', 0) or 0)}",
        f"  message: {report.get('message') or ''}",
    ]
    return "\n".join(lines)


def serialize_write_process_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok", False)),
        "processId": str(getattr(observation, "process_id", "") or ""),
        "pid": getattr(observation, "pid", None),
        "running": bool(getattr(observation, "running", False)),
        "command": str(getattr(observation, "command", "") or ""),
        "cwd": str(getattr(observation, "cwd", "") or ""),
        "contentChars": int(getattr(observation, "content_chars", 0) or 0),
        "message": str(getattr(observation, "message", "") or ""),
    }


def parse_write_process_request(
    argument: str | None = None,
    process_id: str | None = None,
    content: str | None = None,
) -> tuple[str, str]:
    selected_process_id = process_id.strip() if process_id else None
    selected_content = content
    if argument and argument.strip():
        if process_id is not None or content is not None:
            raise ValueError("write-process argument cannot be combined with explicit process_id or content.")
        parts = argument.strip().split(maxsplit=1)
        if parts:
            selected_process_id = parts[0]
        selected_content = parts[1] if len(parts) > 1 else None
    if not selected_process_id:
        raise ValueError("process id is required.")
    if selected_content is None or selected_content == "":
        raise ValueError("stdin text is required.")
    return selected_process_id, decode_stdin_escapes(selected_content)


def decode_stdin_escapes(value: str) -> str:
    return value.replace("\\r", "\r").replace("\\n", "\n").replace("\\t", "\t")


def process_status_text(running: bool, exit_code: int | None, signal: str | None) -> str:
    if signal:
        return f"signaled({signal})"
    if running:
        return "running"
    if exit_code is not None:
        return f"exited({exit_code})"
    return "unknown"


def serialize_command_output_analysis(result: object) -> dict[str, object]:
    diagnostics = [serialize_output_diagnostic(item) for item in list(getattr(result, "output_diagnostics", []) or [])]
    contexts = [serialize_output_context_result(item) for item in list(getattr(result, "output_contexts", []) or [])]
    return {
        "diagnostics": {
            "shown": len(diagnostics),
            "total": int(getattr(result, "output_diagnostic_total", 0) or 0),
            "items": diagnostics,
        },
        "diagnosticsTruncated": bool(getattr(result, "output_diagnostics_truncated", False)),
        "contexts": {
            "shown": len(contexts),
            "totalRefs": int(getattr(result, "output_context_total_refs", 0) or 0),
            "items": contexts,
        },
        "contextsTruncated": bool(getattr(result, "output_contexts_truncated", False)),
    }


def format_structured_command_output_analysis_lines(analysis: dict[str, object], spaces: int) -> list[str]:
    prefix = " " * spaces
    child_prefix = " " * (spaces + 2)
    lines: list[str] = []
    diagnostics = analysis.get("diagnostics") if isinstance(analysis.get("diagnostics"), dict) else {}
    diagnostic_items = diagnostics.get("items") if isinstance(diagnostics.get("items"), list) else []
    diagnostic_total = int(diagnostics.get("total", 0) or 0)
    if diagnostic_items or diagnostic_total:
        lines.append(f"{prefix}outputDiagnostics: {len(diagnostic_items)}/{diagnostic_total}")
        lines.append(f"{prefix}outputDiagnosticsTruncated: {'yes' if bool(analysis.get('diagnosticsTruncated')) else 'no'}")
        if diagnostic_items:
            lines.append(f"{prefix}diagnostics:")
            for raw_diagnostic in diagnostic_items:
                diagnostic = raw_diagnostic if isinstance(raw_diagnostic, dict) else {}
                location = ""
                if diagnostic.get("path"):
                    location = f" {diagnostic.get('path')}:{diagnostic.get('line') if diagnostic.get('line') is not None else '?'}"
                    if diagnostic.get("column") is not None:
                        location += f":{diagnostic.get('column')}"
                lines.append(
                    f"{child_prefix}- {diagnostic.get('severity')} outputLine={diagnostic.get('outputLine')}{location}: {diagnostic.get('text') or ''}"
                )
    contexts = analysis.get("contexts") if isinstance(analysis.get("contexts"), dict) else {}
    context_items = contexts.get("items") if isinstance(contexts.get("items"), list) else []
    total_refs = int(contexts.get("totalRefs", 0) or 0)
    if context_items or total_refs:
        lines.append(f"{prefix}outputContexts: {len(context_items)}/{total_refs}")
        lines.append(f"{prefix}outputContextsTruncated: {'yes' if bool(analysis.get('contextsTruncated')) else 'no'}")
        if context_items:
            lines.append(f"{prefix}contexts:")
            for raw_context in context_items:
                context = raw_context if isinstance(raw_context, dict) else {}
                column = f":{context.get('column')}" if context.get("column") is not None else ""
                lines.append(
                    f"{child_prefix}- {context.get('path')}:{context.get('line')}{column} "
                    f"[{context.get('raw') or ''}] ok={'yes' if bool(context.get('ok')) else 'no'}"
                )
                content = str(context.get("content") or "")
                if content:
                    lines.append(_indent_block(content.rstrip(), spaces=spaces + 4))
                else:
                    lines.append(f"{' ' * (spaces + 4)}{context.get('message') or ''}")
    return lines


def _indent_block(value: str, spaces: int = 2) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in value.splitlines())
