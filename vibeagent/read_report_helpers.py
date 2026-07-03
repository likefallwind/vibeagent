from __future__ import annotations


def format_read_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage: "):
        return message
    read = report.get("read") if isinstance(report.get("read"), dict) else {}
    content = str(read.get("content") or "") if isinstance(read, dict) else ""
    lines = [
        "Read:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  path: {report.get('path') or ''}",
        f"  range: {report.get('range') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  showLineNumbers: {'yes' if bool(report.get('showLineNumbers')) else 'no'}",
        f"  totalBytes: {read.get('totalBytes') if read.get('totalBytes') is not None else 'unknown'}",
        f"  maxBytes: {read.get('maxBytes') if read.get('maxBytes') is not None else 'unknown'}",
        f"  truncated: {'yes' if bool(read.get('truncated')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]
    if content:
        lines.append("  content:")
        lines.append(indent_block(content.rstrip("\n"), spaces=4))
    else:
        lines.append("  content: none")
    return "\n".join(lines)


def format_tail_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage: "):
        return message
    tail = report.get("tail") if isinstance(report.get("tail"), dict) else {}
    content = str(tail.get("content") or "") if isinstance(tail, dict) else ""
    lines = [
        "Tail:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  path: {report.get('path') or ''}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  lines: {tail.get('lineCount', 0)}/{tail.get('totalLines') if tail.get('totalLines') is not None else 'unknown'}",
        f"  startLine: {tail.get('startLine') if tail.get('startLine') is not None else 'unknown'}",
        f"  requestedLines: {tail.get('requestedLines') if tail.get('requestedLines') is not None else 'unknown'}",
        f"  maxBytes: {tail.get('maxBytes') if tail.get('maxBytes') is not None else 'unknown'}",
        f"  truncated: {'yes' if bool(tail.get('truncated')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]
    if content:
        lines.append("  content:")
        lines.append(indent_block(content.rstrip("\n"), spaces=4))
    else:
        lines.append("  content: none")
    return "\n".join(lines)


def format_around_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage: "):
        return message
    context = report.get("context") if isinstance(report.get("context"), dict) else {}
    content = str(context.get("content") or "") if isinstance(context, dict) else ""
    lines = [
        "Around:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  path: {report.get('path') or ''}",
        f"  line: {report.get('line') if report.get('line') is not None else 'unknown'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  range: {context.get('startLine')}:{context.get('endLine')}",
        f"  contextLines: {context.get('contextLines') if context.get('contextLines') is not None else 'unknown'}",
        f"  targetLineExists: {'yes' if bool(context.get('targetLineExists')) else 'no'}",
        f"  lines: {context.get('lineCount', 0)}/{context.get('totalLines') if context.get('totalLines') is not None else 'unknown'}",
        f"  maxBytes: {context.get('maxBytes') if context.get('maxBytes') is not None else 'unknown'}",
        f"  truncated: {'yes' if bool(context.get('truncated')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]
    if content:
        lines.append("  content:")
        lines.append(indent_block(content.rstrip("\n"), spaces=4))
    else:
        lines.append("  content: none")
    return "\n".join(lines)


def format_around_many_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage: "):
        return message
    contexts = report.get("contexts") if isinstance(report.get("contexts"), dict) else {}
    items = contexts.get("items") if isinstance(contexts.get("items"), list) else []
    lines = [
        "Around many:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  contexts: {contexts.get('ok', 0)}/{contexts.get('total', len(items))}",
        f"  maxBytesPerContext: {report.get('maxBytesPerContext') if report.get('maxBytesPerContext') is not None else 'unknown'}",
        f"  message: {report.get('message') or ''}",
    ]
    for raw_item in items:
        item = raw_item if isinstance(raw_item, dict) else {}
        lines.extend(
            [
                "",
                f"Context: {item.get('path') or ''}:{item.get('line') if item.get('line') is not None else 'unknown'}",
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


def format_read_files_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage: "):
        return message
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = files.get("items") if isinstance(files, dict) and isinstance(files.get("items"), list) else []
    lines = [
        "Read files:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  files: {files.get('ok', 0)}/{files.get('total', 0)}",
        f"  maxBytesPerFile: {report.get('maxBytesPerFile', 0)}",
        f"  showLineNumbers: {'yes' if bool(report.get('showLineNumbers')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]
    for item in items:
        if not isinstance(item, dict):
            continue
        lines.extend(
            [
                "",
                f"File: {item.get('path')}",
                f"  ok: {'yes' if bool(item.get('ok')) else 'no'}",
                f"  totalBytes: {item.get('totalBytes') if item.get('totalBytes') is not None else 'unknown'}",
                f"  maxBytes: {item.get('maxBytes') if item.get('maxBytes') is not None else 'unknown'}",
                f"  truncated: {'yes' if bool(item.get('truncated')) else 'no'}",
                f"  showLineNumbers: {'yes' if bool(item.get('showLineNumbers')) else 'no'}",
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


def format_read_ranges_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage: "):
        return message
    ranges = report.get("ranges") if isinstance(report.get("ranges"), dict) else {}
    items = ranges.get("items") if isinstance(ranges, dict) and isinstance(ranges.get("items"), list) else []
    lines = [
        "Read ranges:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ranges: {ranges.get('ok', 0)}/{ranges.get('total', 0)}",
        f"  maxBytesPerRange: {report.get('maxBytesPerRange', 0)}",
        f"  message: {report.get('message') or ''}",
    ]
    for item in items:
        if not isinstance(item, dict):
            continue
        lines.extend(
            [
                "",
                f"Range: {item.get('path')}:{item.get('startLine')}:{item.get('endLine')}",
                f"  ok: {'yes' if bool(item.get('ok')) else 'no'}",
                f"  lineCount: {item.get('lineCount')}",
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


def indent_block(value: str, spaces: int = 2) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in value.splitlines())
