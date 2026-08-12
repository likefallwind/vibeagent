from __future__ import annotations

import re
from pathlib import Path

from .nested_skill_discovery import discover_nested_skill_locations
from .plugin_runtime import (
    PluginComponentFile,
    enabled_plugin_component_files,
    expand_plugin_path_variables,
    plugin_component_path_reference,
)
from .plugin_store import read_installed_plugin_manifest
from .scoped_component_selection import select_preferred_components
from .user_paths import user_home
from .workspace_core import RunWorkspace
from .workspace_metadata_files import (
    has_symlink_component,
    parse_scalar_frontmatter,
    read_regular_file_bytes,
)
from .session_config_state import effective_nested_skill_root, effective_skill_root


SKILL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SKILL_SCOPE_SEGMENT = r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}"
SKILL_REFERENCE_PATTERN = re.compile(
    rf"^(?:(?:{SKILL_SCOPE_SEGMENT})(?:/{SKILL_SCOPE_SEGMENT}){{0,7}}:)?"
    rf"{SKILL_SCOPE_SEGMENT}$"
)
MAX_SKILL_FILE_BYTES = 256_000
MAX_SKILL_SCAN = 1_000


def read_project_skills(workspace: RunWorkspace, max_skills: int = 100) -> dict[str, object]:
    if max_skills < 1 or max_skills > 500:
        raise ValueError("max_skills must be between 1 and 500.")
    skills = _discover_project_skills(workspace)
    shown = skills[:max_skills]
    return {
        "ok": True,
        "skills": shown,
        "total": len(skills),
        "truncated": len(skills) > len(shown),
        "invalid": sum(1 for skill in skills if not skill["available"]),
        "message": f"Found {len(skills)} custom skill(s); {sum(1 for skill in skills if skill['available'])} available.",
    }


def read_project_skill(workspace: RunWorkspace, name: str, max_bytes: int = 20_000) -> dict[str, object]:
    normalized = name.strip()
    if not SKILL_REFERENCE_PATTERN.fullmatch(normalized):
        raise ValueError(
            "skill name must use a valid optional plugin or directory namespace and 1-64 character name."
        )
    if max_bytes < 200 or max_bytes > 50_000:
        raise ValueError("max_bytes must be between 200 and 50000.")

    discovered = _discover_project_skills(workspace)
    matches = [skill for skill in discovered if skill["name"] == normalized]
    if not matches:
        raise ValueError(f"Custom skill not found: {normalized}.")
    available = [skill for skill in matches if skill["available"]]
    if len(available) != 1:
        detail = "; ".join(str(skill["message"]) for skill in matches)
        raise ValueError(f"Custom skill {normalized!r} is unavailable: {detail}")

    skill = available[0]
    path = _effective_skill_path(workspace, skill)
    raw = _read_skill_bytes(path)
    description = _validate_skill_content(
        path,
        raw.decode("utf-8"),
        enforce_directory_name=not str(skill["source"]).startswith("plugin:"),
    )
    content = raw[:max_bytes].decode("utf-8", errors="ignore")
    appended_truncated = False
    if str(skill["source"]).startswith("plugin:"):
        plugin = str(skill["source"]).removeprefix("plugin:")
        manifest = read_installed_plugin_manifest(
            workspace.root,
            plugin,
        )
        content = expand_plugin_path_variables(
            content,
            PluginComponentFile(plugin, "skill", path, manifest.root),
            workspace,
        )
    elif ":" not in normalized:
        variants = [
            item
            for item in discovered
            if str(item.get("name", "")).rsplit(":", 1)[-1] == normalized
            and item.get("source") == "nested_claude"
            and item.get("available")
        ]
        if variants:
            names = ", ".join(str(item["name"]) for item in variants)
            combined = content + (
                "\n\nDirectory-qualified variants are available: "
                f"{names}. Load each variant whose scope contains the files being worked on."
            )
            encoded = combined.encode("utf-8")
            appended_truncated = len(encoded) > max_bytes
            content = encoded[:max_bytes].decode("utf-8", errors="ignore")
    truncated = len(raw) > max_bytes or appended_truncated
    return {
        **skill,
        "description": description,
        "content": content,
        "bytes": len(raw),
        "truncated": truncated,
        "max_bytes": max_bytes,
        "message": (
            f"Loaded custom skill {normalized!r} from {skill['path']}."
            + (" Content truncated." if truncated else "")
        ),
    }


def format_project_skill_catalog(workspace: RunWorkspace, max_skills: int = 20) -> str | None:
    metadata = read_project_skills(workspace, max_skills=max_skills)
    available = [skill for skill in metadata["skills"] if skill["available"]]
    if not available:
        return None
    lines = [
        "Available custom skills (metadata only; use tool_search for project_skills or skill before loading one):"
    ]
    for skill in available:
        lines.append(f"- {skill['name']}: {skill['description']} ({skill['path']})")
    if metadata["truncated"]:
        lines.append(f"[{int(metadata['total']) - len(metadata['skills'])} additional skill(s) omitted]")
    return "\n".join(lines)


def discover_project_skill_metadata(workspace: RunWorkspace) -> list[dict[str, object]]:
    return _discover_project_skills(workspace)


def _discover_project_skills(workspace: RunWorkspace) -> list[dict[str, object]]:
    if workspace.safe_mode:
        return []
    discovered: list[dict[str, object]] = []
    home = user_home()
    roots = (
        []
        if workspace.bare_mode
        else [
            (effective_skill_root(workspace, user=False), "claude"),
            (workspace.root / ".agents/skills", "agents"),
            (effective_skill_root(workspace, user=True), "user"),
        ]
    )
    for root, source in roots:
        boundary = _skill_boundary(workspace, home, root, source)
        if not root.exists() or not root.is_dir() or has_symlink_component(boundary, root):
            continue
        try:
            children = sorted(root.iterdir(), key=lambda path: path.name)[:MAX_SKILL_SCAN]
        except OSError:
            continue
        for child in children:
            if not child.is_dir() or not SKILL_NAME_PATTERN.fullmatch(child.name):
                continue
            skill_path = child / "SKILL.md"
            relative_path = plugin_component_path_reference(workspace.root, skill_path)
            available, description, message = _inspect_skill_file(boundary, skill_path)
            discovered.append(
                {
                    "name": child.name,
                    "description": description,
                    "path": relative_path,
                    "source": source,
                    "available": available,
                    "message": message,
                }
            )

    nested_root = effective_nested_skill_root(workspace)
    nested_boundary = workspace.session_dir if nested_root != workspace.root else workspace.root
    locations = []
    if not workspace.bare_mode:
        locations, _ = discover_nested_skill_locations(
            nested_root,
            max_skills=MAX_SKILL_SCAN,
        )
    for location in locations:
        local_name = location.path.parent.name
        if not SKILL_NAME_PATTERN.fullmatch(local_name):
            continue
        qualified_name = f"{location.scope.as_posix()}:{local_name}"
        relative_path = location.path.relative_to(nested_root).as_posix()
        if not SKILL_REFERENCE_PATTERN.fullmatch(qualified_name):
            available = False
            description = ""
            message = "Nested skill scope is invalid or exceeds the supported depth."
        else:
            available, description, message = _inspect_skill_file(nested_boundary, location.path)
        discovered.append(
            {
                "name": qualified_name,
                "description": description,
                "path": relative_path,
                "source": "nested_claude",
                "available": available,
                "message": message,
            }
        )

    for component in enabled_plugin_component_files(workspace, "skill"):
        path = component.path
        relative_path = plugin_component_path_reference(workspace.root, path)
        try:
            content = _read_skill_bytes(path).decode("utf-8")
            frontmatter = _skill_frontmatter(content)
            declared_name = frontmatter.get("name", path.parent.name)
            description = _validate_skill_content(path, content, enforce_directory_name=False)
            available = True
            message = "Available."
        except UnicodeDecodeError as error:
            declared_name = path.parent.name
            description = ""
            available = False
            message = f"SKILL.md is not valid UTF-8: {error}"
        except (OSError, ValueError) as error:
            declared_name = path.parent.name
            description = ""
            available = False
            message = str(error)
        discovered.append(
            {
                "name": f"{component.plugin}:{declared_name}",
                "description": description,
                "path": relative_path,
                "source": component.source,
                "available": available,
                "message": message,
            }
        )

    selected = select_preferred_components(
        discovered,
        source_priority=_skill_source_priority,
        duplicate_message=lambda name: (
            f"Duplicate skill name {name!r} exists in multiple skill roots."
        ),
    )
    return sorted(selected, key=lambda skill: (str(skill["name"]), str(skill["source"])))


def _effective_skill_path(workspace: RunWorkspace, skill: dict[str, object]) -> Path:
    source = str(skill["source"])
    if source == "user":
        return effective_skill_root(workspace, user=True) / str(skill["name"]) / "SKILL.md"
    if source == "claude":
        return effective_skill_root(workspace, user=False) / str(skill["name"]) / "SKILL.md"
    if source == "nested_claude":
        return effective_nested_skill_root(workspace) / str(skill["path"])
    return workspace.root / str(skill["path"])


def _skill_boundary(
    workspace: RunWorkspace,
    home: Path,
    root: Path,
    source: str,
) -> Path:
    if source == "user":
        physical_root = home / ".claude/skills"
    elif source == "nested_claude":
        physical_root = workspace.root
    else:
        physical_root = workspace.root / f".{source}/skills"
    if source in {"user", "claude", "nested_claude"} and root != physical_root:
        return workspace.session_dir
    return home if source == "user" else workspace.root


def _skill_source_priority(source: str) -> int:
    if source == "user":
        return 1
    if source in {"claude", "agents", "nested_claude"}:
        return 2
    return 3


def _inspect_skill_file(root: Path, path: Path) -> tuple[bool, str, str]:
    if has_symlink_component(root, path):
        return False, "", "Skill path contains a symbolic link."
    if not path.is_file():
        return False, "", "SKILL.md is missing."
    try:
        content = _read_skill_bytes(path).decode("utf-8")
    except UnicodeDecodeError as error:
        return False, "", f"SKILL.md is not valid UTF-8: {error}"
    except ValueError as error:
        return False, "", str(error)
    except OSError as error:
        return False, "", f"Could not read SKILL.md: {error}"
    try:
        description = _validate_skill_content(path, content)
    except ValueError as error:
        return False, "", str(error)
    return True, description, "Available."


def _validate_skill_content(path: Path, content: str, *, enforce_directory_name: bool = True) -> str:
    frontmatter = _skill_frontmatter(content)
    declared_name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    if not description or (enforce_directory_name and not declared_name):
        raise ValueError("SKILL.md frontmatter requires non-empty name and description fields.")
    if declared_name and not SKILL_NAME_PATTERN.fullmatch(declared_name):
        raise ValueError("SKILL.md frontmatter name is invalid.")
    if enforce_directory_name and declared_name != path.parent.name:
        raise ValueError(f"SKILL.md name {declared_name!r} does not match directory {path.parent.name!r}.")
    return description


def _skill_frontmatter(content: str) -> dict[str, str]:
    metadata, _ = parse_scalar_frontmatter(content, frozenset({"name", "description"}))
    return {key: " ".join(value.split())[:500] for key, value in metadata.items()}


def _read_skill_bytes(path: Path) -> bytes:
    return read_regular_file_bytes(path, max_bytes=MAX_SKILL_FILE_BYTES, label="SKILL.md")
