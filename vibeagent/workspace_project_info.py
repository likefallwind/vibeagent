from __future__ import annotations

import json
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

from .workspace_core import (
    PROJECT_INSTRUCTION_CONTENT_LIMIT,
    PROJECT_INSTRUCTION_FILE_NAMES,
    PROJECT_TODO_MARKERS,
    PROJECT_TODO_PATTERN,
    RunWorkspace,
)
from .workspace_git_utils import run_readonly_git
from .workspace_paths import should_ignore_path
from .workspace_resolve import resolve_inside_run


def read_workspace_snapshot(workspace: RunWorkspace, max_bytes: int = 12_000) -> str:
    # Build a bounded project file listing so prompts remain informative but not oversized.
    files = list_files(workspace.root)
    if not files:
        return "No project files found."

    used = 0
    chunks: list[str] = []
    for file in files[:120]:
        content = file
        remaining = max_bytes - used
        if remaining <= 0:
            chunks.append("\n[workspace snapshot truncated]")
            break

        shown = content[:remaining]
        used += len(shown)
        chunks.append(shown)

    return "\n\n".join(chunks)


def read_project_instructions(workspace: RunWorkspace, max_bytes: int = 12_000, max_files: int = 20) -> str | None:
    metadata = read_project_instruction_sources(workspace, max_bytes=max_bytes, max_files=max_files)
    text = str(metadata["text"])
    return text if text.strip() else None


def read_project_instruction_sources(
    workspace: RunWorkspace,
    max_bytes: int = 12_000,
    max_files: int = 20,
) -> dict[str, object]:
    if max_bytes < 1:
        raise ValueError("max_bytes must be at least 1.")
    if max_bytes > PROJECT_INSTRUCTION_CONTENT_LIMIT:
        raise ValueError(f"max_bytes must be at most {PROJECT_INSTRUCTION_CONTENT_LIMIT}.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 200:
        raise ValueError("max_files must be at most 200.")

    instruction_files = [file for file in list_files(workspace.root) if Path(file).name in PROJECT_INSTRUCTION_FILE_NAMES]
    scanned_files = instruction_files[:max_files]
    sources: list[dict[str, object]] = []
    chunks: list[str] = []
    for relative_path in scanned_files:
        instructions_path = workspace.root / relative_path
        try:
            content = instructions_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            sources.append(
                {
                    "path": relative_path,
                    "scope": project_instruction_scope(relative_path),
                    "bytes": instructions_path.stat().st_size,
                    "chars": 0,
                    "empty": False,
                    "included": False,
                    "message": f"Instruction file is not valid UTF-8: {error}",
                }
            )
            continue
        included = bool(content.strip())
        sources.append(
            {
                "path": relative_path,
                "scope": project_instruction_scope(relative_path),
                "bytes": len(content.encode("utf-8")),
                "chars": len(content),
                "empty": not included,
                "included": included,
                "message": "Included." if included else "Instruction file is empty.",
            }
        )
        if included:
            chunks.append(
                "\n".join(
                    [
                        f"File: {relative_path}",
                        f"Scope: {project_instruction_scope(relative_path)}",
                        "Instructions:",
                        content,
                    ]
                )
            )

    omitted_files = max(0, len(instruction_files) - len(scanned_files))
    if omitted_files:
        chunks.append(f"[{omitted_files} additional project instruction file(s) omitted]")

    combined = "\n\n".join(chunks)
    text_truncated = len(combined) > max_bytes
    text = f"{combined[:max_bytes]}\n[project instructions truncated]" if text_truncated else combined
    return {
        "ok": True,
        "files": sources,
        "total_files": len(instruction_files),
        "scanned_files": len(scanned_files),
        "omitted_files": omitted_files,
        "truncated": text_truncated or bool(omitted_files),
        "text": text,
        "message": (
            f"Read {len(scanned_files)}/{len(instruction_files)} project instruction file(s)."
            if instruction_files
            else "No project instruction files found."
        ),
    }


def project_instruction_scope(relative_path: str) -> str:
    scope = Path(relative_path).parent.as_posix()
    return "." if scope == "." else scope


def read_project_command_hints(workspace: RunWorkspace, max_bytes: int = 8_000, max_files: int = 30) -> str | None:
    metadata = read_project_commands(workspace, max_commands=500, max_files=max_files)
    commands = metadata["commands"]
    if not commands:
        return None

    chunks: list[str] = []
    current_file = ""
    current_lines: list[str] = []
    for command in commands:
        relative_path = str(command["file"])
        if relative_path != current_file:
            if current_lines:
                chunks.append("\n".join(current_lines))
            current_file = relative_path
            current_lines = [f"File: {relative_path}", f"Cwd: {command['cwd']}"]
            source = str(command["source"])
            if source == "package_json_script":
                current_lines.append("package.json scripts:")
            elif source == "pyproject_console_script":
                current_lines.append("pyproject.toml console scripts:")
            elif source == "makefile_target":
                current_lines.append("Makefile targets:")
        current_lines.append(format_command_hint(str(command["command"]), str(command["detail"]) or None))
    if current_lines:
        chunks.append("\n".join(current_lines))

    omitted_files = int(metadata["total_files"]) - int(metadata["scanned_files"])
    if omitted_files > 0:
        chunks.append(f"[{omitted_files} additional command metadata file(s) omitted]")
    if bool(metadata["truncated"]):
        omitted_commands = int(metadata["total"]) - len(commands)
        if omitted_commands > 0:
            chunks.append(f"[{omitted_commands} additional command(s) omitted]")

    combined = "\n\n".join(chunks)
    if len(combined) <= max_bytes:
        return combined
    return f"{combined[:max_bytes]}\n[project command hints truncated]"


def read_project_todos(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_items: int = 100,
    max_files: int = 1000,
) -> dict[str, object]:
    if max_items < 1:
        raise ValueError("max_items must be at least 1.")
    if max_items > 500:
        raise ValueError("max_items must be at most 500.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 5000:
        raise ValueError("max_files must be at most 5000.")

    selected_path = relative_path.strip() if relative_path else None
    files = list_search_files(workspace, selected_path)
    scanned_files = files[:max_files]
    todos: list[dict[str, object]] = []
    total = 0
    for relative in scanned_files:
        path = resolve_inside_run(workspace.root, relative)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, start=1):
            match = PROJECT_TODO_PATTERN.search(line)
            if not match:
                continue
            total += 1
            if len(todos) >= max_items:
                continue
            todos.append(
                {
                    "path": relative,
                    "line": line_number,
                    "marker": match.group(1).upper(),
                    "text": line.strip(),
                }
            )

    truncated = len(files) > len(scanned_files) or total > len(todos)
    return {
        "ok": True,
        "todos": todos,
        "total": total,
        "truncated": truncated,
        "total_files": len(files),
        "scanned_files": len(scanned_files),
        "path": selected_path or ".",
        "markers": list(PROJECT_TODO_MARKERS),
        "message": f"Found {total} project TODO marker(s) in {len(scanned_files)}/{len(files)} scanned file(s).",
    }


def read_project_commands(workspace: RunWorkspace, max_commands: int = 100, max_files: int = 30) -> dict[str, object]:
    if max_commands < 1:
        raise ValueError("max_commands must be at least 1.")
    if max_commands > 500:
        raise ValueError("max_commands must be at most 500.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 200:
        raise ValueError("max_files must be at most 200.")

    command_files = [
        file
        for file in list_files(workspace.root)
        if Path(file).name in {"package.json", "pyproject.toml", "Makefile"}
    ]
    commands: list[dict[str, object]] = []
    total = 0
    for relative_path in command_files[:max_files]:
        path = workspace.root / relative_path
        cwd = Path(relative_path).parent.as_posix()
        if cwd == ".":
            cwd = "."

        file_commands: list[tuple[str, str, str]] = []
        if Path(relative_path).name == "package.json":
            file_commands = [
                ("package_json_script", f"npm run {name}", command)
                for name, command in read_package_json_scripts(path)
            ]
        elif Path(relative_path).name == "pyproject.toml":
            file_commands = [
                ("pyproject_console_script", name, target)
                for name, target in read_pyproject_scripts(path)
            ]
        elif Path(relative_path).name == "Makefile":
            file_commands = [
                ("makefile_target", f"make {target}", target)
                for target in read_makefile_targets(path)
            ]

        total += len(file_commands)
        for source, command, detail in file_commands:
            if len(commands) >= max_commands:
                continue
            missing_tool = missing_command_tool(command)
            commands.append(
                {
                    "file": relative_path,
                    "cwd": cwd,
                    "source": source,
                    "command": command,
                    "detail": detail,
                    "available": missing_tool is None,
                    "missing_tool": missing_tool,
                }
            )

    truncated = len(command_files) > max_files or total > len(commands)
    scanned_files = min(len(command_files), max_files)
    return {
        "ok": True,
        "commands": commands,
        "total": total,
        "truncated": truncated,
        "total_files": len(command_files),
        "scanned_files": scanned_files,
        "message": f"Found {total} project command(s) in {scanned_files}/{len(command_files)} metadata file(s).",
    }


def read_project_manifests(workspace: RunWorkspace, max_files: int = 30, max_items: int = 500) -> dict[str, object]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 200:
        raise ValueError("max_files must be at most 200.")
    if max_items < 1:
        raise ValueError("max_items must be at least 1.")
    if max_items > 2000:
        raise ValueError("max_items must be at most 2000.")

    manifest_files = [
        file
        for file in list_files(workspace.root)
        if Path(file).name in {"package.json", "pyproject.toml"}
    ]
    manifests: list[dict[str, object]] = []
    remaining_items = max_items
    for relative_path in manifest_files[:max_files]:
        path = workspace.root / relative_path
        if Path(relative_path).name == "package.json":
            manifest = read_package_json_manifest(path, relative_path, remaining_items)
        else:
            manifest = read_pyproject_manifest(path, relative_path, remaining_items)
        manifests.append(manifest)
        remaining_items = max(0, remaining_items - int(manifest["item_count"]))

    total_items = sum(int(manifest["item_count"]) for manifest in manifests)
    truncated = len(manifest_files) > max_files or any(bool(manifest["truncated"]) for manifest in manifests)
    return {
        "ok": all(bool(manifest["ok"]) for manifest in manifests),
        "manifests": manifests,
        "total_files": len(manifest_files),
        "scanned_files": min(len(manifest_files), max_files),
        "total_items": total_items,
        "truncated": truncated,
        "message": f"Read {min(len(manifest_files), max_files)}/{len(manifest_files)} project manifest file(s).",
    }


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


def format_command_hint(command: str, detail: str | None = None) -> str:
    missing_tool = missing_command_tool(command)
    availability = f"available={str(missing_tool is None).lower()} missingTool={missing_tool or '.'}"
    suffix = f": {detail}" if detail else ""
    return f"- {command} [{availability}]{suffix}"


def read_environment_info(workspace: RunWorkspace) -> dict[str, object]:
    tools = [read_runtime_tool_info(name, args) for name, args in runtime_tool_commands()]
    git_probe = run_readonly_git(workspace.root, ["rev-parse", "--is-inside-work-tree"])
    return {
        "project_root": workspace.root.as_posix(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}".strip(),
        "is_git_repo": git_probe.ok and git_probe.stdout.strip() == "true",
        "tools": tools,
        "message": f"Inspected runtime environment; {sum(1 for tool in tools if tool['available'])}/{len(tools)} tool(s) available.",
    }


def runtime_tool_commands() -> list[tuple[str, list[str]]]:
    return [
        ("python", [sys.executable, "--version"]),
        ("python3", ["python3", "--version"]),
        ("git", ["git", "--version"]),
        ("node", ["node", "--version"]),
        ("npm", ["npm", "--version"]),
        ("pnpm", ["pnpm", "--version"]),
        ("yarn", ["yarn", "--version"]),
        ("uv", ["uv", "--version"]),
        ("pytest", ["pytest", "--version"]),
    ]


def read_runtime_tool_info(name: str, command: list[str]) -> dict[str, object]:
    executable = command[0]
    path = sys.executable if executable == sys.executable else shutil.which(executable)
    if not path:
        return {"name": name, "available": False, "path": None, "version": None, "message": "Not found on PATH."}
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"name": name, "available": True, "path": path, "version": None, "message": str(error)}
    version = (result.stdout or result.stderr).strip().splitlines()
    version_text = version[0] if version else ""
    return {
        "name": name,
        "available": result.returncode == 0,
        "path": path,
        "version": version_text or None,
        "message": version_text or f"Exited with {result.returncode}.",
    }


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


def list_files(root: str | Path) -> list[str]:
    # Enumerate all files in deterministic order so prompt diffs stay stable.
    root_path = Path(root).resolve()
    files = [
        path.relative_to(root_path).as_posix()
        for path in root_path.rglob("*")
        if not path.is_symlink() and path.is_file() and not should_ignore_path(root_path, path)
    ]
    return sorted(files)


def missing_command_tool(command: str) -> str | None:
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
    if shutil.which(executable):
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


def list_search_files(workspace: RunWorkspace, relative_path: str | None) -> list[str]:
    if not relative_path:
        return list_files(workspace.root)

    base = resolve_inside_run(workspace.root, relative_path)
    if not base.exists():
        raise ValueError(f"Path does not exist: {relative_path}")
    if base.is_file():
        return [base.relative_to(workspace.root).as_posix()]
    return [
        path.relative_to(workspace.root).as_posix()
        for path in sorted(base.rglob("*"))
        if not path.is_symlink() and path.is_file() and not should_ignore_path(workspace.root, path)
    ]
