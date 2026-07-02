from __future__ import annotations

from .types import OutputContextResult, OutputDiagnostic


def output_context_results_from_dicts(items: object) -> list[OutputContextResult]:
    if not isinstance(items, list):
        return []
    results: list[OutputContextResult] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        results.append(
            OutputContextResult(
                path=str(item["path"]),
                line=int(item["line"]),
                column=int(item["column"]) if item["column"] is not None else None,
                raw=str(item["raw"]),
                ok=bool(item["ok"]),
                content=str(item["content"]),
                message=str(item["message"]),
                context_lines=int(item["context_lines"]),
                start_line=int(item["start_line"]),
                end_line=int(item["end_line"]),
                line_count=int(item["line_count"]),
                total_lines=int(item["total_lines"]) if item["total_lines"] is not None else None,
                target_line_exists=bool(item["target_line_exists"]),
                truncated=bool(item["truncated"]),
                max_bytes=int(item["max_bytes"]),
            )
        )
    return results


def output_diagnostics_from_dicts(items: object) -> list[OutputDiagnostic]:
    if not isinstance(items, list):
        return []
    diagnostics: list[OutputDiagnostic] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity") or "info")
        if severity not in {"error", "warning", "failure", "info"}:
            severity = "info"
        diagnostics.append(
            OutputDiagnostic(
                severity=severity,  # type: ignore[arg-type]
                output_line=int(item["output_line"]),
                text=str(item["text"]),
                path=str(item["path"]) if item.get("path") is not None else None,
                line=int(item["line"]) if item.get("line") is not None else None,
                column=int(item["column"]) if item.get("column") is not None else None,
                raw=str(item["raw"]) if item.get("raw") is not None else None,
            )
        )
    return diagnostics
