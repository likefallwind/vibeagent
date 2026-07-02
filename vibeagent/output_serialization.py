from __future__ import annotations


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
