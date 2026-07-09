from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .command_parsing import parse_optional_single_path_argument
from .types import ConfigCheckAction
from .workspace_core import RunWorkspace


def plain_data(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, list):
        return [plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): plain_data(item) for key, item in value.items()}
    return value


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def get_config_check_text(project_root: str | Path = ".", argument: str | None = None, max_files: int = 200) -> str:
    return format_config_check_report_text(get_config_check_report(project_root, argument, max_files=max_files))


def get_config_check_report(project_root: str | Path = ".", argument: str | None = None, max_files: int = 200) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        path = parse_optional_single_path_argument(argument)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": argument or ".",
            "files": {"shown": 0, "total": 0, "items": []},
            "truncated": False,
            "message": f"Usage: /config-check [path]\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-config-check", session_dir=root / ".vibeagent" / "sessions" / "local-config-check")
    observation = _execute_action(workspace, ConfigCheckAction(type="config_check", path=path, max_files=max_files))
    if observation.kind != "config_check":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path or ".",
            "files": {"shown": 0, "total": 0, "items": []},
            "truncated": False,
            "message": f"Unexpected observation: {observation.kind}",
        }

    files = [plain_data(item) for item in observation.files]
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path or ".",
        "files": {
            "shown": len(files),
            "total": observation.total,
            "items": files,
        },
        "truncated": observation.truncated,
        "message": observation.message,
    }


def format_config_check_report_text(report: dict[str, object]) -> str:
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = [item for item in files.get("items", []) if isinstance(item, dict)] if isinstance(files.get("items"), list) else []
    lines = [
        "Config check:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or '.'}",
        f"  files: {int(files.get('shown', len(items)) or 0)}/{int(files.get('total', len(items)) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]
    if items:
        lines.append("  items:")
        for item in items:
            line = item.get("line") if isinstance(item.get("line"), int) else None
            column = item.get("column") if isinstance(item.get("column"), int) else None
            location = format_check_location(line, column)
            status = "ok" if bool(item.get("ok")) else "failed"
            lines.append(f"    - {item.get('path')} ({item.get('format')}): {status}{location} - {item.get('message')}")
    else:
        lines.append("  items: none")
    return "\n".join(lines)


def format_check_location(line: int | None, column: int | None) -> str:
    if line is None:
        return ""
    if column is None:
        return f" at line {line}"
    return f" at line {line}, column {column}"
