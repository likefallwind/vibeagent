from __future__ import annotations

from pathlib import Path

from .command_parsing import parse_optional_single_path_argument
from .edit_commands import format_check_location
from .smart_code_common import (
    commands_attr as _commands_attr,
    execute_action_for_commands as _execute_action,
    plain_data as _plain_data,
)
from .local_command_workspace import local_command_workspace
from .types import PythonCheckAction, PythonDependenciesAction


def get_python_check_report(project_root: str | Path = ".", argument: str | None = None, max_files: int = 200) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        path = parse_optional_single_path_argument(argument)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": ".",
            "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "maxFiles": max_files,
            "message": f"Usage: /python-check [path]\nError: {error}",
        }
    workspace = local_command_workspace(root, "local-python-check")
    observation = _execute_action(workspace, PythonCheckAction(type="python_check", path=path, max_files=max_files))
    if observation.kind != "python_check":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path or ".",
            "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "maxFiles": max_files,
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path or ".",
        "files": {
            "shown": len(observation.files),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": [_plain_data(item) for item in observation.files],
        },
        "maxFiles": max_files,
        "message": observation.message,
    }


def format_python_check_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = files.get("items") if isinstance(files.get("items"), list) else []
    lines = [
        "Python check:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or '.'}",
        f"  files: {files.get('shown', 0)}/{files.get('total', 0)}",
        f"  truncated: {'yes' if bool(files.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if items:
        lines.append("  items:")
        for item in items:
            if isinstance(item, dict):
                location = format_check_location(item.get("line"), item.get("column"))
                lines.append(f"    - {item.get('path')}: {'ok' if bool(item.get('ok')) else 'failed'}{location} - {item.get('message')}")
    else:
        lines.append("  items: none")
    return "\n".join(lines)


def get_python_deps_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_files: int = 100,
    max_imports: int = 500,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        path = parse_optional_single_path_argument(argument)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": ".",
            "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "maxFiles": max_files,
            "maxImports": max_imports,
            "message": f"Usage: /python-deps [path]\nError: {error}",
        }
    workspace = local_command_workspace(root, "local-python-deps")
    observation = _execute_action(
        workspace,
        PythonDependenciesAction(type="python_dependencies", path=path, max_files=max_files, max_imports=max_imports),
    )
    if observation.kind != "python_dependencies":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path or ".",
            "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "maxFiles": max_files,
            "maxImports": max_imports,
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path or ".",
        "files": {
            "shown": len(observation.files),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": [_plain_data(item) for item in observation.files],
        },
        "maxFiles": max_files,
        "maxImports": max_imports,
        "message": observation.message,
    }


def format_python_deps_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = files.get("items") if isinstance(files.get("items"), list) else []
    lines = [
        "Python dependencies:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or '.'}",
        f"  files: {files.get('shown', 0)}/{files.get('total', 0)}",
        f"  truncated: {'yes' if bool(files.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if items:
        lines.append("  files:")
        for item in items:
            if not isinstance(item, dict):
                continue
            local_modules = item.get("local_modules") if isinstance(item.get("local_modules"), list) else []
            external_modules = item.get("external_modules") if isinstance(item.get("external_modules"), list) else []
            imports = item.get("imports") if isinstance(item.get("imports"), list) else []
            lines.append(f"    - {item.get('path')} ({item.get('module') or '.'}): {'ok' if bool(item.get('ok')) else 'failed'} - {item.get('message')}")
            lines.append(f"      local: {', '.join(str(value) for value in local_modules) if local_modules else '-'}")
            lines.append(f"      external: {', '.join(str(value) for value in external_modules) if external_modules else '-'}")
            if imports:
                lines.append("      imports:")
                for import_ref in imports:
                    if not isinstance(import_ref, dict):
                        continue
                    name = import_ref.get("name") or "-"
                    alias = f" as {import_ref.get('alias')}" if import_ref.get("alias") else ""
                    module = import_ref.get("module") or "."
                    lines.append(
                        f"        - line {import_ref.get('line')} {import_ref.get('kind')}: {module}.{name}{alias} "
                        f"-> {import_ref.get('target')} local={'yes' if bool(import_ref.get('local')) else 'no'}"
                    )
            else:
                lines.append("      imports: none")
    else:
        lines.append("  files: none")
    return "\n".join(lines)


def get_python_check_text(project_root: str | Path = ".", argument: str | None = None, max_files: int = 200) -> str:
    get_report = _commands_attr("get_python_check_report", get_python_check_report)
    formatter = _commands_attr("format_python_check_report_text", format_python_check_report_text)
    return formatter(get_report(project_root, argument, max_files=max_files))


def get_python_deps_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_files: int = 100,
    max_imports: int = 500,
) -> str:
    get_report = _commands_attr("get_python_deps_report", get_python_deps_report)
    formatter = _commands_attr("format_python_deps_report_text", format_python_deps_report_text)
    return formatter(get_report(project_root, argument, max_files=max_files, max_imports=max_imports))
