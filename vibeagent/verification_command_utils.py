from __future__ import annotations

import re
import shlex
from pathlib import PurePath
from typing import Any

from .agent_approval_targets import command_target

CommandKey = tuple[str, str]
_PYTHON_EXECUTABLE = re.compile(r"python(?:\d+(?:\.\d+)*)?(?:\.exe)?", re.IGNORECASE)


def command_key(command: object, cwd: object = ".") -> CommandKey | None:
    if not isinstance(command, str) or not command.strip():
        return None
    return command, cwd if isinstance(cwd, str) and cwd else "."


def command_keys_from_objects(items: object) -> set[CommandKey]:
    if not isinstance(items, list):
        return set()
    keys: set[CommandKey] = set()
    for item in items:
        key = command_key(getattr(item, "command", None), getattr(item, "cwd", "."))
        if key is not None:
            keys.add(key)
    return keys


def command_keys_from_dicts(items: object) -> set[CommandKey]:
    if not isinstance(items, list):
        return set()
    keys: set[CommandKey] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        key = command_key(item.get("command"), item.get("cwd"))
        if key is not None:
            keys.add(key)
    return keys


def matching_verification_command_key(
    command: object,
    cwd: object,
    candidates: set[CommandKey],
) -> CommandKey | None:
    key = command_key(command, cwd)
    if key is None:
        return None
    if key in candidates:
        return key
    normalized = _normalized_verification_command(key[0])
    if normalized is None:
        return None
    for candidate in candidates:
        if candidate[1] == key[1] and _normalized_verification_command(candidate[0]) == normalized:
            return candidate
    return None


def _normalized_verification_command(command: str) -> tuple[str, ...] | None:
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    if not parts or not _PYTHON_EXECUTABLE.fullmatch(PurePath(parts[0]).name):
        return None
    normalized = [parts[0]]
    before_program = True
    for part in parts[1:]:
        if before_program and part == "-B":
            continue
        normalized.append(part)
        if before_program and (part == "-m" or not part.startswith("-")):
            before_program = False
    return tuple(normalized)


def verification_commands_from_objects(
    suggested_checks: object,
    focused_test_commands: object = None,
) -> set[CommandKey]:
    suggested_commands = command_keys_from_objects(suggested_checks)
    if suggested_commands:
        return suggested_commands
    return command_keys_from_objects(focused_test_commands)


def verification_commands_from_final_review(final_review: object) -> set[CommandKey]:
    return verification_commands_from_objects(
        getattr(final_review, "suggested_checks", []),
        getattr(final_review, "focused_test_commands", []),
    )


def verification_commands_from_final_review_payload(result: dict[str, Any]) -> set[CommandKey]:
    suggested_commands = command_keys_from_dicts(result.get("suggested_checks"))
    if suggested_commands:
        return suggested_commands
    return command_keys_from_dicts(result.get("focused_test_commands"))


def verification_command_label(command: str, cwd: str) -> str:
    return command if cwd in {"", "."} else command_target(command, cwd)


def failed_verification_command_label(command: str, cwd: str, reason: str) -> str:
    return f"{verification_command_label(command, cwd)} ({reason})"
