from __future__ import annotations

from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_project_metadata import (
    missing_command_tool,
    read_makefile_targets,
    read_package_json_scripts,
    read_pyproject_scripts,
)
from .workspace_search_files import list_files


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


def format_command_hint(command: str, detail: str | None = None) -> str:
    missing_tool = missing_command_tool(command)
    availability = f"available={str(missing_tool is None).lower()} missingTool={missing_tool or '.'}"
    suffix = f": {detail}" if detail else ""
    return f"- {command} [{availability}]{suffix}"
