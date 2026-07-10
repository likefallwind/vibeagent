from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from .agent_delegate_policy import CODE_DELEGATE_EXCLUDED_TOOL_NAMES, DELEGATE_TOOL_NAMES
from .tool_catalog_core import APPROVAL_REQUIRED_TOOL_NAMES
from .tool_definitions import AGENT_TOOL_DEFINITIONS
from .workspace_core import RunWorkspace
from .workspace_metadata_files import (
    has_symlink_component,
    parse_scalar_frontmatter,
    read_regular_file_bytes,
    unquote_scalar,
)


AGENT_ROOTS = ((".claude/agents", "claude"), (".agents/agents", "agents"))
AGENT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
MAX_AGENT_FILE_BYTES = 64_000
MAX_AGENT_SCAN = 500
KNOWN_TOOL_NAMES = frozenset(str(tool["name"]) for tool in AGENT_TOOL_DEFINITIONS)


def read_project_agents(workspace: RunWorkspace, max_agents: int = 100) -> dict[str, object]:
    if max_agents < 1 or max_agents > 500:
        raise ValueError("max_agents must be between 1 and 500.")
    agents = _discover_project_agents(workspace)
    shown = agents[:max_agents]
    return {
        "ok": True,
        "agents": shown,
        "total": len(agents),
        "truncated": len(agents) > len(shown),
        "invalid": sum(1 for agent in agents if not agent["available"]),
        "message": f"Found {len(agents)} project agent profile(s); {sum(1 for agent in agents if agent['available'])} available.",
    }


def read_project_agent(workspace: RunWorkspace, name: str) -> dict[str, object]:
    normalized = name.strip()
    if not AGENT_NAME_PATTERN.fullmatch(normalized):
        raise ValueError("agent name must use 1-64 letters, digits, dots, underscores, or hyphens.")
    matches = [agent for agent in _discover_project_agents(workspace) if agent["name"] == normalized]
    if not matches:
        raise ValueError(f"Project agent profile not found: {normalized}.")
    available = [agent for agent in matches if agent["available"]]
    if len(available) != 1:
        detail = "; ".join(str(agent["message"]) for agent in matches)
        raise ValueError(f"Project agent profile {normalized!r} is unavailable: {detail}")

    agent = available[0]
    path = workspace.root / str(agent["path"])
    raw = _read_agent_bytes(path)
    content = raw.decode("utf-8")
    metadata, body = _parse_agent_content(path, content)
    return {
        **agent,
        **metadata,
        "prompt": body,
        "bytes": len(raw),
        "message": f"Loaded project agent profile {normalized!r} from {agent['path']}.",
    }


def format_project_agent_catalog(workspace: RunWorkspace, max_agents: int = 20) -> str | None:
    metadata = read_project_agents(workspace, max_agents=max_agents)
    available = [agent for agent in metadata["agents"] if agent["available"]]
    if not available:
        return None
    lines = ["Available project agent profiles (metadata only; select one by exact name in delegate_task.agent):"]
    for agent in available:
        tools = agent.get("tools")
        tool_text = f", tools={','.join(str(name) for name in tools)}" if isinstance(tools, list) else ""
        lines.append(
            f"- {agent['name']}: {agent['description']} "
            f"(mode={agent['mode']}{tool_text}, {agent['path']})"
        )
    if metadata["truncated"]:
        lines.append(f"[{int(metadata['total']) - len(metadata['agents'])} additional agent profile(s) omitted]")
    return "\n".join(lines)


def _discover_project_agents(workspace: RunWorkspace) -> list[dict[str, object]]:
    discovered: list[dict[str, object]] = []
    for relative_root, source in AGENT_ROOTS:
        root = workspace.root / relative_root
        if not root.exists() or not root.is_dir() or has_symlink_component(workspace.root, root):
            continue
        try:
            children = sorted(root.iterdir(), key=lambda path: path.name)[:MAX_AGENT_SCAN]
        except OSError:
            continue
        for path in children:
            if path.suffix.lower() != ".md" or not AGENT_NAME_PATTERN.fullmatch(path.stem):
                continue
            relative_path = path.relative_to(workspace.root).as_posix()
            available, metadata, message = _inspect_agent_file(workspace.root, path)
            discovered.append(
                {
                    "name": path.stem,
                    "description": metadata.get("description", ""),
                    "mode": metadata.get("mode", "explore"),
                    "tools": metadata.get("tools"),
                    "path": relative_path,
                    "source": source,
                    "available": available,
                    "message": message,
                }
            )

    counts = Counter(str(agent["name"]) for agent in discovered)
    duplicates = {name for name, count in counts.items() if count > 1}
    for agent in discovered:
        if agent["name"] in duplicates:
            agent["available"] = False
            agent["message"] = f"Duplicate agent profile name {agent['name']!r} exists in multiple roots."
    return sorted(discovered, key=lambda agent: (str(agent["name"]), str(agent["source"])))


def _inspect_agent_file(root: Path, path: Path) -> tuple[bool, dict[str, object], str]:
    if has_symlink_component(root, path):
        return False, {}, "Agent profile path contains a symbolic link."
    if not path.is_file():
        return False, {}, "Agent profile is not a regular Markdown file."
    try:
        content = _read_agent_bytes(path).decode("utf-8")
        metadata, _ = _parse_agent_content(path, content)
    except UnicodeDecodeError as error:
        return False, {}, f"Agent profile is not valid UTF-8: {error}"
    except (OSError, ValueError) as error:
        return False, {}, str(error)
    return True, metadata, "Available."


def _parse_agent_content(path: Path, content: str) -> tuple[dict[str, object], str]:
    metadata, body = parse_scalar_frontmatter(
        content,
        frozenset({"name", "description", "mode", "tools"}),
    )
    name = str(metadata.get("name", "")).strip()
    description = str(metadata.get("description", "")).strip()
    mode = str(metadata.get("mode", "explore")).strip().lower()
    if not name or not description:
        raise ValueError("Agent profile frontmatter requires non-empty name and description fields.")
    if not AGENT_NAME_PATTERN.fullmatch(name):
        raise ValueError("Agent profile frontmatter name is invalid.")
    if name != path.stem:
        raise ValueError(f"Agent profile name {name!r} does not match filename {path.stem!r}.")
    if mode not in {"explore", "code"}:
        raise ValueError("Agent profile mode must be explore or code.")
    tools = _parse_tool_names(metadata.get("tools"))
    _validate_agent_tools(mode, tools)
    if not body.strip():
        raise ValueError("Agent profile body must contain a non-empty system prompt.")
    return {
        "name": name,
        "description": " ".join(description.split())[:500],
        "mode": mode,
        "tools": sorted(tools) if tools is not None else None,
    }, body.strip()


def _parse_tool_names(value: object) -> frozenset[str] | None:
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    names: list[str]
    if text.startswith("["):
        try:
            parsed = json.loads(text.replace("'", '"'))
        except json.JSONDecodeError as error:
            if not text.endswith("]"):
                raise ValueError(f"Agent profile tools must be a comma-separated or inline list: {error}") from error
            parsed = [unquote_scalar(item.strip()) for item in text[1:-1].split(",") if item.strip()]
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise ValueError("Agent profile tools list must contain strings only.")
        names = parsed
    else:
        names = text.split(",")
    normalized = frozenset(name.strip() for name in names if name.strip())
    if not normalized:
        raise ValueError("Agent profile tools must not be empty when declared.")
    return normalized


def _validate_agent_tools(mode: str, tools: frozenset[str] | None) -> None:
    if tools is None:
        return
    unknown = sorted(tools - KNOWN_TOOL_NAMES)
    if unknown:
        raise ValueError(f"Agent profile references unknown tool(s): {', '.join(unknown)}.")
    forbidden = sorted(tools & CODE_DELEGATE_EXCLUDED_TOOL_NAMES)
    if forbidden:
        raise ValueError(f"Agent profile references forbidden tool(s): {', '.join(forbidden)}.")
    if mode == "explore":
        unavailable = sorted(
            name
            for name in tools
            if (
                name not in DELEGATE_TOOL_NAMES and name != "finish"
            ) or name in APPROVAL_REQUIRED_TOOL_NAMES
        )
        if unavailable:
            raise ValueError(f"Explore agent profile references non-read-only tool(s): {', '.join(unavailable)}.")


def _read_agent_bytes(path: Path) -> bytes:
    return read_regular_file_bytes(path, max_bytes=MAX_AGENT_FILE_BYTES, label="Agent profile")
