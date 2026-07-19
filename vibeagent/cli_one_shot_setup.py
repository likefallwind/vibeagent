from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .cli_mcp_args import resolve_mcp_config_paths
from .cli_one_shot_input import resolve_one_shot_code_task


@dataclass(frozen=True)
class OneShotProjectSetup:
    task: str
    task_metadata: dict[str, object] | None
    mcp_config_paths: tuple[Path, ...]


def resolve_one_shot_project_setup(
    task: str,
    *,
    request_mode: str,
    project_root: Path,
    mcp_config_paths: list[str] | tuple[str, ...] | None,
    resolve_code_task_func: Callable[..., tuple[str, dict[str, object] | None]] = resolve_one_shot_code_task,
    resolve_mcp_config_paths_func: Callable[[Path, list[str] | tuple[str, ...] | None], tuple[Path, ...]] = (
        resolve_mcp_config_paths
    ),
) -> OneShotProjectSetup:
    resolved_task, task_metadata = resolve_code_task_func(
        task,
        request_mode=request_mode,
        project_root=project_root,
    )
    resolved_mcp_config_paths = resolve_mcp_config_paths_func(project_root, mcp_config_paths)
    return OneShotProjectSetup(
        task=resolved_task,
        task_metadata=task_metadata,
        mcp_config_paths=resolved_mcp_config_paths,
    )
