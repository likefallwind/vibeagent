from __future__ import annotations

from .output_serialization import serialize_output_context_result, serialize_output_diagnostic


def indent_block(value: str, spaces: int = 2) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in value.splitlines())


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
        lines.append(indent_block(stdout.rstrip(), spaces=4))
    else:
        lines.append("  stdout: none")
    if stderr:
        lines.append("  stderr:")
        lines.append(indent_block(stderr.rstrip(), spaces=4))
    else:
        lines.append("  stderr: none")
    lines.extend(format_structured_command_output_analysis_lines(analysis, spaces=2))
    return "\n".join(lines)


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
            lines.append(indent_block(content.rstrip("\n"), spaces=4))
        else:
            lines.append("  content: none")
    return "\n".join(lines)


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
            lines.append(indent_block(content.rstrip("\n"), spaces=4))
        else:
            lines.append("  content: none")
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
                    lines.append(indent_block(content.rstrip(), spaces=spaces + 4))
                else:
                    lines.append(f"{' ' * (spaces + 4)}{context.get('message') or ''}")
    return lines
