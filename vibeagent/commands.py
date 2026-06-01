from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .minimax import get_minimax_api_key_info_from_env, get_minimax_defaults


@dataclass(frozen=True)
class LocalCommand:
    type: Literal["exit", "help", "model", "chat", "code"]
    argument: str | None = None


def parse_local_command(value: str) -> LocalCommand | None:
    # Recognize slash commands before sending anything to the model.
    trimmed = value.strip()
    if trimmed == "/exit":
        return LocalCommand(type="exit")
    if trimmed == "/help":
        return LocalCommand(type="help")
    if trimmed == "/model":
        return LocalCommand(type="model")
    if trimmed == "/chat" or trimmed.startswith("/chat "):
        return LocalCommand(type="chat", argument=trimmed[5:].strip() or None)
    if trimmed == "/code" or trimmed.startswith("/code "):
        return LocalCommand(type="code", argument=trimmed[5:].strip() or None)
    return None


def is_exit_command(value: str) -> bool:
    # Helper for tests and callers that only care whether input is an exit command.
    command = parse_local_command(value)
    return command is not None and command.type == "exit"


def get_help_text() -> str:
    # Static help text shown by `/help` in the interactive prompt.
    return "\n".join(
        [
            "Commands:",
            "  /help   Show this help.",
            "  /model  Show MiniMax model configuration.",
            "  /chat   Switch to daily conversation mode, or chat once with /chat <message>.",
            "  /code   Switch to coding mode, or run one coding task with /code <task>.",
            "  /exit   Exit the interactive prompt.",
            "",
            "In coding mode, normal input is treated as a programming task.",
            "In chat mode, normal input is treated as daily conversation.",
        ]
    )


def get_model_text(env: dict[str, str | None] | None = None) -> str:
    # Show resolved model and key-source info without leaking secret material.
    defaults = get_minimax_defaults(env)
    api_key = get_minimax_api_key_info_from_env(env)
    return "\n".join(
        [
            "MiniMax configuration:",
            f"  model: {defaults['model']}",
            f"  baseUrl: {defaults['base_url']}",
            f"  apiKey: {'configured via ' + api_key.name if api_key else 'missing'}",
        ]
    )
