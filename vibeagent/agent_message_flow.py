from __future__ import annotations

from .agent_runtime_utils import compact_agent_message_history
from .types import ApprovalPolicy, ChatMessage, ContentBlock, Observation, PlanItem
from .workspace_core import RunWorkspace


def append_tool_results_and_compact(
    *,
    task: str,
    workspace: RunWorkspace,
    messages: list[ChatMessage],
    tool_results: list[ContentBlock],
    observations: list[Observation],
    plan: list[PlanItem],
    original_prior_context: str | None,
    iteration: int,
    approval_policy: ApprovalPolicy,
    system_prompt: str | None,
    append_system_prompt: str | None,
) -> list[ChatMessage]:
    messages.append(ChatMessage(role="user", content=tool_results))
    return compact_agent_message_history(
        task,
        workspace,
        messages,
        observations,
        plan,
        original_prior_context,
        iteration,
        approval_policy=approval_policy,
        system_prompt=system_prompt,
        append_system_prompt=append_system_prompt,
    )
