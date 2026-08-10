from __future__ import annotations

from .agent_runtime_utils import CompactHookRunner, compact_agent_message_history
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
    compact_hook_runner: CompactHookRunner | None = None,
) -> list[ChatMessage]:
    messages.append(ChatMessage(role="user", content=tool_results))
    return compact_agent_context_if_needed(
        task=task,
        workspace=workspace,
        messages=messages,
        observations=observations,
        plan=plan,
        original_prior_context=original_prior_context,
        iteration=iteration,
        approval_policy=approval_policy,
        system_prompt=system_prompt,
        append_system_prompt=append_system_prompt,
        compact_hook_runner=compact_hook_runner,
    )


def compact_agent_context_if_needed(
    *,
    task: str,
    workspace: RunWorkspace,
    messages: list[ChatMessage],
    observations: list[Observation],
    plan: list[PlanItem],
    original_prior_context: str | None,
    iteration: int,
    approval_policy: ApprovalPolicy,
    system_prompt: str | None,
    append_system_prompt: str | None,
    compact_hook_runner: CompactHookRunner | None = None,
) -> list[ChatMessage]:
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
        compact_hook_runner=compact_hook_runner,
    )


def recover_agent_context_limit(
    *,
    task: str,
    workspace: RunWorkspace,
    messages: list[ChatMessage],
    observations: list[Observation],
    plan: list[PlanItem],
    original_prior_context: str | None,
    iteration: int,
    approval_policy: ApprovalPolicy,
    system_prompt: str | None,
    append_system_prompt: str | None,
    compact_hook_runner: CompactHookRunner | None = None,
) -> bool:
    compacted = compact_agent_message_history(
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
        force=True,
        reason="context_limit_error",
        compact_hook_runner=compact_hook_runner,
    )
    if compacted is messages:
        return False
    messages[:] = compacted
    return True
