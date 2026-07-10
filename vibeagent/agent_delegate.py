from __future__ import annotations

import json

from .actions import ActionParseError, execute_action, parse_tool_action
from .agent_model import complete_with_retries
from .agent_observation_utils import observation_failed
from .agent_parallel_safety import PARALLEL_SAFE_TOOL_NAMES, is_parallel_safe_action
from .agent_runtime_utils import (
    append_session_event,
    content_blocks_to_text,
    normalize_assistant_content,
    to_jsonable,
    tool_error_observation,
)
from .tool_definitions import AGENT_TOOL_DEFINITIONS
from .types import (
    AgentLogger,
    ChatClient,
    ChatMessage,
    ContentBlock,
    DelegateTaskAction,
    DelegateTaskObservation,
    FinishAction,
    ToolErrorObservation,
)
from .workspace import format_project_skill_catalog, read_project_instructions, read_workspace_snapshot
from .workspace_core import RunWorkspace


DELEGATE_TOOL_NAMES = {
    name
    for name in PARALLEL_SAFE_TOOL_NAMES
    if not name.startswith("check_") and name not in {"final_review"}
}
DELEGATE_TOOL_DEFINITIONS = [
    tool
    for tool in AGENT_TOOL_DEFINITIONS
    if tool["name"] in DELEGATE_TOOL_NAMES or tool["name"] == "finish"
]

DELEGATE_SYSTEM_PROMPT = """You are a read-only repository exploration subagent.
Investigate only the delegated task. Use the available tools to gather concrete evidence from the project.
You cannot edit files, run shell commands, ask the user, or delegate another task.
Return a concise report with relevant paths, symbols, line numbers, risks, and uncertainties. Do not claim changes were made.
Answer directly when the investigation is complete, or call finish with the report."""


def execute_delegate_task_action(
    workspace: RunWorkspace,
    action: DelegateTaskAction,
    client: ChatClient,
    *,
    parent_iteration: int,
    subagent_id: str,
    max_output_tokens: int,
    model_retries: int,
    model_retry_delay_ms: int,
    model_timeout_ms: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
) -> DelegateTaskObservation:
    messages = build_delegate_messages(workspace, action)
    tool_calls_used: list[str] = []
    append_session_event(
        workspace.session_dir,
        "subagent_started",
        {
            "iteration": parent_iteration,
            "subagent_id": subagent_id,
            "task": action.task,
            "context": action.context,
            "max_iterations": action.max_iterations,
        },
    )
    if logger:
        logger("subagent started", action.task)

    for child_iteration in range(1, action.max_iterations + 1):
        response, error_message = complete_with_retries(
            client,
            messages,
            tools=DELEGATE_TOOL_DEFINITIONS,
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
            iteration=child_iteration,
            session_dir=workspace.session_dir,
            logger=logger,
            error_event_type="subagent_model_error",
            error_event_extra={"subagent_id": subagent_id, "parent_iteration": parent_iteration},
        )
        if response is None:
            return finish_delegate_task(
                workspace,
                action,
                subagent_id,
                ok=False,
                summary="",
                iterations=child_iteration,
                tool_calls=tool_calls_used,
                message=error_message or "Subagent model request failed.",
                logger=logger,
            )

        assistant_content = normalize_assistant_content(response.content if hasattr(response, "content") else response)
        model_payload = {
            "subagent_id": subagent_id,
            "parent_iteration": parent_iteration,
            "iteration": child_iteration,
            "content": assistant_content,
        }
        usage = getattr(response, "usage", None)
        if usage is not None:
            model_payload["usage"] = to_jsonable(usage)
        append_session_event(workspace.session_dir, "subagent_model", model_payload)
        messages.append(ChatMessage(role="assistant", content=assistant_content))

        tool_calls = [block for block in assistant_content if block.get("type") == "tool_call"]
        if not tool_calls:
            summary = content_blocks_to_text(assistant_content).strip()
            if summary:
                return finish_delegate_task(
                    workspace,
                    action,
                    subagent_id,
                    ok=True,
                    summary=clip_delegate_summary(summary),
                    iterations=child_iteration,
                    tool_calls=tool_calls_used,
                    message="Subagent completed the investigation.",
                    logger=logger,
                )
            return finish_delegate_task(
                workspace,
                action,
                subagent_id,
                ok=False,
                summary="",
                iterations=child_iteration,
                tool_calls=tool_calls_used,
                message="Subagent response did not include text or a tool call.",
                logger=logger,
            )

        tool_results: list[ContentBlock] = []
        for block in tool_calls:
            tool_id = str(block.get("id") or "")
            tool_name = str(block.get("name") or "")
            tool_input = block.get("input") or {}
            tool_calls_used.append(tool_name)
            append_session_event(
                workspace.session_dir,
                "subagent_tool_call",
                {
                    "subagent_id": subagent_id,
                    "parent_iteration": parent_iteration,
                    "iteration": child_iteration,
                    "id": tool_id,
                    "name": tool_name,
                    "input": tool_input,
                },
            )
            try:
                parsed = parse_tool_action(tool_name, tool_input)
                if isinstance(parsed, FinishAction):
                    summary = clip_delegate_summary(parsed.message)
                    return finish_delegate_task(
                        workspace,
                        action,
                        subagent_id,
                        ok=bool(summary),
                        summary=summary,
                        iterations=child_iteration,
                        tool_calls=tool_calls_used,
                        message=(
                            "Subagent completed the investigation."
                            if summary
                            else "Subagent finish call did not include a report."
                        ),
                        logger=logger,
                        tool_event={
                            "parent_iteration": parent_iteration,
                            "iteration": child_iteration,
                            "id": tool_id,
                            "name": tool_name,
                        },
                    )
                if tool_name not in DELEGATE_TOOL_NAMES or not is_parallel_safe_action(parsed):
                    observation = ToolErrorObservation(
                        kind="tool_error",
                        tool=tool_name or "unknown",
                        message="Subagent tool is not allowed in read-only delegation mode.",
                    )
                else:
                    observation = execute_action(workspace, parsed, command_timeout_ms)
            except ActionParseError as error:
                observation = tool_error_observation(tool_name, error)
            except Exception as error:
                observation = ToolErrorObservation(
                    kind="tool_error",
                    tool=tool_name or "unknown",
                    message=f"Subagent tool execution failed: {error}",
                )

            result_payload = to_jsonable(observation)
            append_session_event(
                workspace.session_dir,
                "subagent_tool_result",
                {
                    "subagent_id": subagent_id,
                    "parent_iteration": parent_iteration,
                    "iteration": child_iteration,
                    "id": tool_id,
                    "name": tool_name,
                    "failed": observation_failed(observation),
                    "result": result_payload,
                },
            )
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_call_id": tool_id,
                    "content": json.dumps(result_payload, ensure_ascii=False),
                }
            )
        messages.append(ChatMessage(role="user", content=tool_results))

    return finish_delegate_task(
        workspace,
        action,
        subagent_id,
        ok=False,
        summary="",
        iterations=action.max_iterations,
        tool_calls=tool_calls_used,
        message=f"Subagent reached iteration limit ({action.max_iterations}) before reporting findings.",
        logger=logger,
    )


def build_delegate_messages(workspace: RunWorkspace, action: DelegateTaskAction) -> list[ChatMessage]:
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
    return [
        ChatMessage(role="system", content=DELEGATE_SYSTEM_PROMPT),
        ChatMessage(role="user", content="\n\n".join(parts)),
    ]


def clip_delegate_summary(value: str, max_chars: int = 12_000) -> str:
    value = value.strip()
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}\n[delegate summary truncated]"


def finish_delegate_task(
    workspace: RunWorkspace,
    action: DelegateTaskAction,
    subagent_id: str,
    *,
    ok: bool,
    summary: str,
    iterations: int,
    tool_calls: list[str],
    message: str,
    logger: AgentLogger | None,
    tool_event: dict[str, object] | None = None,
) -> DelegateTaskObservation:
    observation = DelegateTaskObservation(
        kind="delegate_task",
        ok=ok,
        task=action.task,
        summary=summary,
        iterations=iterations,
        tool_calls=list(tool_calls),
        message=message,
    )
    if tool_event is not None:
        append_session_event(
            workspace.session_dir,
            "subagent_tool_result",
            {
                "subagent_id": subagent_id,
                **tool_event,
                "failed": not ok,
                "result": observation,
            },
        )
    append_session_event(
        workspace.session_dir,
        "subagent_completed",
        {"subagent_id": subagent_id, "result": observation},
    )
    if logger:
        logger("subagent completed" if ok else "subagent failed", message)
    return observation
