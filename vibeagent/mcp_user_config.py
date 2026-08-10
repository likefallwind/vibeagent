from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Literal

from .user_paths import user_home
from .workspace_core import RunWorkspace
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes


CLAUDE_USER_CONFIG_MAX_BYTES = 2_000_000
MAX_SCOPED_MCP_SERVERS = 100


@dataclass(frozen=True)
class ScopedMcpDocument:
    document: dict[str, object]
    source: str
    scope: Literal["user", "local"]


def read_user_mcp_documents(
    workspace: RunWorkspace,
) -> tuple[ScopedMcpDocument, ...]:
    home = user_home()
    path = home / ".claude.json"
    if not path.exists():
        return ()
    if has_symlink_component(home, path):
        raise ValueError("~/.claude.json contains a symbolic link.")
    raw = read_regular_file_bytes(
        path,
        max_bytes=CLAUDE_USER_CONFIG_MAX_BYTES,
        label="~/.claude.json",
    )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not parse ~/.claude.json: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("~/.claude.json must contain a JSON object.")

    documents: list[ScopedMcpDocument] = []
    user_servers = _server_map(payload.get("mcpServers"), "~/.claude.json mcpServers")
    if user_servers:
        documents.append(
            ScopedMcpDocument(
                {"mcpServers": user_servers},
                "~/.claude.json#mcpServers",
                "user",
            )
        )

    projects = payload.get("projects", {})
    if not isinstance(projects, dict):
        raise ValueError("~/.claude.json projects must be an object.")
    project = projects.get(workspace.root.resolve().as_posix())
    if project is not None:
        if not isinstance(project, dict):
            raise ValueError("~/.claude.json current project entry must be an object.")
        local_servers = _server_map(
            project.get("mcpServers"),
            "~/.claude.json current project mcpServers",
        )
        if local_servers:
            documents.append(
                ScopedMcpDocument(
                    {"mcpServers": local_servers},
                    "~/.claude.json#projects[current].mcpServers",
                    "local",
                )
            )
    return tuple(documents)


def _server_map(value: object, label: str) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object.")
    if len(value) > MAX_SCOPED_MCP_SERVERS:
        raise ValueError(
            f"{label} exceeds {MAX_SCOPED_MCP_SERVERS} servers."
        )
    return value


__all__ = ["ScopedMcpDocument", "read_user_mcp_documents"]
