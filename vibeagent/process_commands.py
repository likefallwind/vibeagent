from __future__ import annotations

from pathlib import Path
import shlex

from .actions import execute_action
from .types import CheckStopAllProcessesAction, CheckStopProcessAction, CheckWriteProcessAction, EnvironmentInfoAction, ListProcessesAction, ProcessOutputContextsAction, ProcessOutputDiagnosticsAction, ReadProcessAction, StopAllProcessesAction, StopProcessAction, WaitProcessAction, WriteProcessAction
from .workspace_core import RunWorkspace


def _indent_block(value: str, spaces: int = 2) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in value.splitlines())


def serialize_output_context_result(item: object) -> dict[str, object]:
    return {
        "path": str(getattr(item, "path", "")),
        "line": getattr(item, "line", None),
        "column": getattr(item, "column", None),
        "raw": str(getattr(item, "raw", "")),
        "ok": bool(getattr(item, "ok", False)),
        "content": str(getattr(item, "content", "")),
        "message": str(getattr(item, "message", "")),
        "contextLines": getattr(item, "context_lines", None),
        "startLine": getattr(item, "start_line", None),
        "endLine": getattr(item, "end_line", None),
        "lineCount": getattr(item, "line_count", 0),
        "totalLines": getattr(item, "total_lines", None),
        "targetLineExists": bool(getattr(item, "target_line_exists", False)),
        "truncated": bool(getattr(item, "truncated", False)),
        "maxBytes": getattr(item, "max_bytes", None),
    }


def serialize_output_diagnostic(item: object) -> dict[str, object]:
    return {
        "severity": str(getattr(item, "severity", "")),
        "outputLine": getattr(item, "output_line", None),
        "text": str(getattr(item, "text", "")),
        "path": getattr(item, "path", None),
        "line": getattr(item, "line", None),
        "column": getattr(item, "column", None),
        "raw": getattr(item, "raw", None),
    }


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


def process_status_text(running: bool, exit_code: int | None, signal: str | None) -> str:
    if signal:
        return f"signaled({signal})"
    if running:
        return "running"
    if exit_code is not None:
        return f"exited({exit_code})"
    return "unknown"


def serialize_process_info(process: object) -> dict[str, object]:
    running = bool(getattr(process, "running", False))
    exit_code = getattr(process, "exit_code", None)
    signal = getattr(process, "signal", None)
    return {
        "processId": str(getattr(process, "process_id", "") or ""),
        "pid": getattr(process, "pid", None),
        "command": str(getattr(process, "command", "") or ""),
        "cwd": str(getattr(process, "cwd", ".") or "."),
        "running": running,
        "exitCode": exit_code,
        "signal": signal,
        "status": process_status_text(running, exit_code, signal),
    }


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
    return format_wait_process_report_text(
        get_wait_process_report(
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
    observation = execute_action(
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
    return format_write_process_report_text(get_write_process_report(project_root, argument, process_id, content))


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
    observation = execute_action(
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
    return format_check_write_process_report_text(get_check_write_process_report(project_root, argument, process_id, content))


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
    observation = execute_action(
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


def get_check_stop_process_text(project_root: str | Path = ".", process_id: str | None = None) -> str:
    return format_check_stop_process_report_text(get_check_stop_process_report(project_root, process_id))


def get_check_stop_process_report(project_root: str | Path = ".", process_id: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    selected_process_id = process_id.strip() if process_id else None
    if not selected_process_id:
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": "",
            "pid": None,
            "command": "",
            "cwd": "",
            "running": False,
            "exitCode": None,
            "signal": None,
            "status": "unknown",
            "message": "Usage: /check-stop-process <id>\nError: process id is required.",
        }

    workspace = RunWorkspace(root=root, run_id="local-check-stop-process", session_dir=root / ".vibeagent" / "sessions" / "local-check-stop-process")
    observation = execute_action(
        workspace,
        CheckStopProcessAction(type="check_stop_process", process_id=selected_process_id),
    )
    if observation.kind != "check_stop_process":
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": selected_process_id,
            "pid": None,
            "command": "",
            "cwd": "",
            "running": False,
            "exitCode": None,
            "signal": None,
            "status": "unknown",
            "message": f"Unexpected observation: {observation.kind}",
        }

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "processId": observation.process_id,
        "pid": observation.pid,
        "command": observation.command or "",
        "cwd": observation.cwd or "",
        "running": observation.running,
        "exitCode": observation.exit_code,
        "signal": observation.signal,
        "status": process_status_text(observation.running, observation.exit_code, observation.signal),
        "message": observation.message,
    }


def format_check_stop_process_report_text(report: dict[str, object]) -> str:
    return "\n".join(
        [
            "Check stop process:",
            f"  projectRoot: {report.get('projectRoot') or '.'}",
            f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
            f"  processId: {report.get('processId') or ''}",
            f"  pid: {report.get('pid') if report.get('pid') is not None else '.'}",
            f"  status: {report.get('status') or 'unknown'}",
            f"  command: {report.get('command') or '.'}",
            f"  cwd: {report.get('cwd') or '.'}",
            f"  message: {report.get('message') or ''}",
        ]
    )


def get_stop_process_text(project_root: str | Path = ".", process_id: str | None = None) -> str:
    return format_stop_process_report_text(get_stop_process_report(project_root, process_id))


def get_stop_process_report(project_root: str | Path = ".", process_id: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    selected_process_id = process_id.strip() if process_id else None
    if not selected_process_id:
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": "",
            "pid": None,
            "exitCode": None,
            "signal": None,
            "result": "unknown",
            "message": "Usage: /stop-process <id>\nError: process id is required.",
        }

    workspace = RunWorkspace(root=root, run_id="local-stop-process", session_dir=root / ".vibeagent" / "sessions" / "local-stop-process")
    observation = execute_action(
        workspace,
        StopProcessAction(type="stop_process", process_id=selected_process_id),
    )
    if observation.kind != "stop_process":
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": selected_process_id,
            "pid": None,
            "exitCode": None,
            "signal": None,
            "result": "unknown",
            "message": f"Unexpected observation: {observation.kind}",
        }

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "processId": observation.process_id,
        "pid": observation.pid,
        "exitCode": observation.exit_code,
        "signal": observation.signal,
        "result": process_status_text(False, observation.exit_code, observation.signal),
        "message": observation.message,
    }


def format_stop_process_report_text(report: dict[str, object]) -> str:
    return "\n".join(
        [
            "Stop process:",
            f"  projectRoot: {report.get('projectRoot') or '.'}",
            f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
            f"  processId: {report.get('processId') or ''}",
            f"  pid: {report.get('pid') if report.get('pid') is not None else '.'}",
            f"  result: {report.get('result') or 'unknown'}",
            f"  message: {report.get('message') or ''}",
        ]
    )


def get_check_stop_all_processes_text(project_root: str | Path = ".") -> str:
    return format_check_stop_all_processes_report_text(get_check_stop_all_processes_report(project_root))


def get_check_stop_all_processes_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-check-stop-all-processes", session_dir=root / ".vibeagent" / "sessions" / "local-check-stop-all-processes")
    observation = execute_action(
        workspace,
        CheckStopAllProcessesAction(type="check_stop_all_processes"),
    )
    if observation.kind != "check_stop_all_processes":
        return {
            "projectRoot": str(root),
            "ok": False,
            "processes": {"total": 0, "running": 0, "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }

    items = [serialize_process_info(process) for process in observation.processes]
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "processes": {"total": len(items), "running": observation.running_count, "items": items},
        "message": observation.message,
    }


def format_check_stop_all_processes_report_text(report: dict[str, object]) -> str:
    processes = report.get("processes") if isinstance(report.get("processes"), dict) else {}
    items = [item for item in processes.get("items", []) if isinstance(item, dict)] if isinstance(processes.get("items"), list) else []
    lines = [
        "Check stop processes:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
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


def get_stop_all_processes_text(project_root: str | Path = ".") -> str:
    return format_stop_all_processes_report_text(get_stop_all_processes_report(project_root))


def get_stop_all_processes_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-stop-all-processes", session_dir=root / ".vibeagent" / "sessions" / "local-stop-all-processes")
    observation = execute_action(
        workspace,
        StopAllProcessesAction(type="stop_all_processes"),
    )
    if observation.kind != "stop_all_processes":
        return {
            "projectRoot": str(root),
            "ok": False,
            "stopped": {"total": 0, "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }

    items = [serialize_stopped_process_info(process) for process in observation.stopped]
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "stopped": {"total": len(items), "items": items},
        "message": observation.message,
    }


def format_stop_all_processes_report_text(report: dict[str, object]) -> str:
    stopped = report.get("stopped") if isinstance(report.get("stopped"), dict) else {}
    items = [item for item in stopped.get("items", []) if isinstance(item, dict)] if isinstance(stopped.get("items"), list) else []
    lines = [
        "Stop processes:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  stopped: {int(stopped.get('total', len(items)) or 0)}",
    ]
    if items:
        lines.append("  processes:")
        for process in items:
            lines.extend(
                [
                    f"    - {process.get('processId') or ''}",
                    f"      pid: {process.get('pid') if process.get('pid') is not None else '.'}",
                    f"      command: {process.get('command') or ''}",
                    f"      cwd: {process.get('cwd') or '.'}",
                    f"      ok: {'yes' if bool(process.get('ok')) else 'no'}",
                    f"      result: {process.get('result') or 'unknown'}",
                    f"      message: {process.get('message') or ''}",
                ]
            )
    else:
        lines.append("  processes: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def serialize_stopped_process_info(process: object) -> dict[str, object]:
    exit_code = getattr(process, "exit_code", None)
    signal = getattr(process, "signal", None)
    return {
        "processId": str(getattr(process, "process_id", "") or ""),
        "pid": getattr(process, "pid", None),
        "command": str(getattr(process, "command", "") or ""),
        "cwd": str(getattr(process, "cwd", ".") or "."),
        "ok": bool(getattr(process, "ok", False)),
        "exitCode": exit_code,
        "signal": signal,
        "result": process_status_text(False, exit_code, signal),
        "message": str(getattr(process, "message", "") or ""),
    }
