from __future__ import annotations

from pathlib import Path

from .commands import parse_local_command
from .workspace_prompt_commands import expand_project_prompt_command


def expand_one_shot_project_command(project_root: Path, task: str) -> tuple[str, dict[str, object] | None]:
    expanded = expand_code_task_project_command(project_root, task)
    if expanded is None:
        return task, None
    return str(expanded["prompt"]), project_command_task_metadata(expanded)


def expand_code_task_project_command(project_root: Path, task: str) -> dict[str, object] | None:
    stripped = task.strip()
    if not stripped.startswith("/") or parse_local_command(stripped) is not None:
        return None
    return expand_project_prompt_command(project_root, stripped)


def project_command_task_metadata(command: dict[str, object]) -> dict[str, object]:
    return {
        "source": command.get("task_source", "project_command"),
        "name": command["name"],
        "path": command["path"],
        "arguments": command["arguments"],
    }
