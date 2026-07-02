from __future__ import annotations

from dataclasses import asdict, is_dataclass
import sys

from .actions import execute_action as _default_execute_action


def plain_data(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, list):
        return [plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): plain_data(item) for key, item in value.items()}
    return value


def field_value(value: object, name: str, default: object = None) -> object:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def clip(value: str, max_length: int) -> str:
    compacted = value.strip()
    if len(compacted) <= max_length:
        return compacted
    return f"{compacted[:max_length]}\n[context output truncated]"


def indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def commands_attr(name: str, default: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    if commands_module is None:
        return default
    return getattr(commands_module, name, default)
