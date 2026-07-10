from __future__ import annotations

from pathlib import Path

from .workspace_prompt_commands import (
    format_project_prompt_commands as _format_project_prompt_commands,
    read_project_prompt_commands as _read_project_prompt_commands,
)


def get_custom_commands_report(max_commands: int = 100) -> dict[str, object]:
    return _read_project_prompt_commands(Path.cwd(), max_commands=max_commands)


def get_custom_commands_text(max_commands: int = 100) -> str:
    return _format_project_prompt_commands(Path.cwd(), max_commands=max_commands)
