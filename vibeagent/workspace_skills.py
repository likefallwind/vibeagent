from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .plugin_runtime import (
    PluginComponentFile,
    enabled_plugin_component_files,
    expand_plugin_path_variables,
)
from .plugin_store import read_installed_plugin_manifest
from .workspace_core import RunWorkspace
from .workspace_metadata_files import (
    has_symlink_component,
    parse_scalar_frontmatter,
    read_regular_file_bytes,
)


SKILL_ROOTS = ((".claude/skills", "claude"), (".agents/skills", "agents"))
SKILL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SKILL_REFERENCE_PATTERN = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9]):)?[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
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
        "message": f"Found {len(skills)} project skill(s); {sum(1 for skill in skills if skill['available'])} available.",
    }


def read_project_skill(workspace: RunWorkspace, name: str, max_bytes: int = 20_000) -> dict[str, object]:
    normalized = name.strip()
    if not SKILL_REFERENCE_PATTERN.fullmatch(normalized):
        raise ValueError("skill name must use a valid optional plugin namespace and 1-64 character name.")
    if max_bytes < 200 or max_bytes > 50_000:
        raise ValueError("max_bytes must be between 200 and 50000.")

    matches = [skill for skill in _discover_project_skills(workspace) if skill["name"] == normalized]
    if not matches:
        raise ValueError(f"Project skill not found: {normalized}.")
    available = [skill for skill in matches if skill["available"]]
    if len(available) != 1:
        detail = "; ".join(str(skill["message"]) for skill in matches)
        raise ValueError(f"Project skill {normalized!r} is unavailable: {detail}")

    skill = available[0]
    path = workspace.root / str(skill["path"])
    raw = _read_skill_bytes(path)
    description = _validate_skill_content(
        path,
        raw.decode("utf-8"),
        enforce_directory_name=not str(skill["source"]).startswith("plugin:"),
    )
    content = raw[:max_bytes].decode("utf-8", errors="ignore")
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
    truncated = len(raw) > max_bytes
    return {
        **skill,
        "description": description,
        "content": content,
        "bytes": len(raw),
        "truncated": truncated,
        "max_bytes": max_bytes,
        "message": (
            f"Loaded project skill {normalized!r} from {skill['path']}."
            + (" Content truncated." if truncated else "")
        ),
    }


def format_project_skill_catalog(workspace: RunWorkspace, max_skills: int = 20) -> str | None:
    metadata = read_project_skills(workspace, max_skills=max_skills)
    available = [skill for skill in metadata["skills"] if skill["available"]]
    if not available:
        return None
    lines = [
        "Available project skills (metadata only; use tool_search for project_skills or skill before loading one):"
    ]
    for skill in available:
        lines.append(f"- {skill['name']}: {skill['description']} ({skill['path']})")
    if metadata["truncated"]:
        lines.append(f"[{int(metadata['total']) - len(metadata['skills'])} additional skill(s) omitted]")
    return "\n".join(lines)


def _discover_project_skills(workspace: RunWorkspace) -> list[dict[str, object]]:
    discovered: list[dict[str, object]] = []
    for relative_root, source in SKILL_ROOTS:
        root = workspace.root / relative_root
        if not root.exists() or not root.is_dir() or has_symlink_component(workspace.root, root):
            continue
        try:
            children = sorted(root.iterdir(), key=lambda path: path.name)[:MAX_SKILL_SCAN]
        except OSError:
            continue
        for child in children:
            if not child.is_dir() or not SKILL_NAME_PATTERN.fullmatch(child.name):
                continue
            skill_path = child / "SKILL.md"
            relative_path = skill_path.relative_to(workspace.root).as_posix()
            available, description, message = _inspect_skill_file(workspace.root, skill_path)
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

    for component in enabled_plugin_component_files(workspace, "skill"):
        path = component.path
        relative_path = path.relative_to(workspace.root).as_posix()
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

    name_counts = Counter(str(skill["name"]) for skill in discovered)
    duplicate_names = {name for name, count in name_counts.items() if count > 1}
    for skill in discovered:
        if skill["name"] in duplicate_names:
            skill["available"] = False
            skill["message"] = f"Duplicate skill name {skill['name']!r} exists in multiple skill roots."
    return sorted(discovered, key=lambda skill: (str(skill["name"]), str(skill["source"])))


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
