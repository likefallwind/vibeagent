from __future__ import annotations

from .agent_runtime_utils import append_session_event
from .async_hook_runtime import (
    async_hook_notifications_prompt,
    collect_async_hook_notifications,
)
from .types import AgentLogger, ChatMessage
from .workspace_core import RunWorkspace


def inject_async_hook_notifications(
    workspace: RunWorkspace,
    messages: list[ChatMessage],
    *,
    iteration: int,
    logger: AgentLogger | None,
) -> int:
    notifications = collect_async_hook_notifications(workspace)
    if not notifications:
        return 0
    messages.append(
        ChatMessage(
            role="user",
            content=async_hook_notifications_prompt(notifications),
        )
    )
    append_session_event(
        workspace.session_dir,
        "async_hook_notifications_delivered",
        {
            "iteration": iteration,
            "count": len(notifications),
            "process_ids": [item.process_id for item in notifications],
            "rewake": any(item.rewake for item in notifications),
        },
    )
    if logger:
        logger(
            "async hook notifications",
            f"Delivered {len(notifications)} async hook result(s).",
        )
    return len(notifications)


__all__ = ["inject_async_hook_notifications"]
