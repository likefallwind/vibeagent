from __future__ import annotations

from pathlib import Path

from .plugin_runtime import (
    PluginComponentFile,
    enabled_plugin_component_files,
    expand_plugin_path_variables,
    plugin_component_path_reference,
)
from .plugin_store import read_installed_plugin_manifest
from .scoped_component_selection import select_preferred_components
from .user_paths import user_home
from .workspace_agent_profile_parser import AGENT_NAME_PATTERN, AGENT_REFERENCE_PATTERN, parse_agent_content
from .workspace_core import RunWorkspace
from .workspace_metadata_files import (
    has_symlink_component,
    read_regular_file_bytes,
)
from .workspace_skills import read_project_skills


AGENT_ROOTS = ((".claude/agents", "claude"), (".agents/agents", "agents"))
MAX_AGENT_FILE_BYTES = 64_000
MAX_AGENT_SCAN = 500
MAX_AGENT_SCAN_DEPTH = 8


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
    if not AGENT_REFERENCE_PATTERN.fullmatch(normalized):
        raise ValueError("agent name must use a valid optional plugin namespace and 1-64 character name.")
    matches = [agent for agent in _discover_project_agents(workspace) if agent["name"] == normalized]
    if not matches:
        raise ValueError(f"Project agent profile not found: {normalized}.")
    available = [agent for agent in matches if agent["available"]]
    if len(available) != 1:
        detail = "; ".join(str(agent["message"]) for agent in matches)
        raise ValueError(f"Project agent profile {normalized!r} is unavailable: {detail}")

    agent = available[0]
    if agent["source"] == "cli":
        profile = next(
            profile for profile in workspace.dynamic_agent_profiles if profile.name == normalized
        )
        return {
            **profile.metadata(),
            **agent,
            "prompt": profile.prompt,
            "bytes": len(profile.prompt.encode("utf-8")),
            "message": f"Loaded invocation-scoped agent profile {normalized!r} from --agents.",
        }
    path = workspace.root / str(agent["path"])
    raw = _read_agent_bytes(path)
    content = raw.decode("utf-8")
    metadata, body = parse_agent_content(path, content)
    if str(agent["source"]).startswith("plugin:"):
        plugin = str(agent["source"]).removeprefix("plugin:")
        manifest = read_installed_plugin_manifest(
            workspace.root,
            plugin,
        )
        body = expand_plugin_path_variables(
            body,
            PluginComponentFile(plugin, "agent", path, manifest.root),
            workspace,
        )
    return {
        **metadata,
        **agent,
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
        denied = agent.get("disallowed_tools")
        denied_text = f", disallowedTools={','.join(str(name) for name in denied)}" if denied else ""
        skills = agent.get("skills")
        skill_text = f", skills={','.join(str(name) for name in skills)}" if skills else ""
        turn_text = f", maxTurns={agent['max_turns']}" if agent.get("max_turns") is not None else ""
        model_text = f", model={agent['model']}" if agent.get("model") is not None else ""
        effort_text = f", effort={agent['effort']}" if agent.get("effort") is not None else ""
        memory_text = f", memory={agent['memory']}" if agent.get("memory") is not None else ""
        isolation_text = f", isolation={agent['isolation']}" if agent.get("isolation") is not None else ""
        permission_text = (
            f", permissionMode={agent['permission_mode']}"
            if agent.get("permission_mode") is not None
            else ""
        )
        background_text = ", background=true" if agent.get("background") else ""
        mcp_text = (
            f", mcpServers={','.join(str(name) for name in agent['mcp_server_names'])}"
            if agent.get("mcp_server_names")
            else ""
        )
        lines.append(
            f"- {agent['name']}: {agent['description']} "
            f"(mode={agent['mode']}{model_text}{effort_text}{tool_text}{denied_text}{skill_text}{turn_text}{memory_text}{isolation_text}{permission_text}{background_text}{mcp_text}, {agent['path']})"
        )
    if metadata["truncated"]:
        lines.append(f"[{int(metadata['total']) - len(metadata['agents'])} additional agent profile(s) omitted]")
    return "\n".join(lines)


def _discover_project_agents(workspace: RunWorkspace) -> list[dict[str, object]]:
    if workspace.safe_mode:
        return []
    discovered: list[dict[str, object]] = [
        {
            **profile.catalog_metadata(),
            "path": f"<cli --agents:{profile.name}>",
            "source": "cli",
            "available": True,
            "message": "Available from --agents for this invocation.",
        }
        for profile in workspace.dynamic_agent_profiles
    ]
    home = user_home()
    roots = (
        []
        if workspace.bare_mode
        else [
            *((workspace.root / relative_root, source) for relative_root, source in AGENT_ROOTS),
            (home / ".claude/agents", "user"),
        ]
    )
    for root, source in roots:
        boundary = workspace.root if source != "user" else home
        if not root.exists() or not root.is_dir() or has_symlink_component(boundary, root):
            continue
        for path in _agent_files(root):
            relative_path = plugin_component_path_reference(workspace.root, path)
            available, metadata, message = _inspect_agent_file(boundary, path)
            discovered.append(
                {
                    "name": path.stem,
                    **_catalog_profile_metadata(metadata),
                    "path": relative_path,
                    "source": source,
                    "available": available,
                    "message": message,
                }
            )

    for component in enabled_plugin_component_files(workspace, "agent"):
        path = component.path
        relative_path = plugin_component_path_reference(workspace.root, path)
        available, metadata, message = _inspect_agent_file(component.plugin_root, path)
        declared_name = str(metadata.get("name") or path.stem)
        skills = metadata.get("skills", [])
        namespaced_skills = [
            str(name) if ":" in str(name) else f"{component.plugin}:{name}"
            for name in skills
        ] if isinstance(skills, list) else []
        plugin_metadata = _catalog_profile_metadata(metadata, skills=namespaced_skills)
        plugin_metadata.update(
            {
                "permission_mode": None,
                "mcp_server_names": [],
                "has_hooks": False,
            }
        )
        discovered.append(
            {
                "name": f"{component.plugin}:{declared_name}",
                **plugin_metadata,
                "path": relative_path,
                "source": component.source,
                "available": available,
                "message": message,
            }
        )

    available_skills = {
        str(skill["name"])
        for skill in read_project_skills(workspace, max_skills=500)["skills"]
        if skill["available"]
    }
    for agent in discovered:
        skills = agent.get("skills")
        if not agent["available"] or not isinstance(skills, list):
            continue
        missing = sorted(str(name) for name in skills if name not in available_skills)
        if missing:
            agent["available"] = False
            agent["message"] = f"Agent profile references unavailable skill(s): {', '.join(missing)}."

    selected = select_preferred_components(
        discovered,
        source_priority=_agent_source_priority,
        duplicate_message=lambda name: (
            f"Duplicate agent profile name {name!r} exists in multiple roots."
        ),
    )
    return sorted(selected, key=lambda agent: (str(agent["name"]), str(agent["source"])))


def _agent_files(root: Path) -> list[Path]:
    files: list[Path] = []

    def visit(directory: Path, depth: int) -> None:
        if depth > MAX_AGENT_SCAN_DEPTH or len(files) >= MAX_AGENT_SCAN:
            return
        try:
            children = sorted(directory.iterdir(), key=lambda path: path.as_posix())
        except OSError:
            return
        for child in children:
            if len(files) >= MAX_AGENT_SCAN:
                return
            if child.is_symlink():
                if child.suffix.lower() == ".md":
                    files.append(child)
                continue
            if child.is_dir():
                visit(child, depth + 1)
            elif child.is_file() and child.suffix.lower() == ".md":
                files.append(child)

    visit(root, 1)
    return files


def _catalog_profile_metadata(
    metadata: dict[str, object],
    *,
    skills: list[str] | None = None,
) -> dict[str, object]:
    raw_entries = metadata.get("mcp_servers")
    entries = raw_entries if isinstance(raw_entries, list) else []
    mcp_names = [
        entry if isinstance(entry, str) else str(next(iter(entry)))
        for entry in entries
        if isinstance(entry, str) or (isinstance(entry, dict) and entry)
    ]
    return {
        "description": metadata.get("description", ""),
        "mode": metadata.get("mode", "explore"),
        "model": metadata.get("model"),
        "effort": metadata.get("effort"),
        "tools": metadata.get("tools"),
        "disallowed_tools": metadata.get("disallowed_tools", []),
        "max_turns": metadata.get("max_turns"),
        "skills": skills if skills is not None else metadata.get("skills", []),
        "memory": metadata.get("memory"),
        "isolation": metadata.get("isolation"),
        "permission_mode": metadata.get("permission_mode"),
        "mcp_server_names": mcp_names,
        "has_hooks": metadata.get("hooks") is not None,
        "has_initial_prompt": metadata.get("initial_prompt") is not None,
        "background": bool(metadata.get("background", False)),
        "color": metadata.get("color"),
    }


def _agent_source_priority(source: str) -> int:
    if source == "cli":
        return 0
    if source in {"claude", "agents"}:
        return 1
    if source == "user":
        return 2
    return 3


def _inspect_agent_file(root: Path, path: Path) -> tuple[bool, dict[str, object], str]:
    if has_symlink_component(root, path):
        return False, {}, "Agent profile path contains a symbolic link."
    if not path.is_file():
        return False, {}, "Agent profile is not a regular Markdown file."
    try:
        content = _read_agent_bytes(path).decode("utf-8")
        metadata, _ = parse_agent_content(path, content)
    except UnicodeDecodeError as error:
        return False, {}, f"Agent profile is not valid UTF-8: {error}"
    except (OSError, ValueError) as error:
        return False, {}, str(error)
    return True, metadata, "Available."


def _read_agent_bytes(path: Path) -> bytes:
    return read_regular_file_bytes(path, max_bytes=MAX_AGENT_FILE_BYTES, label="Agent profile")
