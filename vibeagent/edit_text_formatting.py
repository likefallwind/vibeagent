from __future__ import annotations

from pathlib import Path


def format_write_files_observation(title: str, root: Path, observation: object) -> str:
    return format_write_files_report_text(title, serialize_write_files_report(root, observation))


def serialize_write_files_report(root: Path, observation: object) -> dict[str, object]:
    file_reports: list[dict[str, object]] = []
    for file in list(getattr(observation, "files", [])):
        diff = str(getattr(file, "diff", "") or "")
        file_reports.append(
            {
                "path": str(getattr(file, "path", "") or ""),
                "ok": bool(getattr(file, "ok", False)),
                "message": str(getattr(file, "message", "") or ""),
                "diff": {"text": diff, "lines": diff.splitlines(), "lineCount": len(diff.splitlines())},
            }
        )
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "files": {"total": len(file_reports), "items": file_reports},
        "message": str(getattr(observation, "message", "") or ""),
    }


def format_write_files_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    files_report = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = [item for item in files_report.get("items", []) if isinstance(item, dict)] if isinstance(files_report.get("items"), list) else []
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  files: {int(files_report.get('total', len(items)) or 0)}",
        f"  message: {message}",
    ]
    if items:
        lines.append("  items:")
        for file in items:
            lines.append(f"    - {file.get('path') or ''}: {'ok' if bool(file.get('ok')) else 'failed'} - {file.get('message') or ''}")
            diff_report = file.get("diff") if isinstance(file.get("diff"), dict) else {}
            diff = str(diff_report.get("text") or "")
            if diff:
                lines.append("      diff:")
                for diff_line in diff.splitlines():
                    lines.append(f"        {diff_line}")
    return "\n".join(lines)


def format_line_edit_observation(title: str, root: Path, observation: object) -> str:
    return format_line_edit_report_text(title, serialize_line_edit_report(root, observation))


def serialize_line_edit_report(root: Path, observation: object) -> dict[str, object]:
    diff = str(getattr(observation, "diff", "") or "")
    report: dict[str, object] = {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "")),
        "ok": bool(getattr(observation, "ok", False)),
        "path": str(getattr(observation, "path", "") or ""),
        "message": str(getattr(observation, "message", "") or ""),
        "diff": {"text": diff, "lines": diff.splitlines(), "lineCount": len(diff.splitlines())},
    }
    if hasattr(observation, "start_line"):
        report["startLine"] = getattr(observation, "start_line")
    if hasattr(observation, "end_line"):
        report["endLine"] = getattr(observation, "end_line")
    if hasattr(observation, "line"):
        report["line"] = getattr(observation, "line")
    return report


def format_line_edit_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or ''}",
    ]
    if "startLine" in report and "endLine" in report:
        lines.append(f"  range: {report.get('startLine')}-{report.get('endLine')}")
    if "line" in report:
        lines.append(f"  line: {report.get('line')}")
    lines.append(f"  message: {message}")
    diff_report = report.get("diff") if isinstance(report.get("diff"), dict) else {}
    diff = str(diff_report.get("text") or "")
    if diff:
        lines.append("  diff:")
        for diff_line in diff.splitlines():
            lines.append(f"    {diff_line}")
    return "\n".join(lines)
