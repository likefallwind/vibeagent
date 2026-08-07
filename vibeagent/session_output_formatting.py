from __future__ import annotations


def indent_block(value: str, spaces: int = 2) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in value.splitlines())


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
        lines.extend(format_output_context_item_text(item))
    return "\n".join(lines)


def format_output_context_item_text(item: dict[str, object]) -> list[str]:
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
        lines.append(indent_block(content.rstrip("\n"), spaces=4))
    else:
        lines.append("  content: none")
    return lines


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
        lines.extend(format_output_context_item_text(item))
    return "\n".join(lines)
