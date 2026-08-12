from __future__ import annotations

import re
import shlex
from pathlib import Path

from .command_parsing import parse_local_command
from .plugin_runtime import (
    enabled_plugin_component_files,
    expand_plugin_path_variables,
    plugin_component_for_path,
    plugin_component_path_reference,
)
from .scoped_component_selection import select_preferred_components
from .user_paths import user_home
from .workspace_core import RunWorkspace, create_local_workspace
from .workspace_metadata_files import has_symlink_component, parse_scalar_frontmatter, read_regular_file_bytes
from .workspace_skills import discover_project_skill_metadata, read_project_skill


COMMAND_ROOTS = ((".claude/commands", "claude"), (".agents/commands", "agents"))
COMMAND_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
COMMAND_SEGMENT = r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}"
COMMAND_INVOCATION_PATTERN = re.compile(
    rf"^/((?:{COMMAND_SEGMENT})(?::(?:{COMMAND_SEGMENT})){{0,3}}|"
    rf"(?:{COMMAND_SEGMENT})(?:/(?:{COMMAND_SEGMENT})){{1,7}}:(?:{COMMAND_SEGMENT}))"
    rf"(?:\s+(.*))?$"
)
POSITIONAL_ARGUMENT_PATTERN = re.compile(r"\$(?:\{([1-9])\}|([1-9])(?![0-9]))")
MAX_COMMAND_FILE_BYTES = 64_000
MAX_COMMAND_SCAN = 1_000
MAX_COMMAND_DEPTH = 4
MAX_EXPANDED_COMMAND_CHARS = 100_000


def read_project_prompt_commands(
    root: Path,
    max_commands: int = 100,
    *,
    workspace: RunWorkspace | None = None,
) -> dict[str, object]:
    if max_commands < 1 or max_commands > 500:
        raise ValueError("max_commands must be between 1 and 500.")
    commands = _discover_project_prompt_commands(root.resolve(), workspace=workspace)
    shown = commands[:max_commands]
    return {
        "ok": True,
        "commands": shown,
        "total": len(commands),
        "truncated": len(commands) > len(shown),
        "invalid": sum(1 for command in commands if not command["available"]),
        "message": f"Found {len(commands)} custom command template(s); {sum(1 for command in commands if command['available'])} available.",
    }


def format_project_prompt_commands(
    root: Path,
    max_commands: int = 100,
    *,
    workspace: RunWorkspace | None = None,
) -> str:
    report = read_project_prompt_commands(root, max_commands=max_commands, workspace=workspace)
    lines = [
        "Custom commands:",
        f"  shown: {len(report['commands'])}/{report['total']}",
        f"  invalid: {report['invalid']}",
    ]
    for command in report["commands"]:
        status = "available" if command["available"] else "invalid"
        hint = f" {command['argument_hint']}" if command["argument_hint"] else ""
        detail = command["description"] if command["available"] else command["message"]
        lines.append(
            f"  /{command['name']}{hint} [{status}, {command['source']}] - "
            f"{detail}"
        )
    if report["truncated"]:
        lines.append(f"  [{int(report['total']) - len(report['commands'])} additional command(s) omitted]")
    return "\n".join(lines)


def expand_project_prompt_command(
    root: Path,
    invocation: str,
    *,
    workspace: RunWorkspace | None = None,
) -> dict[str, object] | None:
    match = COMMAND_INVOCATION_PATTERN.fullmatch(invocation.strip())
    if match is None:
        return None
    name = match.group(1)
    arguments = match.group(2) or ""
    current_workspace = workspace or create_local_workspace(root, "skill-invocation")
    skill = _load_invoked_skill(current_workspace, name)
    if skill is not None:
        prompt = _expand_command_body(str(skill["body"]), arguments)
        return {
            "name": name,
            "arguments": arguments,
            "prompt": prompt,
            "path": skill["path"],
            "source": skill["source"],
            "task_source": "custom_skill",
            "description": skill["description"],
        }
    command = _load_project_prompt_command(current_workspace, name)
    if command is None:
        raise ValueError(f"Unknown command: /{name}. Use /skills or /custom-commands to list custom prompts.")
    prompt = _expand_command_body(str(command["body"]), arguments)
    return {
        "name": name,
        "arguments": arguments,
        "prompt": prompt,
        "path": command["path"],
        "source": command["source"],
        "description": command["description"],
        "task_source": "project_command",
    }


def _load_invoked_skill(workspace: RunWorkspace, name: str) -> dict[str, object] | None:
    matches = [
        skill
        for skill in discover_project_skill_metadata(workspace)
        if skill["name"] == name
    ]
    if not matches:
        return None
    loaded = read_project_skill(workspace, name, max_bytes=50_000)
    _, body = parse_scalar_frontmatter(
        str(loaded["content"]),
        frozenset({"name", "description"}),
    )
    if not body.strip():
        raise ValueError(f"Custom skill /{name} has no instruction body.")
    return {**loaded, "body": body.strip()}


def _load_project_prompt_command(workspace: RunWorkspace, name: str) -> dict[str, object] | None:
    root = workspace.root
    matches = [
        command
        for command in _discover_project_prompt_commands(root, workspace=workspace)
        if command["name"] == name
    ]
    if not matches:
        return None
    available = [command for command in matches if command["available"]]
    if len(available) != 1:
        detail = "; ".join(str(command["message"]) for command in matches)
        raise ValueError(f"Project command /{name} is unavailable: {detail}")
    command = available[0]
    path = root / str(command["path"])
    content = read_regular_file_bytes(path, max_bytes=MAX_COMMAND_FILE_BYTES, label="Command template").decode("utf-8")
    metadata, body = _parse_command_content(content)
    source = str(command["source"])
    if source.startswith("plugin:"):
        component = plugin_component_for_path(workspace, path, "command")
        if component is None:
            raise ValueError(f"Plugin command component is no longer enabled: /{name}")
        body = expand_plugin_path_variables(
            body,
            component,
            workspace,
        )
    return {**command, **metadata, "body": body}


def _discover_project_prompt_commands(
    root: Path,
    *,
    workspace: RunWorkspace | None = None,
) -> list[dict[str, object]]:
    discovered: list[dict[str, object]] = []
    home = user_home()
    roots = (
        []
        if workspace is not None and workspace.bare_mode
        else [
            *((root / relative_root, source) for relative_root, source in COMMAND_ROOTS),
            (home / ".claude/commands", "user"),
        ]
    )
    for command_root, source in roots:
        boundary = home if source == "user" else root
        if not command_root.exists() or not command_root.is_dir() or has_symlink_component(boundary, command_root):
            continue
        for path in _command_files(command_root):
            relative_path = plugin_component_path_reference(root, path)
            relative_command_path = path.relative_to(command_root).with_suffix("")
            name = ":".join(relative_command_path.parts)
            available, metadata, message = _inspect_command_file(boundary, path)
            discovered.append(
                {
                    "name": name,
                    "description": metadata.get("description", ""),
                    "argument_hint": metadata.get("argument_hint", ""),
                    "path": relative_path,
                    "source": source,
                    "available": available,
                    "message": message,
                }
            )
            if len(discovered) >= MAX_COMMAND_SCAN:
                break
        if len(discovered) >= MAX_COMMAND_SCAN:
            break

    workspace = workspace or create_local_workspace(root, "plugin-discovery")
    for component in enabled_plugin_component_files(workspace, "command"):
        path = component.path
        relative_path = plugin_component_path_reference(root, path)
        component_path = path.relative_to(component.plugin_root).with_suffix("")
        parts = component_path.parts[1:] if component_path.parts[:1] == ("commands",) else (path.stem,)
        local_name = ":".join(parts)
        name = f"{component.plugin}:{local_name}"
        if not COMMAND_INVOCATION_PATTERN.fullmatch(f"/{name}"):
            available, metadata, message = False, {}, "Plugin command name exceeds supported namespace depth."
        else:
            available, metadata, message = _inspect_command_file(component.plugin_root, path)
        discovered.append(
            {
                "name": name,
                "description": metadata.get("description", ""),
                "argument_hint": metadata.get("argument_hint", ""),
                "path": relative_path,
                "source": component.source,
                "available": available,
                "message": message,
            }
        )
        if len(discovered) >= MAX_COMMAND_SCAN:
            break

    selected = select_preferred_components(
        discovered,
        source_priority=_command_source_priority,
        duplicate_message=lambda name: (
            f"Duplicate custom command /{name} exists in multiple roots."
        ),
    )
    skill_names = {str(skill["name"]) for skill in discover_project_skill_metadata(workspace)}
    for command in selected:
        if parse_local_command(f"/{command['name']}") is not None:
            command["available"] = False
            command["message"] = f"Custom command /{command['name']} conflicts with a built-in command."
        elif command["name"] in skill_names:
            command["available"] = False
            command["message"] = f"Custom command /{command['name']} is shadowed by a skill with the same name."
    return sorted(selected, key=lambda command: (str(command["name"]), str(command["source"])))


def _command_source_priority(source: str) -> int:
    if source == "user":
        return 1
    if source in {"claude", "agents"}:
        return 2
    return 3


def _command_files(root: Path) -> list[Path]:
    files: list[Path] = []

    def visit(directory: Path, depth: int) -> None:
        if depth > MAX_COMMAND_DEPTH or len(files) >= MAX_COMMAND_SCAN:
            return
        try:
            children = sorted(directory.iterdir(), key=lambda path: path.name)
        except OSError:
            return
        for child in children:
            if len(files) >= MAX_COMMAND_SCAN:
                return
            if child.is_symlink():
                if child.suffix.lower() == ".md" and COMMAND_SEGMENT_PATTERN.fullmatch(child.stem):
                    files.append(child)
                continue
            if child.is_dir() and COMMAND_SEGMENT_PATTERN.fullmatch(child.name):
                visit(child, depth + 1)
            elif child.is_file() and child.suffix.lower() == ".md" and COMMAND_SEGMENT_PATTERN.fullmatch(child.stem):
                files.append(child)

    visit(root, 1)
    return files


def _inspect_command_file(root: Path, path: Path) -> tuple[bool, dict[str, str], str]:
    if has_symlink_component(root, path):
        return False, {}, "Command template path contains a symbolic link."
    try:
        content = read_regular_file_bytes(path, max_bytes=MAX_COMMAND_FILE_BYTES, label="Command template").decode("utf-8")
        metadata, body = _parse_command_content(content)
    except UnicodeDecodeError as error:
        return False, {}, f"Command template is not valid UTF-8: {error}"
    except (OSError, ValueError) as error:
        return False, {}, str(error)
    if not body.strip():
        return False, metadata, "Command template body must not be empty."
    return True, metadata, "Available."


def _parse_command_content(content: str) -> tuple[dict[str, str], str]:
    metadata, body = parse_scalar_frontmatter(
        content,
        frozenset({"description", "argument-hint"}),
    )
    description = " ".join(metadata.get("description", "").split())[:500]
    argument_hint = " ".join(metadata.get("argument-hint", "").split())[:200]
    return {"description": description, "argument_hint": argument_hint}, body.strip()


def _expand_command_body(body: str, arguments: str) -> str:
    protected = body.replace("$$", "\0DOLLAR\0")
    uses_arguments = "$ARGUMENTS" in protected
    uses_positionals = POSITIONAL_ARGUMENT_PATTERN.search(protected) is not None
    expanded = protected.replace("$ARGUMENTS", arguments)
    if uses_positionals:
        try:
            positional = shlex.split(arguments)
        except ValueError as error:
            raise ValueError(f"Custom command arguments are invalid: {error}") from error

        def replace_position(match: re.Match[str]) -> str:
            index = int(match.group(1) or match.group(2)) - 1
            return positional[index] if index < len(positional) else ""

        expanded = POSITIONAL_ARGUMENT_PATTERN.sub(replace_position, expanded)
    expanded = expanded.replace("\0DOLLAR\0", "$")
    if arguments and not uses_arguments and not uses_positionals:
        expanded = f"{expanded}\n\nArguments:\n{arguments}"
    if len(expanded) > MAX_EXPANDED_COMMAND_CHARS:
        raise ValueError(f"Expanded custom command exceeds {MAX_EXPANDED_COMMAND_CHARS} characters.")
    expanded = expanded.strip()
    if not expanded:
        raise ValueError("Expanded custom command is empty; provide the required arguments.")
    return expanded
