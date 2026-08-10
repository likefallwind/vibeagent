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
    if trimmed == "/plugin" or trimmed.startswith("/plugin "):
        return make_local_command("plugin", trimmed[7:].strip() or None)
    if trimmed == "/reload-plugins":
        return make_local_command("reload_plugins", None)
    if trimmed == "/agents" or trimmed.startswith("/agents "):
        return make_local_command("agents", trimmed[7:].strip() or None)
    if trimmed == "/skills" or trimmed.startswith("/skills "):
        return make_local_command("skills", trimmed[7:].strip() or None)
    if trimmed == "/clear":
        return make_local_command("clear", None)
    if trimmed == "/goal" or trimmed.startswith("/goal "):
        return make_local_command("goal", trimmed[5:].strip() or None)
    if trimmed == "/workflows" or trimmed.startswith("/workflows "):
        return make_local_command("workflows", trimmed[10:].strip() or None)
    if trimmed in {"/list-agents", "/peers"}:
        return make_local_command("list_agents_local", None)
    if trimmed == "/peer-inbox" or trimmed.startswith("/peer-inbox "):
        return make_local_command("peer_inbox", trimmed[11:].strip() or None)
    if trimmed == "/usage":
        return make_local_command("usage", None)
    if trimmed == "/cost":
        return make_local_command("cost", None)
    if trimmed == "/approval" or trimmed.startswith("/approval "):
        return make_local_command("approval", trimmed[9:].strip() or None)
    if trimmed == "/system-prompt" or trimmed.startswith("/system-prompt "):
        return make_local_command("system_prompt", trimmed[14:].strip() or None)
    if trimmed == "/append-system-prompt" or trimmed.startswith("/append-system-prompt "):
        return make_local_command("append_system_prompt", trimmed[21:].strip() or None)
    if trimmed == "/resume" or trimmed.startswith("/resume "):
        return make_local_command("resume", trimmed[8:].strip() or None)
    if trimmed == "/compact" or trimmed.startswith("/compact "):
        return make_local_command("compact", trimmed[9:].strip() or None)
    if trimmed == "/chat" or trimmed.startswith("/chat "):
        return make_local_command("chat", trimmed[5:].strip() or None)
    if trimmed == "/code" or trimmed.startswith("/code "):
        return make_local_command("code", trimmed[5:].strip() or None)
    return None
