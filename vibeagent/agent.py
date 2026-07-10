from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any

from .actions import AGENT_TOOL_DEFINITIONS, ActionParseError, execute_action, parse_tool_action
from .agent_model import complete_with_retries
from .agent_result import AgentResult
from .prompts import build_messages
from .redaction import redact_jsonable_payload
from .agent_action_logging import log_action
from .agent_auto_checkpoint import (
    create_auto_checkpoint_before_action as _create_auto_checkpoint_before_action,
    should_auto_checkpoint_before_action as _should_auto_checkpoint_before_action,
)
from .agent_approval import (
    build_approval_request,
    request_approval,
    summarize_approval_decision,
    summarize_approval_request,
)
from .agent_approval_preview import (
    PREVIEW_KIND_BY_ACTION_TYPE,
    approval_preview_key,
    approval_preview_summary,
    attach_approval_preview,
    summarize_preview_observation,
)
from .agent_parallel_safety import PARALLEL_SAFE_TOOL_NAMES, is_parallel_safe_action
from .agent_parallel_execution import execute_parallel_tool_call_batch
from .agent_steps import complete_task_step, observation_summary, start_task_step
from .agent_tool_execution import execute_parsed_tool_action
from .agent_user_input import execute_user_input_action
from .agent_run_completion import (
    auto_run_final_review_if_needed as _auto_run_final_review_if_needed,
    completion_blocked_feedback_if_needed as _completion_blocked_feedback_if_needed,
    finish_agent_run as _finish_agent_run,
    session_result_status as _session_result_status,
)
from .agent_observation_utils import observation_failed, summarize
from .agent_runtime_utils import (
    append_session_event,
    compact_session_context,
    compact_agent_message_history,
    content_blocks_to_text,
    normalize_assistant_content,
    summarize_command,
    to_jsonable,
    tool_error_observation,
)
from .session import summarize_session
from .types import (
    AgentLogger,
    ApprovalHandler,
    AskUserAction,
    ChatClient,
    ChatMessage,
    ContentBlock,
    Observation,
    PlanItem,
    RunCommandObservation,
    TaskStep,
    ToolErrorObservation,
    UserInputHandler,
)
from .workspace_core import RunWorkspace, create_run_workspace


def run_agent(
    task: str,
    client: ChatClient,
    base_dir: str | Path | None = None,
    max_iterations: int = 20,
    command_timeout_ms: int = 30_000,
    max_output_tokens: int = 4096,
    model_retries: int = 1,
    model_retry_delay_ms: int = 250,
    model_timeout_ms: int = 120_000,
    logger: AgentLogger | None = None,
    workspace: RunWorkspace | None = None,
    approval_handler: ApprovalHandler | None = None,
    user_input_handler: UserInputHandler | None = None,
    prior_context: str | None = None,
) -> AgentResult:
    # Start with an isolated run workspace for one task execution.
    current_workspace = workspace or create_run_workspace(base_dir)
    observations: list[Observation] = []
    steps: list[TaskStep] = []
    plan: list[PlanItem] = []
    messages = build_messages(task, current_workspace, prior_context=prior_context)
    original_prior_context = prior_context
    auto_checkpoint_attempted = False
    append_session_event(
        current_workspace.session_dir,
        "task",
        {"task": task, "prior_context": compact_session_context(prior_context) if prior_context else None},
    )

    for iteration in range(1, max_iterations + 1):
        # Tool loop: provider-neutral tool_call blocks -> local execution -> tool_result blocks.
        if logger:
            logger("thinking", f"iteration {iteration}/{max_iterations}")

        response, model_error_message = complete_with_retries(
            client,
            messages,
            tools=AGENT_TOOL_DEFINITIONS,
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
            iteration=iteration,
            session_dir=current_workspace.session_dir,
            logger=logger,
            sleep=time.sleep,
        )
        if response is None:
            return finish_agent_run(
                current_workspace,
                success=False,
                message=model_error_message or "Model request failed.",
                iterations=iteration,
                observations=observations,
                steps=steps,
                plan=plan,
                command_timeout_ms=command_timeout_ms,
                logger=logger,
            )
        assistant_content = normalize_assistant_content(response.content if hasattr(response, "content") else response)
        model_event: dict[str, Any] = {"iteration": iteration, "content": assistant_content}
        response_usage = response.usage if hasattr(response, "usage") else None
        if response_usage is not None:
            model_event["usage"] = to_jsonable(response_usage)
        append_session_event(current_workspace.session_dir, "model", model_event)
        messages.append(ChatMessage(role="assistant", content=assistant_content))

        tool_calls = [block for block in assistant_content if block.get("type") == "tool_call"]
        if not tool_calls:
            text = content_blocks_to_text(assistant_content).strip()
            if text:
                feedback = completion_blocked_feedback_if_needed(
                    current_workspace,
                    success=True,
                    message=text,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    observations=observations,
                    plan=plan,
                    command_timeout_ms=command_timeout_ms,
                    logger=logger,
                )
                if feedback is not None:
                    messages.append(ChatMessage(role="user", content=feedback))
                    continue
                if logger:
                    logger("finished", text)
                return finish_agent_run(
                    current_workspace,
                    success=True,
                    message=text,
                    iterations=iteration,
                    observations=observations,
                    steps=steps,
                    plan=plan,
                    command_timeout_ms=command_timeout_ms,
                    logger=logger,
                )
            return finish_agent_run(
                current_workspace,
                success=False,
                message="Model response did not include text or a tool call.",
                iterations=iteration,
                observations=observations,
                steps=steps,
                plan=plan,
                command_timeout_ms=command_timeout_ms,
                logger=logger,
            )

        parallel_batch_result = execute_parallel_tool_call_batch(
            current_workspace,
            tool_calls,
            observations,
            steps,
            iteration,
            command_timeout_ms,
            logger,
            execute=execute_action,
        )
        tool_results: list[ContentBlock] = []
        handled_tool_calls = 0
        if parallel_batch_result is not None:
            tool_results.extend(parallel_batch_result.tool_results)
            handled_tool_calls = parallel_batch_result.handled_count
        if handled_tool_calls == len(tool_calls):
            messages.append(ChatMessage(role="user", content=tool_results))
            messages = compact_agent_message_history(
                task,
                current_workspace,
                messages,
                observations,
                plan,
                original_prior_context,
                iteration,
            )
            continue

        blocked_completion_feedback: str | None = None
        for block in tool_calls[handled_tool_calls:]:
            tool_id = str(block.get("id") or "")
            tool_name = str(block.get("name") or "")
            tool_input = block.get("input") or {}
            append_session_event(
                current_workspace.session_dir,
                "tool_call",
                {"iteration": iteration, "id": tool_id, "name": tool_name, "input": tool_input},
            )

            try:
                action = parse_tool_action(tool_name, tool_input)
                if isinstance(action, AskUserAction):
                    observation = execute_user_input_action(
                        current_workspace,
                        action,
                        steps,
                        iteration,
                        logger,
                        user_input_handler,
                    )
                else:
                    execution = execute_parsed_tool_action(
                        current_workspace,
                        action,
                        observations,
                        steps,
                        iteration,
                        command_timeout_ms,
                        logger,
                        approval_handler,
                        tool_name,
                        auto_checkpoint_attempted,
                        execute_action_safely,
                        should_auto_checkpoint_before_action,
                        create_auto_checkpoint_before_action,
                    )
                    observation = execution.observation
                    auto_checkpoint_attempted = execution.auto_checkpoint_attempted
                    if execution.auto_checkpoint is not None:
                        observations.append(execution.auto_checkpoint)
                if observation.kind == "update_plan":
                    plan = list(observation.plan)
            except ActionParseError as error:
                observation = tool_error_observation(tool_name, error)

            observations.append(observation)
            result_payload = redact_jsonable_payload(to_jsonable(observation))
            append_session_event(
                current_workspace.session_dir,
                "tool_result",
                {"iteration": iteration, "id": tool_id, "name": tool_name, "result": result_payload},
            )
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_call_id": tool_id,
                    "content": json.dumps(result_payload, ensure_ascii=False),
                }
            )

            if observation.kind == "finish":
                blocked_completion_feedback = completion_blocked_feedback_if_needed(
                    current_workspace,
                    success=True,
                    message=observation.message,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    observations=observations,
                    plan=plan,
                    command_timeout_ms=command_timeout_ms,
                    logger=logger,
                )
                if blocked_completion_feedback is not None:
                    break
                if logger:
                    logger("finished", observation.message)
                return finish_agent_run(
                    current_workspace,
                    success=True,
                    message=observation.message,
                    iterations=iteration,
                    observations=observations,
                    steps=steps,
                    plan=plan,
                    command_timeout_ms=command_timeout_ms,
                    logger=logger,
                )

            if isinstance(observation, RunCommandObservation) and logger:
                ok = observation.result.exit_code == 0 and not observation.result.timed_out
                logger("observed success" if ok else "observed failure", summarize_command(observation.result))

        if blocked_completion_feedback is not None:
            messages.append(ChatMessage(role="user", content=tool_results))
            messages.append(ChatMessage(role="user", content=blocked_completion_feedback))
            continue

        messages.append(ChatMessage(role="user", content=tool_results))
        messages = compact_agent_message_history(
            task,
            current_workspace,
            messages,
            observations,
            plan,
            original_prior_context,
            iteration,
        )

    # Return failure only after exhausting max iterations without an explicit finish action.
    return finish_agent_run(
        current_workspace,
        success=False,
        message=f"Reached iteration limit ({max_iterations}) before finish.",
        iterations=max_iterations,
        observations=observations,
        steps=steps,
        plan=plan,
        command_timeout_ms=command_timeout_ms,
        logger=logger,
    )


def completion_blocked_feedback_if_needed(
    workspace: RunWorkspace,
    success: bool,
    message: str,
    iteration: int,
    max_iterations: int,
    observations: list[Observation],
    plan: list[PlanItem],
    command_timeout_ms: int,
    logger: AgentLogger | None,
) -> str | None:
    return _completion_blocked_feedback_if_needed(
        workspace,
        success,
        message,
        iteration,
        max_iterations,
        observations,
        plan,
        command_timeout_ms,
        logger,
        execute_action_safely,
    )


def finish_agent_run(
    workspace: RunWorkspace,
    success: bool,
    message: str,
    iterations: int,
    observations: list[Observation],
    steps: list[TaskStep],
    plan: list[PlanItem],
    command_timeout_ms: int,
    logger: AgentLogger | None,
) -> AgentResult:
    return _finish_agent_run(
        workspace,
        success,
        message,
        iterations,
        observations,
        steps,
        plan,
        command_timeout_ms,
        logger,
        execute_action_safely,
    )


def session_result_status(success: bool, completion_ready: bool) -> str:
    return _session_result_status(success, completion_ready)


def auto_run_final_review_if_needed(
    workspace: RunWorkspace,
    success: bool,
    observations: list[Observation],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
) -> None:
    return _auto_run_final_review_if_needed(
        workspace,
        success,
        observations,
        iteration,
        command_timeout_ms,
        logger,
        execute_action_safely,
    )


def execute_action_safely(
    workspace: RunWorkspace,
    action: object,
    command_timeout_ms: int,
    tool_name: str,
) -> Observation:
    try:
        return execute_action(workspace, action, command_timeout_ms)
    except Exception as error:
        return ToolErrorObservation(
            kind="tool_error",
            tool=tool_name or str(getattr(action, "type", "unknown")) or "unknown",
            message=f"Tool execution failed: {error}",
        )


def should_auto_checkpoint_before_action(workspace: RunWorkspace, action: object) -> bool:
    return _should_auto_checkpoint_before_action(workspace, action)


def create_auto_checkpoint_before_action(
    workspace: RunWorkspace,
    action: object,
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
) -> Observation | None:
    return _create_auto_checkpoint_before_action(
        workspace,
        action,
        steps,
        iteration,
        command_timeout_ms,
        logger,
        execute_action_safely,
    )
