from __future__ import annotations

from typing import Any

from .types import ChatClient


def configure_agent_profile_client(
    client: ChatClient,
    *,
    model: str | None,
    effort: str | None,
) -> ChatClient:
    selected_model = None if model in {None, "inherit"} else model
    if selected_model is None and effort is None:
        return client
    configure = getattr(client, "with_agent_profile", None)
    if not callable(configure):
        raise ValueError(
            "The active chat client does not support agent profile model or effort overrides."
        )
    configured: Any = configure(model=selected_model, effort=effort)
    if configured is None or not callable(getattr(configured, "complete", None)):
        raise ValueError("The chat client returned an invalid configured profile client.")
    return configured


__all__ = ["configure_agent_profile_client"]
