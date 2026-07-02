from __future__ import annotations

from typing import Any

CommandKey = tuple[str, str]


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
