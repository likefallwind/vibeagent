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


def path_action_usage_report(root: Path, kind: str, usage: str, error: ValueError, *, path: str | None = None) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "kind": kind,
        "ok": False,
        "path": path or "",
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
