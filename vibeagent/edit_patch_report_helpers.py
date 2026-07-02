from __future__ import annotations

from pathlib import Path
from typing import Callable

from .edit_command_parsing import parse_patch_argument, parse_patches_argument
from .workspace_core import RunWorkspace


def _workspace(root: Path, run_id: str) -> RunWorkspace:
    return RunWorkspace(root=root, run_id=run_id, session_dir=root / ".vibeagent" / "sessions" / run_id)


def _patch_usage_report(root: Path, kind: str, usage: str, error: ValueError, *, path: str | None = None) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "kind": kind,
        "ok": False,
        "path": path or "",
        "message": f"Usage: {usage}\nError: {error}",
        "diff": {"text": "", "lines": [], "lineCount": 0},
    }


def _patches_usage_report(root: Path, kind: str, usage: str, error: ValueError) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "kind": kind,
        "ok": False,
        "files": {"total": 0, "items": []},
        "message": f"Usage: {usage}\nError: {error}",
        "diff": {"text": "", "lines": [], "lineCount": 0},
    }


def get_patch_command_report(
    project_root: str | Path,
    argument: str | None,
    *,
    path: str | None,
    patch: str | None,
    kind: str,
    usage: str,
    run_id: str,
    action_factory: Callable[[str, str, str], object],
    execute_action: Callable[[RunWorkspace, object], object],
    serialize_report: Callable[[Path, object], dict[str, object]],
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_patch = parse_patch_argument(argument, path=path, patch=patch, usage=usage)
    except ValueError as error:
        return _patch_usage_report(root, kind, usage, error, path=path)
    observation = execute_action(_workspace(root, run_id), action_factory(kind, parsed_path, parsed_patch))
    return serialize_report(root, observation)


def get_patches_command_report(
    project_root: str | Path,
    argument: str | None,
    *,
    patch: str | None,
    kind: str,
    usage: str,
    run_id: str,
    action_factory: Callable[[str, str], object],
    execute_action: Callable[[RunWorkspace, object], object],
    serialize_report: Callable[[Path, object], dict[str, object]],
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_patch = parse_patches_argument(argument, patch=patch, usage=usage)
    except ValueError as error:
        return _patches_usage_report(root, kind, usage, error)
    observation = execute_action(_workspace(root, run_id), action_factory(kind, parsed_patch))
    return serialize_report(root, observation)
