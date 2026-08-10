from __future__ import annotations

from .agent_runtime_utils import append_session_event
from .monitor_runtime import collect_monitor_notifications, monitor_notifications_prompt
from .types import AgentLogger, ChatMessage
from .workspace_core import RunWorkspace


def inject_monitor_notifications(
    workspace: RunWorkspace,
    messages: list[ChatMessage],
    *,
    iteration: int,
    logger: AgentLogger | None,
) -> int:
    notifications = collect_monitor_notifications(workspace)
    if not notifications:
        return 0
    messages.append(
        ChatMessage(role="user", content=monitor_notifications_prompt(notifications))
    )
    append_session_event(
        workspace.session_dir,
        "monitor_notifications_delivered",
        {
            "iteration": iteration,
            "count": len(notifications),
            "task_ids": sorted({item.task_id for item in notifications}),
            "statuses": [item.status for item in notifications],
        },
    )
    if logger:
        logger(
            "monitor notifications",
            f"Delivered {len(notifications)} monitor notification(s).",
        )
    return len(notifications)


__all__ = ["inject_monitor_notifications"]
