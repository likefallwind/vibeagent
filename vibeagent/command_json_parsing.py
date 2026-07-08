from __future__ import annotations

from .command_types import LocalCommand, make_local_command


def parse_json_local_command(trimmed: str) -> LocalCommand | None:
    if trimmed == "/config-check" or trimmed.startswith("/config-check "):
        return make_local_command("config_check", trimmed[14:].strip() or None)
    if trimmed == "/check-json-set" or trimmed.startswith("/check-json-set "):
        return make_local_command("check_json_set", trimmed[16:].strip() or None)
    if trimmed == "/json-set" or trimmed.startswith("/json-set "):
        return make_local_command("json_set", trimmed[10:].strip() or None)
    if trimmed == "/check-json-remove" or trimmed.startswith("/check-json-remove "):
        return make_local_command("check_json_remove", trimmed[19:].strip() or None)
    if trimmed == "/json-remove" or trimmed.startswith("/json-remove "):
        return make_local_command("json_remove", trimmed[13:].strip() or None)
    if trimmed == "/check-json-patch" or trimmed.startswith("/check-json-patch "):
        return make_local_command("check_json_patch", trimmed[18:].strip() or None)
    if trimmed == "/json-patch" or trimmed.startswith("/json-patch "):
        return make_local_command("json_patch", trimmed[12:].strip() or None)
    return None
