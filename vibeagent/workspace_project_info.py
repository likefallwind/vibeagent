from __future__ import annotations

from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_environment_info import read_environment_info, read_runtime_tool_info, runtime_tool_commands
from .workspace_project_instructions import (
    project_instruction_scope,
    project_instruction_sort_key,
    read_path_instruction_context,
    read_project_instruction_sources,
    read_project_instructions,
)
from .workspace_project_commands import format_command_hint, read_project_command_hints, read_project_commands
from .workspace_project_manifests import read_project_manifests
from .workspace_project_metadata import (
    SHELL_BUILTINS,
    empty_project_manifest,
    first_command_executable,
    is_shell_assignment,
    manifest_group_items,
    missing_command_tool,
    normalize_manifest_group_items,
    read_makefile_targets,
    read_package_json_manifest,
    read_package_json_scripts,
    read_pyproject_manifest,
    read_pyproject_scripts,
    stringify_manifest_value,
)
from .workspace_project_todos import read_project_todos
from .workspace_search_files import list_files, list_search_files


def read_workspace_snapshot(workspace: RunWorkspace, max_bytes: int = 12_000) -> str:
    # Build a bounded project file listing so prompts remain informative but not oversized.
    files = list_files(workspace.root)
    if not files:
        return "No project files found."

    used = 0
    chunks: list[str] = []
    for file in files[:120]:
        content = file
        remaining = max_bytes - used
        if remaining <= 0:
            chunks.append("\n[workspace snapshot truncated]")
            break

        shown = content[:remaining]
        used += len(shown)
        chunks.append(shown)

    return "\n\n".join(chunks)
