from __future__ import annotations

from pathlib import Path

from .command_parsing import parse_optional_single_path_argument
from .smart_code_common import (
    commands_attr as _commands_attr,
    execute_action_for_commands as _execute_action,
    plain_data as _plain_data,
)
from .smart_code_formatting import format_code_deps_report_text
from .types import CodeDependenciesAction
from .workspace_core import RunWorkspace


def get_code_deps_report(
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
            "message": f"Usage: /code-deps [path]\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-code-deps", session_dir=root / ".vibeagent" / "sessions" / "local-code-deps")
    observation = _execute_action(
        workspace,
        CodeDependenciesAction(type="code_dependencies", path=path, max_files=max_files, max_imports=max_imports),
    )
    if observation.kind != "code_dependencies":
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


def get_code_deps_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_files: int = 100,
    max_imports: int = 500,
) -> str:
    get_report = _commands_attr("get_code_deps_report", get_code_deps_report)
    formatter = _commands_attr("format_code_deps_report_text", format_code_deps_report_text)
    return formatter(get_report(project_root, argument, max_files=max_files, max_imports=max_imports))
