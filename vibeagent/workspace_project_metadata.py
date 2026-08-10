from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import tomllib
from pathlib import Path


def read_package_json_manifest(path: Path, relative_path: str, max_items: int) -> dict[str, object]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return empty_project_manifest(relative_path, "package_json", str(error))
    if not isinstance(parsed, dict):
        return empty_project_manifest(relative_path, "package_json", "package.json root is not an object.")

    groups = [
        ("scripts", parsed.get("scripts")),
        ("dependencies", parsed.get("dependencies")),
        ("devDependencies", parsed.get("devDependencies")),
        ("peerDependencies", parsed.get("peerDependencies")),
        ("optionalDependencies", parsed.get("optionalDependencies")),
    ]
    items, item_count, truncated = manifest_group_items(groups, max_items)
    return {
        "path": relative_path,
        "kind": "package_json",
        "ok": True,
        "name": str(parsed.get("name") or ""),
        "version": str(parsed.get("version") or ""),
        "items": items,
        "item_count": item_count,
        "truncated": truncated,
        "message": f"Read package.json manifest with {item_count} item(s).",
    }


def read_pyproject_manifest(path: Path, relative_path: str, max_items: int) -> dict[str, object]:
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        return empty_project_manifest(relative_path, "pyproject_toml", str(error))
    if not isinstance(parsed, dict):
        return empty_project_manifest(relative_path, "pyproject_toml", "pyproject.toml root is not an object.")

    project = parsed.get("project") if isinstance(parsed.get("project"), dict) else {}
    tool = parsed.get("tool") if isinstance(parsed.get("tool"), dict) else {}
    poetry = tool.get("poetry") if isinstance(tool.get("poetry"), dict) else {}
    groups = [
        ("dependencies", project.get("dependencies")),
        ("optional-dependencies", project.get("optional-dependencies")),
        ("scripts", project.get("scripts")),
        ("gui-scripts", project.get("gui-scripts")),
        ("poetry.dependencies", poetry.get("dependencies")),
        ("poetry.dev-dependencies", poetry.get("dev-dependencies")),
    ]
    items, item_count, truncated = manifest_group_items(groups, max_items)
    return {
        "path": relative_path,
        "kind": "pyproject_toml",
        "ok": True,
        "name": str(project.get("name") or poetry.get("name") or ""),
        "version": str(project.get("version") or poetry.get("version") or ""),
        "items": items,
        "item_count": item_count,
        "truncated": truncated,
        "message": f"Read pyproject.toml manifest with {item_count} item(s).",
    }


def empty_project_manifest(relative_path: str, kind: str, message: str) -> dict[str, object]:
    return {
        "path": relative_path,
        "kind": kind,
        "ok": False,
        "name": "",
        "version": "",
        "items": [],
        "item_count": 0,
        "truncated": False,
        "message": message,
    }


def manifest_group_items(groups: list[tuple[str, object]], max_items: int) -> tuple[list[dict[str, str]], int, bool]:
    items: list[dict[str, str]] = []
    total = 0
    for group, value in groups:
        entries = normalize_manifest_group_items(group, value)
        total += len(entries)
        for item in entries:
            if len(items) < max_items:
                items.append(item)
    return items, total, total > len(items)


def normalize_manifest_group_items(group: str, value: object) -> list[dict[str, str]]:
    if isinstance(value, dict):
        return sorted(
            [
                {"group": group, "name": str(name), "value": stringify_manifest_value(raw_value)}
                for name, raw_value in value.items()
                if isinstance(name, str)
            ],
            key=lambda item: item["name"],
        )
    if isinstance(value, list):
        return [
            {"group": group, "name": str(item), "value": ""}
            for item in value
            if isinstance(item, str)
        ]
    return []


def stringify_manifest_value(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if value is None:
        return ""
    try:
        return json.dumps(value, sort_keys=True)
    except TypeError:
        return str(value)


def read_package_json_scripts(path: Path, max_scripts: int = 30) -> list[tuple[str, str]]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    scripts = parsed.get("scripts") if isinstance(parsed, dict) else None
    if not isinstance(scripts, dict):
        return []
    return sorted(
        (str(name), command)
        for name, command in scripts.items()
        if isinstance(name, str) and isinstance(command, str)
    )[:max_scripts]


def read_pyproject_scripts(path: Path, max_scripts: int = 30) -> list[tuple[str, str]]:
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return []
    project = parsed.get("project") if isinstance(parsed, dict) else None
    scripts = project.get("scripts") if isinstance(project, dict) else None
    if not isinstance(scripts, dict):
        return []
    return sorted(
        (str(name), target)
        for name, target in scripts.items()
        if isinstance(name, str) and isinstance(target, str)
    )[:max_scripts]


def read_makefile_targets(path: Path, max_targets: int = 40) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    targets: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if line.startswith(("\t", " ", "#")):
            continue
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.-]*):(?:\s|$)", line)
        if not match:
            continue
        target = match.group(1)
        if "%" in target or target in seen:
            continue
        seen.add(target)
        targets.append(target)
        if len(targets) >= max_targets:
            break
    return targets


def missing_command_tool(command: str, search_path: str | None = None) -> str | None:
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    if not parts:
        return None

    executable = first_command_executable(parts)
    if not executable:
        return None
    if executable.startswith(("./", "../")):
        return None
    if executable in SHELL_BUILTINS:
        return None
    resolved = (
        shutil.which(executable)
        if search_path is None or search_path == os.environ.get("PATH", "")
        else shutil.which(executable, path=search_path)
    )
    if resolved:
        return None
    return executable


SHELL_BUILTINS = {
    "alias",
    "bg",
    "cd",
    "command",
    "echo",
    "eval",
    "exec",
    "exit",
    "export",
    "fg",
    "hash",
    "jobs",
    "printf",
    "pwd",
    "read",
    "set",
    "shift",
    "test",
    "type",
    "ulimit",
    "umask",
    "unalias",
    "unset",
}


def first_command_executable(parts: list[str]) -> str | None:
    for part in parts:
        if is_shell_assignment(part):
            continue
        return part
    return None


def is_shell_assignment(value: str) -> bool:
    name, separator, _rest = value.partition("=")
    return bool(separator) and bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name))


__all__ = [
    "SHELL_BUILTINS",
    "empty_project_manifest",
    "first_command_executable",
    "is_shell_assignment",
    "manifest_group_items",
    "missing_command_tool",
    "normalize_manifest_group_items",
    "read_makefile_targets",
    "read_package_json_manifest",
    "read_package_json_scripts",
    "read_pyproject_manifest",
    "read_pyproject_scripts",
    "stringify_manifest_value",
]
