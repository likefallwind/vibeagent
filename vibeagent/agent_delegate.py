from __future__ import annotations

from dataclasses import replace
import json

from .agent_delegate_tools import (
    DELEGATE_TOOL_DEFINITIONS,
    code_delegate_initial_tool_names,
    delegate_tool_definitions,
    execute_delegate_tool_call,
)
from .agent_model import complete_with_retries
from .agent_observation_utils import observation_failed
from .agent_runtime_utils import (
    append_session_event,
    content_blocks_to_text,
    normalize_assistant_content,
    to_jsonable,
)
from .redaction import redact_jsonable_payload
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    ChatClient,
    ChatMessage,
    ContentBlock,
    DelegateTaskAction,
    DelegateTaskObservation,
    Observation,
    TaskStep,
)
from .workspace import format_project_skill_catalog, read_project_instructions, read_workspace_snapshot
from .workspace_agents import read_project_agent
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
    approval_handler: ApprovalHandler | None = None,
    approval_policy: ApprovalPolicy = "ask",
    parent_observations: list[Observation] | None = None,
    parent_steps: list[TaskStep] | None = None,
) -> DelegateTaskObservation:
    profile: dict[str, object] | None = None
    profile_error: str | None = None
    if action.agent:
        try:
            profile = read_project_agent(workspace, action.agent)
            action = replace(action, mode=str(profile["mode"]))
        except ValueError as error:
            profile_error = str(error)
    profile_prompt = str(profile["prompt"]) if profile is not None else None
    profile_tools = profile.get("tools") if profile is not None else None
    allowed_tool_names = (
        frozenset(str(name) for name in profile_tools) | {"finish"}
        if isinstance(profile_tools, list)
        else None
    )
    messages = build_delegate_messages(workspace, action, profile_prompt=profile_prompt)
    tool_calls_used: list[str] = []
    observations = parent_observations if action.mode == "code" and parent_observations is not None else []
    steps = parent_steps if action.mode == "code" and parent_steps is not None else []
    auto_checkpoint_attempted = False
    active_tool_names = (
        code_delegate_initial_tool_names(approval_policy, allowed_tool_names)
        if action.mode == "code"
        else set()
    )
    append_session_event(
        workspace.session_dir,
        "subagent_started",
        {
            "iteration": parent_iteration,
            "subagent_id": subagent_id,
            "task": action.task,
            "context": action.context,
            "max_iterations": action.max_iterations,
            "mode": action.mode,
            "agent": action.agent,
            "approval_policy": approval_policy,
        },
    )
    if logger:
        logger(f"{action.mode} subagent started", action.task)

    if profile_error is not None:
        return finish_delegate_task(
            workspace,
            action,
            subagent_id,
            ok=False,
            summary="",
            iterations=0,
            tool_calls=tool_calls_used,
            message=f"Project agent profile could not be loaded: {profile_error}",
            logger=logger,
        )

    if action.mode == "code" and approval_policy == "plan":
        return finish_delegate_task(
            workspace,
            action,
            subagent_id,
            ok=False,
            summary="",
            iterations=0,
            tool_calls=tool_calls_used,
            message="Code delegation is unavailable while Plan mode is active.",
            logger=logger,
        )

    for child_iteration in range(1, action.max_iterations + 1):
        response, error_message = complete_with_retries(
            client,
            messages,
            tools=delegate_tool_definitions(
                action.mode,
                active_tool_names,
                approval_policy,
                allowed_tool_names,
            ),
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
                    message=delegate_completion_message(action),
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
            execution = execute_delegate_tool_call(
                workspace,
                mode=action.mode,
                tool_name=tool_name,
                tool_input=tool_input,
                active_tool_names=active_tool_names,
                observations=observations,
                steps=steps,
                iteration=child_iteration,
                command_timeout_ms=command_timeout_ms,
                logger=logger,
                approval_handler=approval_handler,
                approval_policy=approval_policy,
                auto_checkpoint_attempted=auto_checkpoint_attempted,
                allowed_tool_names=allowed_tool_names,
            )
            auto_checkpoint_attempted = execution.auto_checkpoint_attempted
            if execution.finish_action is not None:
                summary = clip_delegate_summary(execution.finish_action.message)
                return finish_delegate_task(
                    workspace,
                    action,
                    subagent_id,
                    ok=bool(summary),
                    summary=summary,
                    iterations=child_iteration,
                    tool_calls=tool_calls_used,
                    message=(
                        delegate_completion_message(action)
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
            observation = execution.observation
            if observation is None:
                continue
            result_payload = redact_jsonable_payload(to_jsonable(observation))
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
        message=f"Subagent reached iteration limit ({action.max_iterations}) before completing the delegated task.",
        logger=logger,
    )


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


def clip_delegate_summary(value: str, max_chars: int = 12_000) -> str:
    value = value.strip()
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}\n[delegate summary truncated]"


def delegate_completion_message(action: DelegateTaskAction) -> str:
    if action.mode == "code":
        return "Subagent completed the coding task."
    return "Subagent completed the investigation."


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
        mode=action.mode,
        agent=action.agent,
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
