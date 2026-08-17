from __future__ import annotations

import socket
from secrets import token_hex

from .session_names import MAX_SESSION_NAME_CHARS, normalize_session_name


REMOTE_CONTROL_NAME_SUFFIX_CHARS = 6
MAX_REMOTE_CONTROL_PREFIX_CHARS = (
    MAX_SESSION_NAME_CHARS - REMOTE_CONTROL_NAME_SUFFIX_CHARS - 1
)


def validate_remote_control_name_options(
    value: str | bool | None,
    prefix: str | None,
) -> str | None:
    try:
        if isinstance(value, str):
            normalize_session_name(value)
        if prefix is not None:
            normalized = normalize_session_name(prefix)
            if len(normalized) > MAX_REMOTE_CONTROL_PREFIX_CHARS:
                raise ValueError(
                    "Remote Control session name prefix must not exceed "
                    f"{MAX_REMOTE_CONTROL_PREFIX_CHARS} characters."
                )
    except ValueError as error:
        return str(error)
    return None


def resolve_remote_control_name(
    value: str | bool,
    prefix: str | None,
    *,
    hostname: str | None = None,
    suffix: str | None = None,
) -> str:
    if isinstance(value, str):
        return normalize_session_name(value)
    base = normalize_session_name(prefix if prefix is not None else (hostname or socket.gethostname()))
    if len(base) > MAX_REMOTE_CONTROL_PREFIX_CHARS:
        base = base[:MAX_REMOTE_CONTROL_PREFIX_CHARS].rstrip()
    generated_suffix = suffix or token_hex(REMOTE_CONTROL_NAME_SUFFIX_CHARS // 2)
    return normalize_session_name(f"{base}-{generated_suffix}")


__all__ = [
    "MAX_REMOTE_CONTROL_PREFIX_CHARS",
    "resolve_remote_control_name",
    "validate_remote_control_name_options",
]
