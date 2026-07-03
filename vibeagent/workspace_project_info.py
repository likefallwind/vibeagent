from __future__ import annotations

import platform
import shutil
import subprocess
import sys
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
from .workspace_project_metadata import (
    SHELL_BUILTINS,
    empty_project_manifest,
    first_command_executable,
    is_shell_assignment,
    manifest_group_items,
    missing_command_tool,
    normalize_manifest_group_items,
    read_makefile_targets,
    read_package_json_manifest,
    read_package_json_scripts,
    read_pyproject_manifest,
    read_pyproject_scripts,
    stringify_manifest_value,
)
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

    instruction_files = sorted(
        (file for file in list_files(workspace.root) if Path(file).name in PROJECT_INSTRUCTION_FILE_NAMES),
        key=project_instruction_sort_key,
    )
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


def project_instruction_sort_key(relative_path: str) -> tuple[int, str, int, str]:
    path = Path(relative_path)
    scope = project_instruction_scope(relative_path)
    file_order = {"AGENTS.md": 0, "CLAUDE.md": 1}.get(path.name, 2)
    return len(path.parts), scope, file_order, relative_path


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


def list_files(root: str | Path) -> list[str]:
    # Enumerate all files in deterministic order so prompt diffs stay stable.
    root_path = Path(root).resolve()
    files = [
        path.relative_to(root_path).as_posix()
        for path in root_path.rglob("*")
        if not path.is_symlink() and path.is_file() and not should_ignore_path(root_path, path)
    ]
    return sorted(files)


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
