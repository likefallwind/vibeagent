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
