from __future__ import annotations

from typing import Any

from .action_parsing_delegation import AGENT_PROFILE_NAME_PATTERN
from .dynamic_workflow_types import WorkflowAgentRequest


def parse_workflow_agent_request(message: dict[str, Any]) -> WorkflowAgentRequest:
    call_id = message.get("call_id")
    if not isinstance(call_id, str) or not _is_call_id(call_id):
        raise ValueError("Workflow agent call has an invalid call ID.")
    task = message.get("task")
    if not isinstance(task, str) or not task.strip() or len(task.strip()) > 4_000:
        raise ValueError(f"Workflow {call_id} task must contain 1 to 4000 characters.")
    options = message.get("options")
    if not isinstance(options, dict):
        raise ValueError(f"Workflow {call_id} options must be an object.")
    allowed = {"context", "mode", "agent", "maxIterations", "isolation"}
    unknown = sorted(set(options) - allowed)
    if unknown:
        raise ValueError(f"Workflow {call_id} has unknown options: {', '.join(unknown)}")
    context = options.get("context")
    if context is not None and (not isinstance(context, str) or len(context) > 4_000):
        raise ValueError(f"Workflow {call_id} context must contain at most 4000 characters.")
    mode = options.get("mode", "explore")
    if mode not in {"explore", "code"}:
        raise ValueError(f"Workflow {call_id} mode must be explore or code.")
    agent_name = options.get("agent")
    if agent_name is not None and (
        not isinstance(agent_name, str) or not AGENT_PROFILE_NAME_PATTERN.fullmatch(agent_name)
    ):
        raise ValueError(f"Workflow {call_id} agent must be a valid profile name.")
    max_iterations = options.get("maxIterations", 4)
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or not 1 <= max_iterations <= 8:
        raise ValueError(f"Workflow {call_id} maxIterations must be between 1 and 8.")
    isolation = options.get("isolation")
    if isolation not in {None, "worktree"}:
        raise ValueError(f"Workflow {call_id} isolation must be worktree when provided.")
    return WorkflowAgentRequest(
        call_id=call_id,
        task=task.strip(),
        context=context.strip() if isinstance(context, str) and context.strip() else None,
        mode=mode,
        agent=agent_name,
        max_iterations=max_iterations,
        isolation=isolation,
    )


def request_to_dict(request: WorkflowAgentRequest) -> dict[str, object]:
    return {
        "call_id": request.call_id,
        "task": request.task,
        "context": request.context,
        "mode": request.mode,
        "agent": request.agent,
        "max_iterations": request.max_iterations,
        "isolation": request.isolation,
    }


def _is_call_id(value: str) -> bool:
    return len(value) == 9 and value.startswith("call-") and value[5:].isdigit()


__all__ = ["parse_workflow_agent_request", "request_to_dict"]
