from __future__ import annotations

from dataclasses import dataclass

from .agent_profile_client import configure_agent_profile_client
from .types import ChatClient


INTERACTIVE_EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")


@dataclass(frozen=True)
class InteractiveEffortSelection:
    override: str | None
    changed: bool
    text: str


def resolve_interactive_effort_selection(
    argument: str | None,
    current_override: str | None,
) -> InteractiveEffortSelection:
    if argument is None:
        override = current_override
    else:
        override = normalize_interactive_effort(argument)
    changed = argument is not None and override != current_override
    source = "session override" if override is not None else "provider/model default"
    level = override or "auto"
    action = "Switched interactive effort." if changed else "Interactive effort configuration."
    return InteractiveEffortSelection(
        override=override,
        changed=changed,
        text="\n".join([action, f"  effort: {level}", f"  source: {source}"]),
    )


def normalize_interactive_effort(value: str) -> str | None:
    normalized = value.strip().lower()
    if normalized in {"auto", "default"}:
        return None
    if normalized not in INTERACTIVE_EFFORT_LEVELS:
        choices = "|".join(("auto", *INTERACTIVE_EFFORT_LEVELS))
        raise ValueError(f"Usage: /effort [{choices}]")
    return normalized


def configure_interactive_effort(client: ChatClient, effort: str | None) -> ChatClient:
    if effort is None:
        return client
    return configure_agent_profile_client(client, model=None, effort=effort)


__all__ = [
    "INTERACTIVE_EFFORT_LEVELS",
    "InteractiveEffortSelection",
    "configure_interactive_effort",
    "normalize_interactive_effort",
    "resolve_interactive_effort_selection",
]
