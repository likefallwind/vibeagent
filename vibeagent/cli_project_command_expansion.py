from __future__ import annotations

from pathlib import Path

from .builtin_model_workflows import resolve_builtin_model_workflow
from .commands import parse_local_command
from .workspace_prompt_commands import expand_project_prompt_command
from .workspace_core import RunWorkspace


def expand_one_shot_project_command(
    project_root: Path,
    task: str,
    *,
    safe_mode: bool = False,
    bare_mode: bool = False,
    workspace: RunWorkspace | None = None,
) -> tuple[str, dict[str, object] | None]:
    builtin = resolve_builtin_model_workflow(parse_local_command(task), interactive=False)
    if builtin is not None:
        return builtin.task, builtin.metadata
    if safe_mode and task.strip().startswith("/"):
        raise ValueError("Custom commands and skill invocations are disabled by safe mode.")
    if bare_mode and task.strip().startswith("/") and workspace is None:
        raise ValueError("Custom commands and skill invocations are disabled by bare mode.")
    expanded = expand_code_task_project_command(project_root, task, workspace=workspace)
    if expanded is None:
        return task, None
    return str(expanded["prompt"]), project_command_task_metadata(expanded)


def expand_code_task_project_command(
    project_root: Path,
    task: str,
    *,
    workspace: RunWorkspace | None = None,
) -> dict[str, object] | None:
    stripped = task.strip()
    if not stripped.startswith("/") or parse_local_command(stripped) is not None:
        return None
    return expand_project_prompt_command(project_root, stripped, workspace=workspace)


def project_command_task_metadata(command: dict[str, object]) -> dict[str, object]:
    return {
        "source": command.get("task_source", "project_command"),
        "name": command["name"],
        "path": command["path"],
        "arguments": command["arguments"],
    }
