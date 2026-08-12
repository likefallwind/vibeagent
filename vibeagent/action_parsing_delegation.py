from __future__ import annotations

import re
from typing import Any

from .action_parsing_helpers import ActionParseError
from .review_profiles import REVIEW_PERSPECTIVES
from .types import DeepReviewAction, DelegateTaskAction, ListAgentsAction, SendMessageAction, TaskOutputAction, TaskStopAction


AGENT_PROFILE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
AGENT_REFERENCE_PATTERN = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9]):)?[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
)


def parse_delegation_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type == "deep_review":
        return _parse_deep_review_action(value, raw)
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
        approve_plan = value.get("approve_plan", False)
        if not isinstance(approve_plan, bool):
            raise ActionParseError("send_message action approve_plan must be a boolean.", raw)
        return SendMessageAction(
            type="send_message",
            to=recipient.strip(),
            message=message,
            approve_plan=approve_plan,
        )

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
    if mode not in {"explore", "code", "plan"}:
        raise ActionParseError("delegate_task action mode must be explore, code, or plan.", raw)

    agent = value.get("agent")
    if agent is not None and (not isinstance(agent, str) or not AGENT_REFERENCE_PATTERN.fullmatch(agent.strip())):
        raise ActionParseError("delegate_task action agent must be a valid project agent profile name.", raw)
    agent = agent.strip() if isinstance(agent, str) else None

    run_in_background = value.get("run_in_background", False)
    if not isinstance(run_in_background, bool):
        raise ActionParseError("delegate_task action run_in_background must be a boolean.", raw)
    isolation = value.get("isolation")
    if isolation not in {None, "worktree"}:
        raise ActionParseError("delegate_task action isolation must be worktree when provided.", raw)
    teammate_name = value.get("teammate_name")
    if teammate_name is not None and (
        not isinstance(teammate_name, str)
        or not AGENT_PROFILE_NAME_PATTERN.fullmatch(teammate_name.strip())
    ):
        raise ActionParseError("delegate_task action teammate_name must be a valid teammate name.", raw)
    teammate_name = teammate_name.strip() if isinstance(teammate_name, str) else None
    if teammate_name == "lead":
        raise ActionParseError("delegate_task action teammate_name cannot use the reserved name lead.", raw)
    if mode == "plan" and teammate_name is None:
        raise ActionParseError("delegate_task action plan mode requires a named teammate.", raw)
    if teammate_name is not None:
        run_in_background = True
    return DelegateTaskAction(
        type="delegate_task",
        task=task,
        context=context,
        max_iterations=max_iterations,
        mode=mode,
        agent=agent,
        run_in_background=run_in_background,
        isolation=isolation,
        teammate_name=teammate_name,
    )


def _parse_deep_review_action(value: dict[str, Any], raw: str) -> DeepReviewAction:
    review_kind = value.get("review_kind", "defects")
    if not isinstance(review_kind, str) or review_kind not in REVIEW_PERSPECTIVES:
        raise ActionParseError("deep_review action review_kind must be defects, cleanup, or security.", raw)
    allowed = REVIEW_PERSPECTIVES[review_kind]
    perspectives = value.get("perspectives", list(allowed))
    if (
        not isinstance(perspectives, list)
        or not perspectives
        or len(perspectives) > len(allowed)
        or any(not isinstance(item, str) or item not in allowed for item in perspectives)
        or len(set(perspectives)) != len(perspectives)
    ):
        raise ActionParseError(
            f"deep_review action perspectives must be a non-empty unique list for the {review_kind} review profile: "
            f"{', '.join(allowed)}.",
            raw,
        )
    max_iterations = value.get("max_iterations", 4)
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int):
        raise ActionParseError("deep_review action max_iterations must be an integer.", raw)
    if not 1 <= max_iterations <= 8:
        raise ActionParseError("deep_review action max_iterations must be between 1 and 8.", raw)
    base_ref = value.get("base_ref")
    if base_ref is not None:
        if not isinstance(base_ref, str) or not base_ref.strip():
            raise ActionParseError("deep_review action base_ref must be a non-empty string when provided.", raw)
        base_ref = base_ref.strip()
        if len(base_ref) > 200 or any(character.isspace() for character in base_ref):
            raise ActionParseError("deep_review action base_ref must be one token of at most 200 characters.", raw)
        if base_ref.startswith("-"):
            raise ActionParseError("deep_review action base_ref must not start with '-'.", raw)
    target = value.get("target")
    if target is not None:
        if not isinstance(target, str) or not target.strip():
            raise ActionParseError("deep_review action target must be a non-empty string when provided.", raw)
        target = target.strip()
        if len(target) > 1_000 or "\x00" in target:
            raise ActionParseError("deep_review action target must contain at most 1000 characters and no NUL.", raw)
    if base_ref is not None and target is not None:
        raise ActionParseError("deep_review action accepts either base_ref or target, not both.", raw)
    return DeepReviewAction(
        type="deep_review",
        review_kind=review_kind,
        perspectives=list(perspectives),
        max_iterations=max_iterations,
        base_ref=base_ref,
        target=target,
    )


def parse_task_id(value: dict[str, Any], raw: str, action_type: str) -> str:
    task_id = value.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty task_id.", raw)
    task_id = task_id.strip()
    if not AGENT_PROFILE_NAME_PATTERN.fullmatch(task_id):
        raise ActionParseError(f"{action_type} action task_id must be a valid subagent ID.", raw)
    return task_id
