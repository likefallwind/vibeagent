from __future__ import annotations

import re

from .command_safety import get_blocked_command_reason


_DESTRUCTIVE_SYSTEM_CMDLET = re.compile(
    r"(?i)(?:^|[;|&\n])\s*(?:format-volume|clear-disk|initialize-disk|"
    r"stop-computer|restart-computer|remove-computer)\b"
)
_BROAD_REMOVE_ITEM = re.compile(
    r"(?is)\bremove-item\b(?=[^;\n]*(?:-recurse|-r)\b)"
    r"(?=[^;\n]*(?:-force|-fo)\b)[^;\n]*"
    r"(?:['\"]?(?:[a-z]:\\|/|\\\\|\$home|~|\*)['\"]?(?:\s|$))"
)


def get_blocked_powershell_reason(command: str) -> str | None:
    generic = get_blocked_command_reason(command)
    if generic is not None:
        return generic
    native_generic = get_blocked_command_reason(f"pwsh -NoProfile -Command {command}")
    if native_generic is not None:
        return native_generic
    if _DESTRUCTIVE_SYSTEM_CMDLET.search(command):
        return "destructive PowerShell system cmdlets are not allowed in project mode"
    if _BROAD_REMOVE_ITEM.search(command):
        return "recursive forced deletion of broad paths is not allowed in project mode"
    return None


__all__ = ["get_blocked_powershell_reason"]
