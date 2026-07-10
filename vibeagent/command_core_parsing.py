from __future__ import annotations

from .command_types import LocalCommand, make_local_command


def parse_core_local_command(trimmed: str) -> LocalCommand | None:
    if trimmed == "/exit":
        return make_local_command("exit", None)
    if trimmed == "/help":
        return make_local_command("help", None)
    if trimmed == "/model":
        return make_local_command("model", None)
    if trimmed == "/config":
        return make_local_command("config", None)
    if trimmed == "/custom-commands":
        return make_local_command("custom_commands", None)
    if trimmed == "/clear":
        return make_local_command("clear", None)
    if trimmed == "/usage":
        return make_local_command("usage", None)
    if trimmed == "/cost":
        return make_local_command("cost", None)
    if trimmed == "/approval" or trimmed.startswith("/approval "):
        return make_local_command("approval", trimmed[9:].strip() or None)
    if trimmed == "/resume" or trimmed.startswith("/resume "):
        return make_local_command("resume", trimmed[8:].strip() or None)
    if trimmed == "/compact" or trimmed.startswith("/compact "):
        return make_local_command("compact", trimmed[9:].strip() or None)
    if trimmed == "/chat" or trimmed.startswith("/chat "):
        return make_local_command("chat", trimmed[5:].strip() or None)
    if trimmed == "/code" or trimmed.startswith("/code "):
        return make_local_command("code", trimmed[5:].strip() or None)
    return None
