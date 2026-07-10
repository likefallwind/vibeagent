from __future__ import annotations

import re
import shlex
from collections import Counter
from pathlib import Path

from .command_parsing import parse_local_command
from .workspace_metadata_files import has_symlink_component, parse_scalar_frontmatter, read_regular_file_bytes


COMMAND_ROOTS = ((".claude/commands", "claude"), (".agents/commands", "agents"))
COMMAND_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
COMMAND_INVOCATION_PATTERN = re.compile(r"^/([A-Za-z0-9][A-Za-z0-9._-]*(?::[A-Za-z0-9][A-Za-z0-9._-]*){0,3})(?:\s+(.*))?$")
POSITIONAL_ARGUMENT_PATTERN = re.compile(r"\$(?:\{([1-9])\}|([1-9])(?![0-9]))")
MAX_COMMAND_FILE_BYTES = 64_000
MAX_COMMAND_SCAN = 1_000
MAX_COMMAND_DEPTH = 4
MAX_EXPANDED_COMMAND_CHARS = 100_000


def read_project_prompt_commands(root: Path, max_commands: int = 100) -> dict[str, object]:
    if max_commands < 1 or max_commands > 500:
        raise ValueError("max_commands must be between 1 and 500.")
    commands = _discover_project_prompt_commands(root.resolve())
    shown = commands[:max_commands]
    return {
        "ok": True,
        "commands": shown,
        "total": len(commands),
        "truncated": len(commands) > len(shown),
        "invalid": sum(1 for command in commands if not command["available"]),
        "message": f"Found {len(commands)} project command template(s); {sum(1 for command in commands if command['available'])} available.",
    }


def format_project_prompt_commands(root: Path, max_commands: int = 100) -> str:
    report = read_project_prompt_commands(root, max_commands=max_commands)
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


def expand_project_prompt_command(root: Path, invocation: str) -> dict[str, object] | None:
    match = COMMAND_INVOCATION_PATTERN.fullmatch(invocation.strip())
    if match is None:
        return None
    name = match.group(1)
    arguments = match.group(2) or ""
    command = _load_project_prompt_command(root.resolve(), name)
    if command is None:
        raise ValueError(f"Unknown command: /{name}. Use /custom-commands to list project commands.")
    prompt = _expand_command_body(str(command["body"]), arguments)
    return {
        "name": name,
        "arguments": arguments,
        "prompt": prompt,
        "path": command["path"],
        "source": command["source"],
        "description": command["description"],
    }


def _load_project_prompt_command(root: Path, name: str) -> dict[str, object] | None:
    matches = [command for command in _discover_project_prompt_commands(root) if command["name"] == name]
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
    return {**command, **metadata, "body": body}


def _discover_project_prompt_commands(root: Path) -> list[dict[str, object]]:
    discovered: list[dict[str, object]] = []
    for relative_root, source in COMMAND_ROOTS:
        command_root = root / relative_root
        if not command_root.exists() or not command_root.is_dir() or has_symlink_component(root, command_root):
            continue
        for path in _command_files(command_root):
            relative_path = path.relative_to(root).as_posix()
            relative_command_path = path.relative_to(command_root).with_suffix("")
            name = ":".join(relative_command_path.parts)
            available, metadata, message = _inspect_command_file(root, path)
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

    counts = Counter(str(command["name"]) for command in discovered)
    duplicates = {name for name, count in counts.items() if count > 1}
    for command in discovered:
        if command["name"] in duplicates:
            command["available"] = False
            command["message"] = f"Duplicate project command /{command['name']} exists in multiple roots."
        elif parse_local_command(f"/{command['name']}") is not None:
            command["available"] = False
            command["message"] = f"Project command /{command['name']} conflicts with a built-in command."
    return sorted(discovered, key=lambda command: (str(command["name"]), str(command["source"])))


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
