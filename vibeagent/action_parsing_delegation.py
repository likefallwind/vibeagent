from __future__ import annotations

import re
from typing import Any

from .action_parsing_helpers import ActionParseError
from .types import DelegateTaskAction, ListAgentsAction, SendMessageAction, TaskOutputAction, TaskStopAction


AGENT_PROFILE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def parse_delegation_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type == "list_agents":
        max_agents = value.get("max_agents", 100)
        if isinstance(max_agents, bool) or not isinstance(max_agents, int):
            raise ActionParseError("list_agents action max_agents must be an integer.", raw)
        if not 1 <= max_agents <= 500:
            raise ActionParseError("list_agents action max_agents must be between 1 and 500.", raw)
        return ListAgentsAction(type="list_agents", max_agents=max_agents)

    if action_type == "send_message":
        recipient = value.get("to")
        if not isinstance(recipient, str) or not AGENT_PROFILE_NAME_PATTERN.fullmatch(recipient.strip()):
            raise ActionParseError("send_message action requires a valid subagent ID in to.", raw)
        message = value.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ActionParseError("send_message action requires a non-empty message.", raw)
        message = message.strip()
        if len(message) > 4_000:
            raise ActionParseError("send_message action message must contain at most 4000 characters.", raw)
        return SendMessageAction(type="send_message", to=recipient.strip(), message=message)

    if action_type == "task_output":
        task_id = parse_task_id(value, raw, "task_output")
        block = value.get("block", True)
        if not isinstance(block, bool):
            raise ActionParseError("task_output action block must be a boolean.", raw)
        timeout_ms = value.get("timeout_ms", 30_000)
        if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int):
            raise ActionParseError("task_output action timeout_ms must be an integer.", raw)
        if timeout_ms < 0 or timeout_ms > 600_000:
            raise ActionParseError("task_output action timeout_ms must be between 0 and 600000.", raw)
        return TaskOutputAction(type="task_output", task_id=task_id, block=block, timeout_ms=timeout_ms)

    if action_type == "task_stop":
        return TaskStopAction(type="task_stop", task_id=parse_task_id(value, raw, "task_stop"))

    if action_type != "delegate_task":
        return None

    task = value.get("task")
    if not isinstance(task, str) or not task.strip():
        raise ActionParseError("delegate_task action requires a non-empty task.", raw)
    task = task.strip()
    if len(task) > 4_000:
        raise ActionParseError("delegate_task action task must contain at most 4000 characters.", raw)

    context = value.get("context")
    if context is not None and not isinstance(context, str):
        raise ActionParseError("delegate_task action context must be a string when provided.", raw)
    context = context.strip() if isinstance(context, str) and context.strip() else None
    if context is not None and len(context) > 4_000:
        raise ActionParseError("delegate_task action context must contain at most 4000 characters.", raw)

    max_iterations = value.get("max_iterations", 4)
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int):
        raise ActionParseError("delegate_task action max_iterations must be an integer.", raw)
    if max_iterations < 1 or max_iterations > 8:
        raise ActionParseError("delegate_task action max_iterations must be between 1 and 8.", raw)

    mode = value.get("mode", "explore")
    if mode not in {"explore", "code"}:
        raise ActionParseError("delegate_task action mode must be explore or code.", raw)

    agent = value.get("agent")
    if agent is not None and (not isinstance(agent, str) or not AGENT_PROFILE_NAME_PATTERN.fullmatch(agent.strip())):
        raise ActionParseError("delegate_task action agent must be a valid project agent profile name.", raw)
    agent = agent.strip() if isinstance(agent, str) else None

    run_in_background = value.get("run_in_background", False)
    if not isinstance(run_in_background, bool):
        raise ActionParseError("delegate_task action run_in_background must be a boolean.", raw)
    isolation = value.get("isolation")
    if isolation not in {None, "worktree"}:
        raise ActionParseError("delegate_task action isolation must be worktree when provided.", raw)
    return DelegateTaskAction(
        type="delegate_task",
        task=task,
        context=context,
        max_iterations=max_iterations,
        mode=mode,
        agent=agent,
        run_in_background=run_in_background,
        isolation=isolation,
    )


def parse_task_id(value: dict[str, Any], raw: str, action_type: str) -> str:
    task_id = value.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty task_id.", raw)
    task_id = task_id.strip()
    if not AGENT_PROFILE_NAME_PATTERN.fullmatch(task_id):
        raise ActionParseError(f"{action_type} action task_id must be a valid subagent ID.", raw)
    return task_id
