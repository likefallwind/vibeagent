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
    system_messages: list[str],
    *,
    iteration: int,
    logger: AgentLogger | None,
) -> int:
    notifications = collect_async_hook_notifications(workspace)
    if not notifications:
        return 0
    contexts = [item for item in notifications if item.additional_context]
    system_messages.extend(
        item.system_message for item in notifications if item.system_message
    )
    if contexts:
        messages.append(
            ChatMessage(
                role="user",
                content=async_hook_notifications_prompt(contexts),
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
            "context_count": len(contexts),
            "system_message_count": sum(
                bool(item.system_message) for item in notifications
            ),
        },
    )
    if logger:
        logger(
            "async hook notifications",
            f"Delivered {len(notifications)} async hook result(s).",
        )
    return len(contexts)


__all__ = ["inject_async_hook_notifications"]
