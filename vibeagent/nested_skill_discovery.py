from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


MAX_NESTED_SKILL_DEPTH = 8
MAX_NESTED_SKILL_DIRECTORIES = 10_000
NESTED_SKILL_IGNORED_DIRECTORIES = frozenset(
    {
        ".agents",
        ".codex",
        ".git",
        ".pytest_cache",
        ".venv",
        ".vibeagent",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
)


@dataclass(frozen=True)
class NestedSkillLocation:
    scope: Path
    path: Path


def discover_nested_skill_locations(
    root: Path,
    *,
    max_skills: int,
    max_depth: int = MAX_NESTED_SKILL_DEPTH,
) -> tuple[list[NestedSkillLocation], bool]:
    locations: list[NestedSkillLocation] = []
    visited = 0
    truncated = False

    def visit(directory: Path, depth: int) -> None:
        nonlocal truncated, visited
        if truncated or depth > max_depth:
            return
        visited += 1
        if visited > MAX_NESTED_SKILL_DIRECTORIES:
            truncated = True
            return
        try:
            children = sorted(directory.iterdir(), key=lambda path: path.name)
        except OSError:
            return
        for child in children:
            if len(locations) >= max_skills:
                truncated = True
                return
            if child.is_symlink() or not child.is_dir():
                continue
            if child.name == ".claude":
                scope = child.parent.relative_to(root)
                if scope != Path("."):
                    _append_skill_locations(child / "skills", scope, locations, max_skills)
                    if len(locations) >= max_skills:
                        truncated = True
                        return
                continue
            if child.name in NESTED_SKILL_IGNORED_DIRECTORIES:
                continue
            visit(child, depth + 1)
            if truncated:
                return

    if root.exists() and root.is_dir() and not root.is_symlink():
        visit(root, 0)
    return locations, truncated


def _append_skill_locations(
    skill_root: Path,
    scope: Path,
    locations: list[NestedSkillLocation],
    max_skills: int,
) -> None:
    if skill_root.is_symlink() or not skill_root.is_dir():
        return
    try:
        children = sorted(skill_root.iterdir(), key=lambda path: path.name)
    except OSError:
        return
    for child in children:
        if len(locations) >= max_skills:
            return
        if child.is_symlink() or not child.is_dir():
            continue
        locations.append(NestedSkillLocation(scope=scope, path=child / "SKILL.md"))


__all__ = [
    "MAX_NESTED_SKILL_DEPTH",
    "NestedSkillLocation",
    "discover_nested_skill_locations",
]
