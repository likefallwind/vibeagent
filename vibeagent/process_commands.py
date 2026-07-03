from __future__ import annotations

from pathlib import Path
import shlex

from .actions import execute_action
from .output_serialization import serialize_output_context_result, serialize_output_diagnostic
from .process_stop_commands import (
    format_check_stop_all_processes_report_text,
    format_check_stop_process_report_text,
    format_stop_all_processes_report_text,
    format_stop_process_report_text,
    get_check_stop_all_processes_report,
    get_check_stop_all_processes_text,
    get_check_stop_process_report,
    get_check_stop_process_text,
    get_stop_all_processes_report,
    get_stop_all_processes_text,
    get_stop_process_report,
    get_stop_process_text,
    serialize_stopped_process_info,
)
from .process_wait_write_commands import (
    decode_stdin_escapes,
    format_check_write_process_report_text,
    format_wait_process_report_text,
    format_write_process_report_text,
    get_check_write_process_report,
    get_check_write_process_text,
    get_wait_process_report,
    get_wait_process_text,
    get_write_process_report,
    get_write_process_text,
    parse_wait_process_request,
    parse_write_process_request,
    serialize_write_process_report,
)
from .process_report_helpers import (
    format_structured_command_output_analysis_lines,
    indent_block as _indent_block,
    process_status_text,
    serialize_command_output_analysis,
    serialize_process_info,
)
from .types import EnvironmentInfoAction, ListProcessesAction, ProcessOutputContextsAction, ProcessOutputDiagnosticsAction, ReadProcessAction
from .workspace_core import RunWorkspace


def get_env_text(project_root: str | Path = ".") -> str:
    return format_env_report_text(get_env_report(project_root))


def get_env_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-env", session_dir=root / ".vibeagent" / "sessions" / "local-env")
    observation = execute_action(
        workspace,
        EnvironmentInfoAction(type="environment_info"),
    )
    if observation.kind != "environment_info":
        return {
            "projectRoot": str(root),
            "ok": False,
            "platform": "",
            "pythonVersion": "",
            "pythonExecutable": "",
            "gitRepo": False,
            "tools": {"available": 0, "total": 0, "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }

    items = [
        {
            "name": tool.name,
            "available": tool.available,
            "path": tool.path or "",
            "version": tool.version or "",
            "message": tool.message,
        }
        for tool in observation.tools
    ]
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "platform": observation.platform,
        "pythonVersion": observation.python_version,
        "pythonExecutable": observation.python_executable,
        "gitRepo": observation.is_git_repo,
        "tools": {
            "available": sum(1 for tool in items if bool(tool.get("available"))),
            "total": len(items),
            "items": items,
        },
        "message": observation.message,
    }


def format_env_report_text(report: dict[str, object]) -> str:
    tools = report.get("tools") if isinstance(report.get("tools"), dict) else {}
    items = [item for item in tools.get("items", []) if isinstance(item, dict)] if isinstance(tools.get("items"), list) else []
    lines = [
        "Environment:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  platform: {report.get('platform') or '.'}",
        f"  pythonVersion: {report.get('pythonVersion') or '.'}",
        f"  pythonExecutable: {report.get('pythonExecutable') or '.'}",
        f"  gitRepo: {'yes' if bool(report.get('gitRepo')) else 'no'}",
        f"  tools: {int(tools.get('available', 0) or 0)}/{int(tools.get('total', len(items)) or 0)}",
    ]
    if items:
        lines.append("  items:")
        for tool in items:
            status = "available" if bool(tool.get("available")) else "missing"
            version = str(tool.get("version") or tool.get("message") or "")
            path = str(tool.get("path") or ".")
            lines.append(f"    - {tool.get('name') or ''}: {status}; path={path}; version={version or '.'}")
    else:
        lines.append("  items: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def get_processes_text(project_root: str | Path = ".") -> str:
    return format_processes_report_text(get_processes_report(project_root))


def get_processes_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-processes", session_dir=root / ".vibeagent" / "sessions" / "local-processes")
    observation = execute_action(
        workspace,
        ListProcessesAction(type="list_processes"),
    )
    if observation.kind != "list_processes":
        return {
            "projectRoot": str(root),
            "processes": {"total": 0, "running": 0, "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }

    items = [serialize_process_info(process) for process in observation.processes]
    running_count = sum(1 for process in items if bool(process.get("running")))
    return {
        "projectRoot": str(root),
        "processes": {"total": len(items), "running": running_count, "items": items},
        "message": observation.message,
    }


def format_processes_report_text(report: dict[str, object]) -> str:
    processes = report.get("processes") if isinstance(report.get("processes"), dict) else {}
    items = [item for item in processes.get("items", []) if isinstance(item, dict)] if isinstance(processes.get("items"), list) else []
    lines = [
        "Processes:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  processes: {int(processes.get('total', len(items)) or 0)}",
        f"  running: {int(processes.get('running', 0) or 0)}",
    ]
    if items:
        lines.append("  items:")
        for process in items:
            lines.append(
                f"    - {process.get('processId')}: "
                f"pid={process.get('pid') if process.get('pid') is not None else '.'}; "
                f"status={process.get('status') or 'unknown'}; "
                f"cwd={process.get('cwd') or '.'}; "
                f"command={process.get('command') or ''}"
            )
    else:
        lines.append("  items: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def get_process_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    max_output_chars: int = 4_000,
) -> str:
    return format_process_report_text(get_process_report(project_root, argument, process_id, max_output_chars))


def get_process_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    max_output_chars: int = 4_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        selected_process_id, selected_max = parse_process_request(argument, process_id, max_output_chars)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": process_id or "",
            "pid": None,
            "status": "unknown",
            "running": False,
            "exitCode": None,
            "signal": None,
            "maxOutputChars": max_output_chars,
            "stdout": "",
            "stderr": "",
            "analysis": {"diagnostics": {"shown": 0, "total": 0, "items": []}, "diagnosticsTruncated": False, "contexts": {"shown": 0, "totalRefs": 0, "items": []}, "contextsTruncated": False},
            "message": f"Usage: /process <id> [chars]\nError: {error}",
        }

    workspace = RunWorkspace(root=root, run_id="local-process", session_dir=root / ".vibeagent" / "sessions" / "local-process")
    observation = execute_action(
        workspace,
        ReadProcessAction(type="read_process", process_id=selected_process_id, max_output_chars=selected_max),
    )
    if observation.kind != "read_process":
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": selected_process_id,
            "pid": None,
            "status": "unknown",
            "running": False,
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
        "exitCode": observation.exit_code,
        "signal": observation.signal,
        "maxOutputChars": observation.max_output_chars,
        "stdout": observation.stdout,
        "stderr": observation.stderr,
        "analysis": serialize_command_output_analysis(observation),
        "message": observation.message,
    }


def format_process_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    analysis = report.get("analysis") if isinstance(report.get("analysis"), dict) else {}
    lines = [
        "Process:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  processId: {report.get('processId') or ''}",
        f"  pid: {report.get('pid') if report.get('pid') is not None else '.'}",
        f"  status: {report.get('status') or 'unknown'}",
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


def get_process_output_contexts_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    max_output_chars: int = 20_000,
    context_lines: int = 5,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    return format_process_output_contexts_report_text(
        get_process_output_contexts_report(
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
    max_output_chars: int = 20_000,
    context_lines: int = 5,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        selected_process_id, selected_max = parse_process_request(argument, process_id, max_output_chars)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": process_id or "",
            "pid": None,
            "status": "unknown",
            "contexts": {"ok": 0, "total": 0, "items": []},
            "totalRefs": 0,
            "maxOutputChars": max_output_chars,
            "stdoutChars": 0,
            "stderrChars": 0,
            "truncated": False,
            "message": f"Usage: /process-output-contexts <id> [chars]\nError: {error}",
        }
    if context_lines < 0:
        message = "Usage: /process-output-contexts <id> [chars]\nError: context_lines must be at least 0."
    elif context_lines > 500:
        message = "Usage: /process-output-contexts <id> [chars]\nError: context_lines must be at most 500."
    elif max_contexts < 1:
        message = "Usage: /process-output-contexts <id> [chars]\nError: max_contexts must be at least 1."
    elif max_contexts > 100:
        message = "Usage: /process-output-contexts <id> [chars]\nError: max_contexts must be at most 100."
    elif max_bytes_per_context < 1_000:
        message = "Usage: /process-output-contexts <id> [chars]\nError: max_bytes_per_context must be at least 1000."
    elif max_bytes_per_context > 200_000:
        message = "Usage: /process-output-contexts <id> [chars]\nError: max_bytes_per_context must be at most 200000."
    else:
        message = ""
    if message:
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": selected_process_id,
            "pid": None,
            "status": "unknown",
            "contexts": {"ok": 0, "total": 0, "items": []},
            "totalRefs": 0,
            "maxOutputChars": selected_max,
            "stdoutChars": 0,
            "stderrChars": 0,
            "truncated": False,
            "message": message,
        }

    workspace = RunWorkspace(root=root, run_id="local-process-output-contexts", session_dir=root / ".vibeagent" / "sessions" / "local-process-output-contexts")
    observation = execute_action(
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
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": selected_process_id,
            "pid": None,
            "status": "unknown",
            "contexts": {"ok": 0, "total": 0, "items": []},
            "totalRefs": 0,
            "maxOutputChars": selected_max,
            "stdoutChars": 0,
            "stderrChars": 0,
            "truncated": False,
            "message": f"Unexpected observation: {observation.kind}",
        }

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


def format_process_output_contexts_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    contexts = report.get("contexts") if isinstance(report.get("contexts"), dict) else {}
    items = contexts.get("items") if isinstance(contexts.get("items"), list) else []
    lines = [
        "Process output contexts:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  processId: {report.get('processId') or ''}",
        f"  pid: {report.get('pid') if report.get('pid') is not None else '.'}",
        f"  status: {report.get('status') or 'unknown'}",
        f"  contexts: {contexts.get('ok', 0)}/{contexts.get('total', 0)}",
        f"  totalRefs: {report.get('totalRefs', 0)}",
        f"  maxOutputChars: {report.get('maxOutputChars', 0)}",
        f"  stdoutChars: {report.get('stdoutChars', 0)}",
        f"  stderrChars: {report.get('stderrChars', 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    for raw_item in items:
        item = raw_item if isinstance(raw_item, dict) else {}
        column = f":{item.get('column')}" if item.get("column") is not None else ""
        lines.extend(
            [
                "",
                f"Context: {item.get('path') or ''}:{item.get('line') if item.get('line') is not None else 'unknown'}{column}",
                f"  raw: {item.get('raw') or ''}",
                f"  ok: {'yes' if bool(item.get('ok')) else 'no'}",
                f"  range: {item.get('startLine')}:{item.get('endLine')}",
                f"  contextLines: {item.get('contextLines') if item.get('contextLines') is not None else 'unknown'}",
                f"  targetLineExists: {'yes' if bool(item.get('targetLineExists')) else 'no'}",
                f"  lines: {item.get('lineCount', 0)}/{item.get('totalLines') if item.get('totalLines') is not None else 'unknown'}",
                f"  maxBytes: {item.get('maxBytes') if item.get('maxBytes') is not None else 'unknown'}",
                f"  truncated: {'yes' if bool(item.get('truncated')) else 'no'}",
                f"  message: {item.get('message') or ''}",
            ]
        )
        content = str(item.get("content") or "")
        if content:
            lines.append("  content:")
            lines.append(_indent_block(content.rstrip("\n"), spaces=4))
        else:
            lines.append("  content: none")
    return "\n".join(lines)


def get_process_output_diagnostics_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    max_output_chars: int = 20_000,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    return format_process_output_diagnostics_report_text(
        get_process_output_diagnostics_report(
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
    max_output_chars: int = 20_000,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        selected_process_id, selected_max = parse_process_request(argument, process_id, max_output_chars)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": process_id or "",
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
            "message": f"Usage: /process-output-diagnostics <id> [chars]\nError: {error}",
        }
    if context_lines < 0:
        message = "Usage: /process-output-diagnostics <id> [chars]\nError: context_lines must be at least 0."
    elif context_lines > 500:
        message = "Usage: /process-output-diagnostics <id> [chars]\nError: context_lines must be at most 500."
    elif max_diagnostics < 1:
        message = "Usage: /process-output-diagnostics <id> [chars]\nError: max_diagnostics must be at least 1."
    elif max_diagnostics > 200:
        message = "Usage: /process-output-diagnostics <id> [chars]\nError: max_diagnostics must be at most 200."
    elif max_contexts < 1:
        message = "Usage: /process-output-diagnostics <id> [chars]\nError: max_contexts must be at least 1."
    elif max_contexts > 100:
        message = "Usage: /process-output-diagnostics <id> [chars]\nError: max_contexts must be at most 100."
    elif max_bytes_per_context < 1_000:
        message = "Usage: /process-output-diagnostics <id> [chars]\nError: max_bytes_per_context must be at least 1000."
    elif max_bytes_per_context > 200_000:
        message = "Usage: /process-output-diagnostics <id> [chars]\nError: max_bytes_per_context must be at most 200000."
    else:
        message = ""
    if message:
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": selected_process_id,
            "pid": None,
            "status": "unknown",
            "diagnostics": {"shown": 0, "total": 0, "items": []},
            "contexts": {"ok": 0, "total": 0, "items": []},
            "totalRefs": 0,
            "maxOutputChars": selected_max,
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

    workspace = RunWorkspace(root=root, run_id="local-process-output-diagnostics", session_dir=root / ".vibeagent" / "sessions" / "local-process-output-diagnostics")
    observation = execute_action(
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
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": selected_process_id,
            "pid": None,
            "status": "unknown",
            "diagnostics": {"shown": 0, "total": 0, "items": []},
            "contexts": {"ok": 0, "total": 0, "items": []},
            "totalRefs": 0,
            "maxOutputChars": selected_max,
            "stdoutChars": 0,
            "stderrChars": 0,
            "contextLines": context_lines,
            "maxDiagnostics": max_diagnostics,
            "maxContexts": max_contexts,
            "maxBytesPerContext": max_bytes_per_context,
            "diagnosticsTruncated": False,
            "contextsTruncated": False,
            "message": f"Unexpected observation: {observation.kind}",
        }

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


def format_process_output_diagnostics_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    diagnostics = report.get("diagnostics") if isinstance(report.get("diagnostics"), dict) else {}
    diagnostic_items = diagnostics.get("items") if isinstance(diagnostics.get("items"), list) else []
    contexts = report.get("contexts") if isinstance(report.get("contexts"), dict) else {}
    context_items = contexts.get("items") if isinstance(contexts.get("items"), list) else []
    lines = [
        "Process output diagnostics:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  processId: {report.get('processId') or ''}",
        f"  pid: {report.get('pid') if report.get('pid') is not None else '.'}",
        f"  status: {report.get('status') or 'unknown'}",
        f"  diagnostics: {diagnostics.get('shown', 0)}/{diagnostics.get('total', 0)}",
        f"  contexts: {contexts.get('ok', 0)}/{contexts.get('total', 0)}",
        f"  totalRefs: {report.get('totalRefs', 0)}",
        f"  maxOutputChars: {report.get('maxOutputChars', 0)}",
        f"  stdoutChars: {report.get('stdoutChars', 0)}",
        f"  stderrChars: {report.get('stderrChars', 0)}",
        f"  contextLines: {report.get('contextLines') if report.get('contextLines') is not None else 'unknown'}",
        f"  maxDiagnostics: {report.get('maxDiagnostics') if report.get('maxDiagnostics') is not None else 'unknown'}",
        f"  maxContexts: {report.get('maxContexts') if report.get('maxContexts') is not None else 'unknown'}",
        f"  maxBytesPerContext: {report.get('maxBytesPerContext') if report.get('maxBytesPerContext') is not None else 'unknown'}",
        f"  diagnosticsTruncated: {'yes' if bool(report.get('diagnosticsTruncated')) else 'no'}",
        f"  contextsTruncated: {'yes' if bool(report.get('contextsTruncated')) else 'no'}",
        f"  message: {message}",
    ]
    for raw_diagnostic in diagnostic_items:
        diagnostic = raw_diagnostic if isinstance(raw_diagnostic, dict) else {}
        location = ""
        if diagnostic.get("path") and diagnostic.get("line") is not None:
            column = f":{diagnostic.get('column')}" if diagnostic.get("column") is not None else ""
            location = f" {diagnostic.get('path')}:{diagnostic.get('line')}{column}"
        lines.append(
            f"  - {diagnostic.get('severity')} outputLine={diagnostic.get('outputLine')}{location}: {diagnostic.get('text') or ''}"
        )
    for raw_item in context_items:
        item = raw_item if isinstance(raw_item, dict) else {}
        column = f":{item.get('column')}" if item.get("column") is not None else ""
        lines.extend(
            [
                "",
                f"Context: {item.get('path') or ''}:{item.get('line') if item.get('line') is not None else 'unknown'}{column}",
                f"  raw: {item.get('raw') or ''}",
                f"  ok: {'yes' if bool(item.get('ok')) else 'no'}",
                f"  range: {item.get('startLine')}:{item.get('endLine')}",
                f"  contextLines: {item.get('contextLines') if item.get('contextLines') is not None else 'unknown'}",
                f"  targetLineExists: {'yes' if bool(item.get('targetLineExists')) else 'no'}",
                f"  lines: {item.get('lineCount', 0)}/{item.get('totalLines') if item.get('totalLines') is not None else 'unknown'}",
                f"  maxBytes: {item.get('maxBytes') if item.get('maxBytes') is not None else 'unknown'}",
                f"  truncated: {'yes' if bool(item.get('truncated')) else 'no'}",
                f"  message: {item.get('message') or ''}",
            ]
        )
        content = str(item.get("content") or "")
        if content:
            lines.append("  content:")
            lines.append(_indent_block(content.rstrip("\n"), spaces=4))
        else:
            lines.append("  content: none")
    return "\n".join(lines)


def parse_process_request(
    argument: str | None = None,
    process_id: str | None = None,
    max_output_chars: int = 4_000,
) -> tuple[str, int]:
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
    if selected_max < 1_000:
        raise ValueError("max chars must be at least 1000.")
    if selected_max > 50_000:
        raise ValueError("max chars must be at most 50000.")
    return selected_process_id, selected_max
