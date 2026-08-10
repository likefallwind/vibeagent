from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat
from tempfile import NamedTemporaryFile
from typing import Literal, cast

from .mcp_user_config import CLAUDE_USER_CONFIG_MAX_BYTES, MAX_SCOPED_MCP_SERVERS
from .user_paths import user_home
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes


McpScope = Literal["local", "project", "user"]
MCP_SCOPES = frozenset({"local", "project", "user"})
PROJECT_MCP_MAX_BYTES = 100_000


@dataclass(frozen=True)
class McpScopeSnapshot:
    path: Path
    payload: dict[str, object]
    mode: int
    existed: bool


def validate_mcp_scope(value: str) -> McpScope:
    if value not in MCP_SCOPES:
        raise ValueError("MCP scope must be local, project, or user.")
    return cast(McpScope, value)


def read_mcp_scope_servers(root: Path, scope: McpScope) -> dict[str, object]:
    snapshot = _capture_scope(root, scope)
    configured = _scope_server_map(snapshot.payload, root, scope, create=False)
    return dict(configured or {})


def write_mcp_scope_server(
    root: Path,
    scope: McpScope,
    name: str,
    server: dict[str, object],
    *,
    replace_existing: bool = False,
) -> None:
    snapshot = _capture_scope(root, scope)
    configured = _scope_server_map(snapshot.payload, root, scope, create=True)
    assert configured is not None
    if name in configured and not replace_existing:
        raise ValueError(
            f"MCP server {name!r} already exists at {scope} scope; use --replace to overwrite it."
        )
    if name not in configured and len(configured) >= MAX_SCOPED_MCP_SERVERS:
        raise ValueError(
            f"MCP {scope} scope exceeds {MAX_SCOPED_MCP_SERVERS} servers."
        )
    configured[name] = server
    _write_snapshot(snapshot, scope)


def remove_mcp_scope_server(root: Path, scope: McpScope, name: str) -> None:
    snapshot = _capture_scope(root, scope)
    configured = _scope_server_map(snapshot.payload, root, scope, create=False)
    if configured is None or name not in configured:
        raise ValueError(f"MCP server {name!r} is not configured at {scope} scope.")
    configured.pop(name)
    _prune_empty_scope(snapshot.payload, root, scope)
    _write_snapshot(snapshot, scope)


def mcp_scope_source(root: Path, scope: McpScope) -> str:
    if scope == "user":
        return "~/.claude.json#mcpServers"
    if scope == "local":
        return "~/.claude.json#projects[current].mcpServers"
    return ".mcp.json"


def _capture_scope(root: Path, scope: McpScope) -> McpScopeSnapshot:
    project_root = root.resolve()
    home = user_home()
    path = project_root / ".mcp.json" if scope == "project" else home / ".claude.json"
    boundary = project_root if scope == "project" else home
    mode = 0o644 if scope == "project" else 0o600
    max_bytes = PROJECT_MCP_MAX_BYTES if scope == "project" else CLAUDE_USER_CONFIG_MAX_BYTES
    if path.is_symlink() or (path.exists() and has_symlink_component(boundary, path)):
        raise ValueError(f"{_scope_label(scope)} must be a regular non-symlink file.")
    if not path.exists():
        return McpScopeSnapshot(path, {}, mode, False)
    if not path.is_file():
        raise ValueError(f"{_scope_label(scope)} must be a regular file.")
    raw = read_regular_file_bytes(path, max_bytes=max_bytes, label=_scope_label(scope))
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not parse {_scope_label(scope)}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{_scope_label(scope)} must contain a JSON object.")
    return McpScopeSnapshot(
        path,
        payload,
        stat.S_IMODE(path.stat().st_mode),
        True,
    )


def _scope_server_map(
    payload: dict[str, object],
    root: Path,
    scope: McpScope,
    *,
    create: bool,
) -> dict[str, object] | None:
    if scope in {"user", "project"}:
        return _object_child(payload, "mcpServers", create=create)
    projects = _object_child(payload, "projects", create=create)
    if projects is None:
        return None
    project_key = root.resolve().as_posix()
    project = _object_child(projects, project_key, create=create)
    if project is None:
        return None
    return _object_child(project, "mcpServers", create=create)


def _object_child(
    payload: dict[str, object],
    key: str,
    *,
    create: bool,
) -> dict[str, object] | None:
    value = payload.get(key)
    if value is None:
        if not create:
            return None
        selected: dict[str, object] = {}
        payload[key] = selected
        return selected
    if not isinstance(value, dict):
        raise ValueError(f"MCP configuration field {key!r} must be an object.")
    return value


def _prune_empty_scope(payload: dict[str, object], root: Path, scope: McpScope) -> None:
    if scope in {"user", "project"}:
        if payload.get("mcpServers") == {}:
            payload.pop("mcpServers", None)
        return
    projects = payload.get("projects")
    if not isinstance(projects, dict):
        return
    key = root.resolve().as_posix()
    project = projects.get(key)
    if not isinstance(project, dict):
        return
    if project.get("mcpServers") == {}:
        project.pop("mcpServers", None)
    if not project:
        projects.pop(key, None)
    if not projects:
        payload.pop("projects", None)


def _write_snapshot(snapshot: McpScopeSnapshot, scope: McpScope) -> None:
    path = snapshot.path
    boundary = path.parent if scope == "project" else user_home()
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError(f"Refusing to write MCP configuration through a symbolic link: {path}")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if has_symlink_component(boundary, path):
        raise ValueError(f"Refusing to write MCP configuration through a symbolic link: {path}")
    encoded = (
        json.dumps(snapshot.payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    max_bytes = PROJECT_MCP_MAX_BYTES if scope == "project" else CLAUDE_USER_CONFIG_MAX_BYTES
    if len(encoded) > max_bytes:
        raise ValueError(f"{_scope_label(scope)} exceeds {max_bytes} bytes.")
    with NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
        handle.write(encoded)
        temporary = Path(handle.name)
    try:
        os.chmod(temporary, snapshot.mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _scope_label(scope: McpScope) -> str:
    return ".mcp.json" if scope == "project" else "~/.claude.json"


__all__ = [
    "MCP_SCOPES",
    "McpScope",
    "mcp_scope_source",
    "read_mcp_scope_servers",
    "remove_mcp_scope_server",
    "validate_mcp_scope",
    "write_mcp_scope_server",
]
