from __future__ import annotations

import json

from .agent_runtime_utils import append_session_event
from .agent_tool_results import build_tool_result_payload
from .background_delegate_runtime import collect_background_delegate_notifications
from .types import AgentLogger, ChatMessage, Observation
from .workspace_core import RunWorkspace


def inject_background_delegate_notifications(
    workspace: RunWorkspace,
    messages: list[ChatMessage],
    observations: list[Observation],
    *,
    iteration: int,
    logger: AgentLogger | None,
) -> int:
    completed = collect_background_delegate_notifications(workspace)
    if not completed:
        return 0
    payloads = [build_tool_result_payload(observation) for observation in completed]
    observations.extend(completed)
    messages.append(
        ChatMessage(
            role="user",
            content=(
                "Background subagent completion notification(s):\n"
                + json.dumps(payloads, ensure_ascii=False)
            ),
        )
    )
    for observation, payload in zip(completed, payloads):
        append_session_event(
            workspace.session_dir,
            "background_delegate_notification",
            {
                "iteration": iteration,
                "task_id": observation.task_id,
                "result": payload,
            },
        )
        if logger:
            logger("background subagent completed", observation.message)
    return len(completed)


__all__ = ["inject_background_delegate_notifications"]
