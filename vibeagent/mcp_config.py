from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .mcp_protocol import MCP_HTTP_PROTOCOL_VERSION, MCP_STDIO_PROTOCOL_VERSION
from .workspace_core import RunWorkspace
from .workspace_resolve import resolve_inside_run


MCP_CONFIG_NAME = ".mcp.json"
MCP_CONFIG_MAX_BYTES = 100_000
MCP_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
ENV_REFERENCE_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
HTTP_HEADER_NAME_PATTERN = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
MCP_HTTP_PROTOCOL_VERSIONS = frozenset({MCP_STDIO_PROTOCOL_VERSION, MCP_HTTP_PROTOCOL_VERSION})
MCP_HTTP_DEFAULT_PROTOCOL_VERSION = MCP_HTTP_PROTOCOL_VERSION
MCP_HTTP_RESERVED_HEADERS = frozenset(
    {
        "accept",
        "content-length",
        "content-type",
        "host",
        "mcp-method",
        "mcp-name",
        "mcp-protocol-version",
        "mcp-session-id",
        "origin",
    }
)


@dataclass(frozen=True)
class McpServerConfig:
    name: str
    command: str
    args: list[str]
    cwd: str
    env: dict[str, str]
    config_path: str = MCP_CONFIG_NAME
    transport: str = "stdio"
    url: str = ""
    headers: dict[str, str] | None = None
    protocol_version: str = MCP_HTTP_DEFAULT_PROTOCOL_VERSION

    @property
    def argv(self) -> list[str]:
        return [self.command, *self.args]


def read_mcp_server_configs(workspace: RunWorkspace) -> list[McpServerConfig]:
    configs: list[McpServerConfig] = []
    seen: dict[str, str] = {}
    for path in mcp_config_paths(workspace):
        for config in _read_mcp_server_configs_from_path(workspace, path):
            if config.name in seen:
                raise ValueError(
                    f"MCP server {config.name!r} is defined in both {seen[config.name]} and {config.config_path}."
                )
            seen[config.name] = config.config_path
            configs.append(config)
    return sorted(configs, key=lambda config: config.name)


def mcp_config_paths(workspace: RunWorkspace) -> list[Path]:
    paths: list[Path] = []
    project_config = workspace.root / MCP_CONFIG_NAME
    if not workspace.strict_mcp_config and project_config.exists():
        paths.append(project_config)
    paths.extend(workspace.mcp_config_paths)
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(path)
    return deduped


def _read_mcp_server_configs_from_path(workspace: RunWorkspace, path: Path) -> list[McpServerConfig]:
    label = _config_path_label(workspace, path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file.")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError(f"{label} must be a regular file.")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(MCP_CONFIG_MAX_BYTES + 1)
    finally:
        os.close(descriptor)
    if len(raw) > MCP_CONFIG_MAX_BYTES:
        raise ValueError(f"{label} exceeds {MCP_CONFIG_MAX_BYTES} bytes.")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not parse {label}: {error}") from error
    if not isinstance(document, dict) or not isinstance(document.get("mcpServers", {}), dict):
        raise ValueError(f"{label} must contain an mcpServers object.")

    configs: list[McpServerConfig] = []
    for name, value in document.get("mcpServers", {}).items():
        configs.append(_parse_server_config(workspace, name, value, label))
    return configs


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


def expanded_mcp_headers(config: McpServerConfig) -> dict[str, str]:
    return {
        key: ENV_REFERENCE_PATTERN.sub(lambda match: os.environ.get(match.group(1), ""), value)
        for key, value in (config.headers or {}).items()
    }


def safe_mcp_endpoint(config: McpServerConfig) -> str:
    if not config.url:
        return ""
    parsed = urlsplit(config.url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _parse_server_config(workspace: RunWorkspace, name: object, value: object, config_path: str) -> McpServerConfig:
    if not isinstance(name, str) or not MCP_NAME_PATTERN.fullmatch(name):
        raise ValueError("MCP server names must use 1-64 letters, digits, dots, underscores, or hyphens.")
    if not isinstance(value, dict):
        raise ValueError(f"MCP server {name!r} configuration must be an object.")
    transport = value.get("type", "stdio")
    if transport not in {"stdio", "http"}:
        raise ValueError(f"MCP server {name!r} type must be 'stdio' or 'http'.")
    if transport == "http":
        return _parse_http_server_config(name, value, config_path)
    return _parse_stdio_server_config(workspace, name, value, config_path)


def _parse_stdio_server_config(
    workspace: RunWorkspace, name: str, value: dict[object, object], config_path: str
) -> McpServerConfig:
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
        config_path=config_path,
        transport="stdio",
    )


def _parse_http_server_config(name: str, value: dict[object, object], config_path: str) -> McpServerConfig:
    url = value.get("url")
    headers = value.get("headers", {})
    protocol_version = value.get("protocolVersion", MCP_HTTP_DEFAULT_PROTOCOL_VERSION)
    if not isinstance(url, str) or not url.strip():
        raise ValueError(f"MCP HTTP server {name!r} requires a non-empty url.")
    url = url.strip()
    if len(url) > 2_048:
        raise ValueError(f"MCP HTTP server {name!r} url is too long.")
    if any(character.isspace() or ord(character) < 0x20 for character in url):
        raise ValueError(f"MCP HTTP server {name!r} url must not contain whitespace or control characters.")
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"MCP HTTP server {name!r} url must use http or https and include a host.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"MCP HTTP server {name!r} url must not include credentials.")
    if parsed.fragment:
        raise ValueError(f"MCP HTTP server {name!r} url must not include a fragment.")
    if not isinstance(headers, dict) or any(not isinstance(key, str) or not isinstance(item, str) for key, item in headers.items()):
        raise ValueError(f"MCP HTTP server {name!r} headers must map string names to string values.")
    if len(headers) > 50:
        raise ValueError(f"MCP HTTP server {name!r} has too many headers.")
    normalized_names: set[str] = set()
    for key, item in headers.items():
        lowered = key.lower()
        if not HTTP_HEADER_NAME_PATTERN.fullmatch(key) or lowered in normalized_names:
            raise ValueError(f"MCP HTTP server {name!r} has an invalid or duplicate header name: {key!r}.")
        if lowered in MCP_HTTP_RESERVED_HEADERS or lowered.startswith("mcp-param-"):
            raise ValueError(f"MCP HTTP server {name!r} cannot override reserved header {key!r}.")
        if len(key) > 128 or len(item) > 8_192 or "\r" in item or "\n" in item:
            raise ValueError(f"MCP HTTP server {name!r} has an invalid header value for {key!r}.")
        normalized_names.add(lowered)
    if protocol_version not in MCP_HTTP_PROTOCOL_VERSIONS:
        raise ValueError(
            f"MCP HTTP server {name!r} protocolVersion must be one of {sorted(MCP_HTTP_PROTOCOL_VERSIONS)}."
        )
    return McpServerConfig(
        name=name,
        command="",
        args=[],
        cwd=".",
        env={},
        config_path=config_path,
        transport="http",
        url=url,
        headers=dict(headers),
        protocol_version=str(protocol_version),
    )


def _config_path_label(workspace: RunWorkspace, path: Path) -> str:
    try:
        return path.resolve().relative_to(workspace.root).as_posix()
    except ValueError:
        return path.resolve().as_posix()
