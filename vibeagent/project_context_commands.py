from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .project_context_formatting import (
    format_check_focused_test_commands_report_text,
    format_commands_report_text,
    format_focused_test_commands_report_text,
    format_instructions_report_text,
    format_manifest_summary,
    format_manifests_report_text,
    format_project_command,
    format_related_tests_report_text,
    format_run_focused_test_commands_report_text,
    format_todos_report_text,
)
from .project_focused_test_commands import (
    get_check_focused_test_commands_report,
    get_check_focused_test_commands_text,
    get_focused_test_commands_report,
    get_focused_test_commands_text,
    get_related_tests_report,
    get_related_tests_text,
    get_run_focused_test_commands_report,
    get_run_focused_test_commands_text,
    parse_related_tests_argument,
)
from .workspace_core import RunWorkspace
from .workspace import (
    read_project_commands,
    read_project_instruction_sources,
    read_project_manifests,
    read_project_todos,
)


def get_commands_text(project_root: str | Path = ".", max_commands: int = 100, max_files: int = 30) -> str:
    return format_commands_report_text(get_commands_report(project_root, max_commands=max_commands, max_files=max_files))


def get_commands_report(project_root: str | Path = ".", max_commands: int = 100, max_files: int = 30) -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-commands", session_dir=root / ".vibeagent" / "sessions" / "local-commands")
    try:
        metadata = read_project_commands(workspace, max_commands=max_commands, max_files=max_files)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "commands": {"shown": 0, "total": 0, "items": []},
            "metadataFiles": {"scanned": 0, "total": 0},
            "truncated": False,
            "message": str(error),
        }
    commands = [item for item in metadata["commands"] if isinstance(item, dict)]
    return {
        "projectRoot": str(root),
        "ok": bool(metadata["ok"]),
        "commands": {
            "shown": len(commands),
            "total": int(metadata["total"]),
            "items": commands,
        },
        "metadataFiles": {
            "scanned": int(metadata["scanned_files"]),
            "total": int(metadata["total_files"]),
        },
        "truncated": bool(metadata["truncated"]),
        "message": str(metadata["message"]),
    }


def get_manifests_text(project_root: str | Path = ".", max_files: int = 30, max_items: int = 500) -> str:
    return format_manifests_report_text(get_manifests_report(project_root, max_files=max_files, max_items=max_items))


def get_manifests_report(project_root: str | Path = ".", max_files: int = 30, max_items: int = 500) -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-manifests", session_dir=root / ".vibeagent" / "sessions" / "local-manifests")
    try:
        metadata = read_project_manifests(workspace, max_files=max_files, max_items=max_items)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "files": {"shown": 0, "total": 0, "scanned": 0},
            "items": {"total": 0},
            "truncated": False,
            "manifests": [],
            "message": str(error),
        }
    manifests = [item for item in metadata["manifests"] if isinstance(item, dict)]
    return {
        "projectRoot": str(root),
        "ok": bool(metadata["ok"]),
        "files": {
            "shown": len(manifests),
            "total": int(metadata["total_files"]),
            "scanned": int(metadata["scanned_files"]),
        },
        "items": {"total": int(metadata["total_items"])},
        "truncated": bool(metadata["truncated"]),
        "manifests": manifests,
        "message": str(metadata["message"]),
    }


def get_instructions_text(project_root: str | Path = ".", max_files: int = 20, max_bytes: int = 12_000) -> str:
    return format_instructions_report_text(get_instructions_report(project_root, max_files=max_files, max_bytes=max_bytes))


def get_instructions_report(project_root: str | Path = ".", max_files: int = 20, max_bytes: int = 12_000) -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-instructions", session_dir=root / ".vibeagent" / "sessions" / "local-instructions")
    try:
        metadata = read_project_instruction_sources(workspace, max_files=max_files, max_bytes=max_bytes)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "files": {"shown": 0, "total": 0, "scanned": 0, "omitted": 0, "sources": []},
            "truncated": False,
            "text": "",
            "message": str(error),
        }
    sources = [item for item in metadata["files"] if isinstance(item, dict)]
    return {
        "projectRoot": str(root),
        "ok": bool(metadata["ok"]),
        "files": {
            "shown": len(sources),
            "total": int(metadata["total_files"]),
            "scanned": int(metadata["scanned_files"]),
            "omitted": int(metadata["omitted_files"]),
            "sources": sources,
        },
        "truncated": bool(metadata["truncated"]),
        "text": str(metadata["text"]),
        "message": str(metadata["message"]),
    }


def get_todos_text(
    project_root: str | Path = ".",
    path: str | None = None,
    max_items: int = 100,
    max_files: int = 1000,
) -> str:
    return format_todos_report_text(get_todos_report(project_root, path=path, max_items=max_items, max_files=max_files))


def get_todos_report(
    project_root: str | Path = ".",
    path: str | None = None,
    max_items: int = 100,
    max_files: int = 1000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-todos", session_dir=root / ".vibeagent" / "sessions" / "local-todos")
    try:
        metadata = read_project_todos(workspace, relative_path=path, max_items=max_items, max_files=max_files)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "path": path or ".",
            "ok": False,
            "todos": {"shown": 0, "total": 0, "items": []},
            "files": {"scanned": 0, "total": 0},
            "truncated": False,
            "markers": [],
            "message": str(error),
        }
    todos = [item for item in metadata["todos"] if isinstance(item, dict)]
    return {
        "projectRoot": str(root),
        "path": str(metadata["path"]),
        "ok": bool(metadata["ok"]),
        "todos": {
            "shown": len(todos),
            "total": int(metadata["total"]),
            "items": todos,
        },
        "files": {
            "scanned": int(metadata["scanned_files"]),
            "total": int(metadata["total_files"]),
        },
        "truncated": bool(metadata["truncated"]),
        "markers": list(metadata["markers"]),
        "message": str(metadata["message"]),
    }
