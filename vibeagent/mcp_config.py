from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_resolve import resolve_inside_run


MCP_CONFIG_NAME = ".mcp.json"
MCP_CONFIG_MAX_BYTES = 100_000
MCP_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
ENV_REFERENCE_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass(frozen=True)
class McpServerConfig:
    name: str
    command: str
    args: list[str]
    cwd: str
    env: dict[str, str]

    @property
    def argv(self) -> list[str]:
        return [self.command, *self.args]


def read_mcp_server_configs(workspace: RunWorkspace) -> list[McpServerConfig]:
    path = workspace.root / MCP_CONFIG_NAME
    if not path.exists():
        return []
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{MCP_CONFIG_NAME} must be a regular non-symlink file.")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError(f"{MCP_CONFIG_NAME} must be a regular file.")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(MCP_CONFIG_MAX_BYTES + 1)
    finally:
        os.close(descriptor)
    if len(raw) > MCP_CONFIG_MAX_BYTES:
        raise ValueError(f"{MCP_CONFIG_NAME} exceeds {MCP_CONFIG_MAX_BYTES} bytes.")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not parse {MCP_CONFIG_NAME}: {error}") from error
    if not isinstance(document, dict) or not isinstance(document.get("mcpServers", {}), dict):
        raise ValueError(f"{MCP_CONFIG_NAME} must contain an mcpServers object.")

    configs: list[McpServerConfig] = []
    for name, value in document.get("mcpServers", {}).items():
        configs.append(_parse_server_config(workspace, name, value))
    return sorted(configs, key=lambda config: config.name)


def get_mcp_server_config(workspace: RunWorkspace, name: str) -> McpServerConfig:
    matches = [config for config in read_mcp_server_configs(workspace) if config.name == name]
    if not matches:
        raise ValueError(f"MCP server not found: {name}.")
    return matches[0]


def expanded_mcp_environment(config: McpServerConfig) -> dict[str, str]:
    environment = dict(os.environ)
    for key, value in config.env.items():
        environment[key] = ENV_REFERENCE_PATTERN.sub(lambda match: os.environ.get(match.group(1), ""), value)
    return environment


def _parse_server_config(workspace: RunWorkspace, name: object, value: object) -> McpServerConfig:
    if not isinstance(name, str) or not MCP_NAME_PATTERN.fullmatch(name):
        raise ValueError("MCP server names must use 1-64 letters, digits, dots, underscores, or hyphens.")
    if not isinstance(value, dict):
        raise ValueError(f"MCP server {name!r} configuration must be an object.")
    command = value.get("command")
    args = value.get("args", [])
    cwd = value.get("cwd", ".")
    env = value.get("env", {})
    if not isinstance(command, str) or not command.strip():
        raise ValueError(f"MCP server {name!r} requires a non-empty command.")
    if not isinstance(args, list) or any(not isinstance(arg, str) for arg in args):
        raise ValueError(f"MCP server {name!r} args must be a list of strings.")
    if len(args) > 100:
        raise ValueError(f"MCP server {name!r} has too many args.")
    if not isinstance(cwd, str) or not cwd.strip():
        raise ValueError(f"MCP server {name!r} cwd must be a non-empty project-relative path.")
    resolved_cwd = resolve_inside_run(workspace.root, cwd)
    if not resolved_cwd.is_dir():
        raise ValueError(f"MCP server {name!r} cwd is not a directory: {cwd}.")
    if not isinstance(env, dict) or any(not isinstance(key, str) or not isinstance(item, str) for key, item in env.items()):
        raise ValueError(f"MCP server {name!r} env must map string names to string values.")
    return McpServerConfig(
        name=name,
        command=command.strip(),
        args=list(args),
        cwd=resolved_cwd.relative_to(workspace.root).as_posix() or ".",
        env=dict(env),
    )
