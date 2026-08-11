from __future__ import annotations

from dataclasses import dataclass

from .model_effort import (
    MODEL_EFFORT_LEVELS,
    ModelEffortSetting,
    configure_model_effort,
    normalize_model_effort,
)
from .types import ChatClient


INTERACTIVE_EFFORT_LEVELS = MODEL_EFFORT_LEVELS


@dataclass(frozen=True)
class InteractiveEffortSelection:
    override: str | None
    changed: bool
    text: str


def resolve_interactive_effort_selection(
    argument: str | None,
    current_override: str | None,
    *,
    locked: bool = False,
) -> InteractiveEffortSelection:
    if locked and argument is not None:
        raise ValueError("CLAUDE_CODE_EFFORT_LEVEL locks the effort for this session.")
    if argument is None:
        override = current_override
    else:
        override = normalize_interactive_effort(argument)
    changed = argument is not None and override != current_override
    source = (
        "CLAUDE_CODE_EFFORT_LEVEL"
        if locked
        else "session override" if override is not None else "provider/model default"
    )
    level = override or "auto"
    action = "Switched interactive effort." if changed else "Interactive effort configuration."
    return InteractiveEffortSelection(
        override=override,
        changed=changed,
        text="\n".join([action, f"  effort: {level}", f"  source: {source}"]),
    )


def normalize_interactive_effort(value: str) -> str | None:
    return normalize_model_effort(value, usage="Usage: /effort")


def configure_interactive_effort(
    client: ChatClient,
    effort: str | None,
    *,
    locked: bool = False,
) -> ChatClient:
    return configure_model_effort(client, ModelEffortSetting(effort, locked=locked))


__all__ = [
    "INTERACTIVE_EFFORT_LEVELS",
    "InteractiveEffortSelection",
    "configure_interactive_effort",
    "normalize_interactive_effort",
    "resolve_interactive_effort_selection",
]
