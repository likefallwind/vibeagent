from __future__ import annotations

import os
import re
import stat
from collections import Counter
from pathlib import Path

from .workspace_core import RunWorkspace


SKILL_ROOTS = ((".claude/skills", "claude"), (".agents/skills", "agents"))
SKILL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
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
    if not SKILL_NAME_PATTERN.fullmatch(normalized):
        raise ValueError("skill name must use 1-64 letters, digits, dots, underscores, or hyphens.")
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
    description = _validate_skill_content(path, raw.decode("utf-8"))
    content = raw[:max_bytes].decode("utf-8", errors="ignore")
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
        if not root.exists() or not root.is_dir() or _has_symlink_component(workspace.root, root):
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

    name_counts = Counter(str(skill["name"]) for skill in discovered)
    duplicate_names = {name for name, count in name_counts.items() if count > 1}
    for skill in discovered:
        if skill["name"] in duplicate_names:
            skill["available"] = False
            skill["message"] = f"Duplicate skill name {skill['name']!r} exists in multiple skill roots."
    return sorted(discovered, key=lambda skill: (str(skill["name"]), str(skill["source"])))


def _inspect_skill_file(root: Path, path: Path) -> tuple[bool, str, str]:
    if _has_symlink_component(root, path):
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


def _validate_skill_content(path: Path, content: str) -> str:
    frontmatter = _skill_frontmatter(content)
    declared_name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    if not declared_name or not description:
        raise ValueError("SKILL.md frontmatter requires non-empty name and description fields.")
    if not SKILL_NAME_PATTERN.fullmatch(declared_name):
        raise ValueError("SKILL.md frontmatter name is invalid.")
    if declared_name != path.parent.name:
        raise ValueError(f"SKILL.md name {declared_name!r} does not match directory {path.parent.name!r}.")
    return description


def _skill_frontmatter(content: str) -> dict[str, str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    metadata: dict[str, str] = {}
    closed = False
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            closed = True
            break
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        if key not in {"name", "description"}:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        metadata[key] = " ".join(value.split())[:500]
    return metadata if closed else {}


def _has_symlink_component(root: Path, path: Path) -> bool:
    relative = path.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _read_skill_bytes(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("SKILL.md must be a regular file.")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(MAX_SKILL_FILE_BYTES + 1)
    finally:
        os.close(descriptor)
    if len(raw) > MAX_SKILL_FILE_BYTES:
        raise ValueError(f"SKILL.md exceeds {MAX_SKILL_FILE_BYTES} bytes.")
    return raw
