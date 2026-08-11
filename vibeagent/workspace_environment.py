from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import re
from typing import Mapping

from .ide_context import strip_ide_context_environment
from .workspace_core import RunWorkspace, create_local_workspace
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes
from .workspace_settings_sources import claude_settings_files


MAX_SETTINGS_BYTES = 128_000
MAX_ENVIRONMENT_VARIABLES = 256
MAX_ENVIRONMENT_VALUE_CHARS = 32_000
ENVIRONMENT_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


@dataclass(frozen=True)
class WorkspaceEnvironment:
    variables: dict[str, str]
    sources: tuple[str, ...] = ()
    error: str | None = None


def read_workspace_environment(workspace: RunWorkspace) -> WorkspaceEnvironment:
    variables: dict[str, str] = {}
    sources: list[str] = []
    try:
        for config in claude_settings_files(workspace):
            if not config.trusted and not workspace.project_config_trusted:
                continue
            if not config.path.exists():
                continue
            payload = _read_settings(config.boundary, config.path, config.source)
            environment = payload.get("env")
            if environment is None:
                continue
            sources.append(config.source)
            variables.update(_parse_environment(environment, config.source))
            if len(variables) > MAX_ENVIRONMENT_VARIABLES:
                raise ValueError(
                    f"Workspace settings env exceeds {MAX_ENVIRONMENT_VARIABLES} variables."
                )
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        return WorkspaceEnvironment({}, tuple(sources), str(error))
    return WorkspaceEnvironment(variables, tuple(sources))


def workspace_process_environment(
    workspace: RunWorkspace,
    host_environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    configured = read_workspace_environment(workspace)
    if configured.error is not None:
        raise ValueError(configured.error)
    environment = dict(configured.variables)
    environment.update(os.environ if host_environment is None else host_environment)
    return strip_ide_context_environment(environment)


def workspace_process_environment_from_root(
    root: str | Path,
    *,
    trust_project_settings: bool = False,
    host_environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    workspace = create_local_workspace(root, "local-settings-environment")
    if trust_project_settings and not workspace.project_config_trusted:
        workspace = replace(workspace, project_config_trusted=True)
    return workspace_process_environment(workspace, host_environment)


def _read_settings(boundary: Path, path: Path, source: str) -> dict[str, object]:
    if has_symlink_component(boundary, path):
        raise ValueError(f"{source} contains a symbolic link.")
    raw = read_regular_file_bytes(path, max_bytes=MAX_SETTINGS_BYTES, label=source)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{source} must contain a JSON object.")
    return payload


def _parse_environment(value: object, source: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"{source} env must be an object.")
    if len(value) > MAX_ENVIRONMENT_VARIABLES:
        raise ValueError(
            f"{source} env exceeds {MAX_ENVIRONMENT_VARIABLES} variables."
        )
    parsed: dict[str, str] = {}
    for name, item in value.items():
        if not isinstance(name, str) or not ENVIRONMENT_NAME_PATTERN.fullmatch(name):
            raise ValueError(f"{source} env contains an invalid variable name.")
        if (
            not isinstance(item, str)
            or "\x00" in item
            or len(item) > MAX_ENVIRONMENT_VALUE_CHARS
        ):
            raise ValueError(
                f"{source} env.{name} must be a string of at most "
                f"{MAX_ENVIRONMENT_VALUE_CHARS} characters without NUL bytes."
            )
        parsed[name] = item
    return parsed


__all__ = [
    "WorkspaceEnvironment",
    "read_workspace_environment",
    "workspace_process_environment",
    "workspace_process_environment_from_root",
]
