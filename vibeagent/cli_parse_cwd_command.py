from __future__ import annotations

import shlex


def parse_interactive_cwd_command_argument(
    argument: str | None,
    usage: str,
) -> tuple[str | None, str | None, str | None, bool]:
    if not argument:
        return None, None, None, False
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if "--cwd" in argument:
            return None, None, f"{usage}\n  error: {error}", True
        return argument, None, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag == "--cwd":
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return argument, None, None, False

    cwd: str | None = None
    command_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            command_parts.extend(parts[index + 1 :])
            break
        if part == "--cwd" or part.startswith("--cwd="):
            if cwd is not None:
                return None, None, f"{usage}\n  error: --cwd can only be provided once.", True
            if part.startswith("--cwd="):
                cwd = part.split("=", 1)[1]
                index += 1
            else:
                if index + 1 >= len(parts):
                    return None, None, f"{usage}\n  error: --cwd requires a value.", True
                cwd = parts[index + 1]
                index += 2
            continue
        command_parts.extend(parts[index:])
        break

    command = shlex.join(command_parts).strip()
    if not command:
        return None, cwd, f"{usage}\n  error: command is required.", True
    return command, cwd, None, True


def parse_interactive_check_run_sequence_argument(
    argument: str | None,
) -> tuple[list[str] | None, str | None, str | None, bool]:
    usage = "Usage: /check-run-seq [--cwd PATH] -- <cmd> ;; <cmd>"
    if not argument:
        return None, None, None, False
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if "--cwd" in argument:
            return None, None, f"{usage}\n  error: {error}", True
        return None, None, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag == "--cwd":
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return None, None, None, False

    cwd: str | None = None
    command_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            command_parts.extend(parts[index + 1 :])
            break
        if part == "--cwd" or part.startswith("--cwd="):
            if cwd is not None:
                return None, None, f"{usage}\n  error: --cwd can only be provided once.", True
            if part.startswith("--cwd="):
                cwd = part.split("=", 1)[1]
                index += 1
            else:
                if index + 1 >= len(parts):
                    return None, None, f"{usage}\n  error: --cwd requires a value.", True
                cwd = parts[index + 1]
                index += 2
            continue
        command_parts.extend(parts[index:])
        break

    commands: list[str] = []
    current: list[str] = []
    for part in command_parts:
        if part == ";;":
            command = shlex.join(current).strip()
            if command:
                commands.append(command)
            current = []
            continue
        current.append(part)
    command = shlex.join(current).strip()
    if command:
        commands.append(command)
    if not commands:
        return None, cwd, f"{usage}\n  error: at least one command is required.", True
    if len(commands) > 10:
        return None, cwd, f"{usage}\n  error: expected at most 10 commands.", True
    return commands, cwd, None, True
