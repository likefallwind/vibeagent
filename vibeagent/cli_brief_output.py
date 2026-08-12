from __future__ import annotations

import re
import sys
from typing import TextIO


ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def brief_message_observer(stream: TextIO | None = None):
    output = stream or sys.stderr

    def observe(_session_dir, event: dict[str, object]) -> None:
        if event.get("type") != "agent_user_message":
            return
        message = display_safe_message(event.get("message"))
        if not message:
            return
        output.write(f"Agent update: {message}\n")
        output.flush()

    return observe


def display_safe_message(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(
        character
        for character in ANSI_ESCAPE.sub("", value).strip()
        if ord(character) >= 32 or character in {"\n", "\t"}
    )[:2_000]


__all__ = ["brief_message_observer", "display_safe_message"]
