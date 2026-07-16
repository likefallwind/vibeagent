from __future__ import annotations

from pathlib import Path


def file_transfer_usage_report(
    root: Path,
    kind: str,
    usage: str,
    error: ValueError,
    *,
    source: str | None = None,
    destination: str | None = None,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "kind": kind,
        "ok": False,
        "source": source or "",
        "destination": destination or "",
        "message": f"Usage: {usage}\nError: {error}",
    }


def file_transfer_list_usage_report(root: Path, kind: str, usage: str, error: ValueError) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "kind": kind,
        "ok": False,
        "transfers": {"total": 0, "items": []},
        "message": f"Usage: {usage}\nError: {error}",
    }


def path_action_usage_report(
    root: Path,
    kind: str,
    usage: str,
    error: ValueError,
    *,
    path: str | None = None,
    fields: dict[str, object] | None = None,
) -> dict[str, object]:
    report: dict[str, object] = {
        "projectRoot": str(root),
        "kind": kind,
        "ok": False,
        "path": path or "",
        "message": f"Usage: {usage}\nError: {error}",
    }
    if fields:
        report.update(fields)
    return report


def config_check_usage_report(root: Path, usage: str, error: ValueError, *, path: str | None = None) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "path": path or ".",
        "files": {"shown": 0, "total": 0, "items": []},
        "truncated": False,
        "message": f"Usage: {usage}\nError: {error}",
    }


def path_list_usage_report(root: Path, kind: str, usage: str, error: ValueError) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "kind": kind,
        "ok": False,
        "paths": {"total": 0, "items": []},
        "message": f"Usage: {usage}\nError: {error}",
    }


def line_edit_usage_report(
    root: Path,
    kind: str,
    usage: str,
    error: ValueError,
    *,
    path: str | None = None,
    fields: dict[str, object] | None = None,
) -> dict[str, object]:
    report: dict[str, object] = {
        "projectRoot": str(root),
        "kind": kind,
        "ok": False,
        "path": path or "",
        "message": f"Usage: {usage}\nError: {error}",
        "diff": {"text": "", "lines": [], "lineCount": 0},
    }
    if fields:
        report.update(fields)
    return report
