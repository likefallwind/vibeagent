from __future__ import annotations

from pathlib import Path
import time
from typing import Any

from .actions import ActionParseError, execute_action, parse_tool_action
from .agent_model import complete_with_retries
from .agent_model_turn import handle_no_tool_call_response, record_model_turn
from .agent_multimodal import build_tool_result_block, strip_consumed_tool_images
from .agent_result import AgentResult
from .redaction import redact_jsonable_payload
from .agent_run_setup import prepare_agent_run
from .agent_special_tools import execute_special_tool_action
from .agent_execution_support import (
    create_auto_checkpoint_before_action as _shared_create_auto_checkpoint_before_action,
    execute_action_safely as _shared_execute_action_safely,
    should_auto_checkpoint_before_action as _shared_should_auto_checkpoint_before_action,
)
from .agent_approval import (
    build_approval_request,
    request_approval,
    summarize_approval_decision,
    summarize_approval_request,
)
from .agent_approval_preview import (
    APPROVAL_WITHOUT_PREVIEW_ACTION_TYPES,
    PREVIEW_KIND_BY_ACTION_TYPE,
    approval_preview_key,
    approval_preview_summary,
    attach_approval_preview,
    summarize_preview_observation,
)
from .agent_parallel_safety import PARALLEL_SAFE_TOOL_NAMES, is_parallel_safe_action
from .agent_parallel_execution import execute_parallel_tool_call_batch
from .agent_steps import observation_summary
from .agent_tool_execution import execute_parsed_tool_action
from .agent_tool_registry import (
    agent_tool_definitions,
    activate_tools_for_run,
    activate_tools_from_observations,
    prepare_action_for_policy,
)
from .agent_run_completion import (
    auto_run_final_review_if_needed as _auto_run_final_review_if_needed,
    completion_blocked_feedback_if_needed as _completion_blocked_feedback_if_needed,
    finish_agent_run as _finish_agent_run,
    session_result_status as _session_result_status,
)
from .agent_observation_utils import observation_failed, summarize
from .agent_runtime_utils import (
    append_session_event,
    compact_agent_message_history,
    summarize_command,
    to_jsonable,
    tool_error_observation,
)
from .session import summarize_session
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    AskUserAction,
    ChatClient,
    ChatMessage,
    ContentBlock,
    DelegateTaskAction,
    Observation,
    PlanItem,
    RunCommandObservation,
    TaskStep,
    UserInputHandler,
)
from .workspace_core import RunWorkspace
from .workspace_permissions import ProjectPermissions


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
    approval_policy: ApprovalPolicy = "ask",
    task_metadata: dict[str, object] | None = None,
    trust_project_permissions: bool = False,
    permission_overrides: ProjectPermissions | None = None,
    mcp_config_paths: tuple[Path, ...] = (),
    strict_mcp_config: bool = False,
    system_prompt: str | None = None,
    append_system_prompt: str | None = None,
) -> AgentResult:
    observations: list[Observation] = []
    steps: list[TaskStep] = []
    plan: list[PlanItem] = []
    setup = prepare_agent_run(
        task,
        base_dir=base_dir,
        workspace=workspace,
        prior_context=prior_context,
        approval_policy=approval_policy,
        task_metadata=task_metadata,
        trust_project_permissions=trust_project_permissions,
        permission_overrides=permission_overrides,
        mcp_config_paths=mcp_config_paths,
        strict_mcp_config=strict_mcp_config,
        system_prompt=system_prompt,
        append_system_prompt=append_system_prompt,
    )
    current_workspace = setup.workspace
    messages = setup.messages
    active_tool_names = setup.active_tool_names
    project_hooks = setup.project_hooks
    project_permissions = setup.project_permissions
    original_prior_context = prior_context
    auto_checkpoint_attempted = False

    for iteration in range(1, max_iterations + 1):
        # Tool loop: provider-neutral tool_call blocks -> local execution -> tool_result blocks.
        if logger:
            logger("thinking", f"iteration {iteration}/{max_iterations}")

        response, model_error_message = complete_with_retries(
            client,
            messages,
            tools=agent_tool_definitions(active_tool_names, approval_policy),
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
        strip_consumed_tool_images(messages)
        model_turn = record_model_turn(current_workspace, messages, response, iteration)
        assistant_content = model_turn.assistant_content
        tool_calls = model_turn.tool_calls
        if not tool_calls:
            no_tool_result = handle_no_tool_call_response(
                current_workspace,
                messages,
                assistant_content,
                iteration=iteration,
                max_iterations=max_iterations,
                observations=observations,
                steps=steps,
                plan=plan,
                command_timeout_ms=command_timeout_ms,
                logger=logger,
                completion_blocked_feedback_if_needed_func=completion_blocked_feedback_if_needed,
                finish_agent_run_func=finish_agent_run,
            )
            if no_tool_result.should_continue:
                continue
            return no_tool_result.result

        activate_tools_for_run(
            current_workspace,
            active_tool_names,
            [str(block.get("name") or "") for block in tool_calls],
            iteration,
            source="model_call",
            approval_policy=approval_policy,
        )
        observation_start = len(observations)
        parallel_batch_result = (
            None
            if project_hooks.enabled or project_permissions.enabled
            else execute_parallel_tool_call_batch(
                current_workspace,
                tool_calls,
                observations,
                steps,
                iteration,
                command_timeout_ms,
                logger,
                execute=execute_action,
                approval_policy=approval_policy,
            )
        )
        tool_results: list[ContentBlock] = []
        handled_tool_calls = 0
        if parallel_batch_result is not None:
            tool_results.extend(parallel_batch_result.tool_results)
            handled_tool_calls = parallel_batch_result.handled_count
            activate_tools_from_observations(
                current_workspace,
                active_tool_names,
                observations[observation_start:],
                iteration,
                approval_policy,
            )
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
                approval_policy=approval_policy,
                system_prompt=system_prompt,
                append_system_prompt=append_system_prompt,
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
            hook_results: tuple[object, ...] = ()
            additional_observations: tuple[Observation, ...] = ()

            try:
                action = prepare_action_for_policy(parse_tool_action(tool_name, tool_input), approval_policy)
                if isinstance(action, (AskUserAction, DelegateTaskAction)):
                    wrapped = execute_special_tool_action(
                        current_workspace,
                        action,
                        client,
                        steps=steps,
                        observations=observations,
                        iteration=iteration,
                        tool_name=tool_name,
                        max_output_tokens=max_output_tokens,
                        model_retries=model_retries,
                        model_retry_delay_ms=model_retry_delay_ms,
                        model_timeout_ms=model_timeout_ms,
                        command_timeout_ms=command_timeout_ms,
                        logger=logger,
                        approval_handler=approval_handler,
                        approval_policy=approval_policy,
                        user_input_handler=user_input_handler,
                        hooks=project_hooks,
                        permissions=project_permissions,
                        execute_action_safely_func=execute_action_safely,
                    )
                    observation = wrapped.observation
                    hook_results = wrapped.hook_results
                    additional_observations = wrapped.additional_observations
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
                        approval_policy,
                        project_hooks,
                        project_permissions,
                    )
                    observation = execution.observation
                    hook_results = execution.hook_results
                    additional_observations = execution.additional_observations
                    auto_checkpoint_attempted = execution.auto_checkpoint_attempted
                    if execution.auto_checkpoint is not None:
                        observations.append(execution.auto_checkpoint)
                if observation.kind == "update_plan":
                    plan = list(observation.plan)
            except ActionParseError as error:
                observation = tool_error_observation(tool_name, error)

            observations.append(observation)
            observations.extend(additional_observations)
            activate_tools_from_observations(
                current_workspace,
                active_tool_names,
                [observation],
                iteration,
                approval_policy,
            )
            result_payload = redact_jsonable_payload(to_jsonable(observation))
            if hook_results and isinstance(result_payload, dict):
                result_payload["hooks"] = redact_jsonable_payload(to_jsonable(hook_results))
            append_session_event(
                current_workspace.session_dir,
                "tool_result",
                {"iteration": iteration, "id": tool_id, "name": tool_name, "result": result_payload},
            )
            tool_results.append(build_tool_result_block(current_workspace, tool_id, observation, result_payload))

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
            approval_policy=approval_policy,
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
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
    return _shared_execute_action_safely(
        workspace,
        action,
        command_timeout_ms,
        tool_name,
        execute_action,
    )


def should_auto_checkpoint_before_action(workspace: RunWorkspace, action: object) -> bool:
    return _shared_should_auto_checkpoint_before_action(workspace, action)


def create_auto_checkpoint_before_action(
    workspace: RunWorkspace,
    action: object,
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
) -> Observation | None:
    return _shared_create_auto_checkpoint_before_action(
        workspace,
        action,
        steps,
        iteration,
        command_timeout_ms,
        logger,
        execute_action_safely,
    )
