from __future__ import annotations

from dataclasses import replace

from .agent_multimodal import pending_image_tool_exchange, pending_image_tool_result_count
from .agent_runtime_utils import (
    AGENT_MESSAGE_COMPACT_CHAR_THRESHOLD,
    AGENT_COMPACT_CONTEXT_MAX_LENGTH,
    AGENT_COMPACT_OBSERVATION_LIMIT,
    append_session_event,
    compaction_threshold_reason,
    compact_session_context,
    message_history_char_count,
)
from .prompt_observations import format_observations
from .types import ChatMessage, DelegateTaskAction, Observation
from .workspace import format_project_skill_catalog, read_project_instructions, read_workspace_snapshot
from .workspace_core import RunWorkspace


DELEGATE_SYSTEM_PROMPT = """You are a read-only repository exploration subagent.
Investigate only the delegated task. Use the available tools to gather concrete evidence from the project.
You cannot edit files, run shell commands, ask the user, or delegate another task.
Return a concise report with relevant paths, symbols, line numbers, risks, and uncertainties. Do not claim changes were made.
Answer directly when the investigation is complete, or call finish with the report."""

CODE_DELEGATE_SYSTEM_PROMPT = """You are a focused coding subagent working in the user's active project.
Complete only the delegated implementation task and obey all project instructions. Inspect relevant code before editing.
You may use coding tools, but every side effect remains subject to the parent agent's approval policy and workspace safety rules.
You cannot ask the user, update the parent plan, or delegate another task. Do not broaden scope beyond the delegated task.
Verify your changes with focused checks when possible, then return a concise report of changed files, checks, and remaining risks.
Answer directly when complete, or call finish with the report."""


DELEGATE_MESSAGE_COMPACT_THRESHOLD = 12
DELEGATE_MESSAGE_COMPACT_CHAR_THRESHOLD = AGENT_MESSAGE_COMPACT_CHAR_THRESHOLD


def build_delegate_messages(
    workspace: RunWorkspace,
    action: DelegateTaskAction,
    profile_prompt: str | None = None,
) -> list[ChatMessage]:
    instructions = read_project_instructions(workspace)
    snapshot = read_workspace_snapshot(workspace)
    skill_catalog = format_project_skill_catalog(workspace)
    parts = [f"Delegated task:\n{action.task}"]
    if action.context:
        parts.append(f"Focused context:\n{action.context}")
    if instructions:
        parts.append(f"Project instructions:\n{instructions}")
    if skill_catalog:
        parts.append(skill_catalog)
    parts.append(f"Workspace snapshot:\n{snapshot}")
    system_prompt = CODE_DELEGATE_SYSTEM_PROMPT if action.mode == "code" else DELEGATE_SYSTEM_PROMPT
    if profile_prompt:
        system_prompt = f"{system_prompt}\n\nProject agent profile instructions:\n{profile_prompt}"
    return [
        ChatMessage(
            role="system",
            content=system_prompt,
        ),
        ChatMessage(role="user", content="\n\n".join(parts)),
    ]


def compact_delegate_message_history(
    workspace: RunWorkspace,
    action: DelegateTaskAction,
    messages: list[ChatMessage],
    observations: list[Observation],
    *,
    parent_iteration: int,
    child_iteration: int,
    subagent_id: str,
    profile_prompt: str | None = None,
    threshold: int = DELEGATE_MESSAGE_COMPACT_THRESHOLD,
    char_threshold: int = DELEGATE_MESSAGE_COMPACT_CHAR_THRESHOLD,
    observation_limit: int = AGENT_COMPACT_OBSERVATION_LIMIT,
    max_context_length: int = AGENT_COMPACT_CONTEXT_MAX_LENGTH,
    force: bool = False,
    reason: str | None = None,
) -> list[ChatMessage]:
    previous_chars = message_history_char_count(messages)
    message_threshold_reached = len(messages) > threshold
    char_threshold_reached = previous_chars > char_threshold
    if not force and not message_threshold_reached and not char_threshold_reached:
        return messages

    context = build_compacted_delegate_context(
        action,
        observations,
        observation_limit=observation_limit,
        max_context_length=max_context_length,
    )
    compacted_messages = build_delegate_messages(
        workspace,
        replace(action, context=context),
        profile_prompt=profile_prompt,
    )
    pending_image_exchange = pending_image_tool_exchange(messages)
    compacted_messages.extend(pending_image_exchange)
    new_chars = message_history_char_count(compacted_messages)
    if compacted_messages == messages or ((force or char_threshold_reached) and new_chars >= previous_chars):
        return messages
    resolved_reason = reason or compaction_threshold_reason(message_threshold_reached, char_threshold_reached)
    append_session_event(
        workspace.session_dir,
        "subagent_context_compacted",
        {
            "subagent_id": subagent_id,
            "parent_iteration": parent_iteration,
            "iteration": child_iteration,
            "mode": action.mode,
            "agent": action.agent,
            "previous_messages": len(messages),
            "new_messages": len(compacted_messages),
            "previous_chars": previous_chars,
            "new_chars": new_chars,
            "observations": len(observations),
            "retained_observations": min(len(observations), observation_limit),
            "retained_image_tool_results": pending_image_tool_result_count(messages),
            "reason": resolved_reason,
        },
    )
    return compacted_messages


def recover_delegate_context_limit(
    workspace: RunWorkspace,
    action: DelegateTaskAction,
    messages: list[ChatMessage],
    observations: list[Observation],
    *,
    parent_iteration: int,
    child_iteration: int,
    subagent_id: str,
    profile_prompt: str | None = None,
) -> bool:
    compacted = compact_delegate_message_history(
        workspace,
        action,
        messages,
        observations,
        parent_iteration=parent_iteration,
        child_iteration=child_iteration,
        subagent_id=subagent_id,
        profile_prompt=profile_prompt,
        force=True,
        reason="context_limit_error",
    )
    if compacted is messages:
        return False
    messages[:] = compacted
    return True


def build_compacted_delegate_context(
    action: DelegateTaskAction,
    observations: list[Observation],
    *,
    observation_limit: int = AGENT_COMPACT_OBSERVATION_LIMIT,
    max_context_length: int = AGENT_COMPACT_CONTEXT_MAX_LENGTH,
) -> str:
    recent_observations = observations[-observation_limit:]
    sections = [
        "Compacted delegated-task context:",
        f"Total subagent observations so far: {len(observations)}.",
        f"Recent subagent observations retained: {len(recent_observations)}.",
    ]
    if action.context:
        compacted_focus = compact_session_context(action.context)
        if compacted_focus:
            sections.extend(["Original delegated context:", compacted_focus])
    sections.extend(
        [
            "Compacted subagent observations:",
            format_observations(recent_observations),
        ]
    )
    return compact_session_context("\n".join(sections), max_context_length) or ""
