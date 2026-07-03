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
from .agent_completion import (
    auto_final_review_reason,
    build_active_background_process_details,
    build_checkpoint_failure_details,
    build_completion_blocker_details,
    build_completion_blockers,
    build_completion_warnings,
    build_denied_approval_details,
    build_failed_verification_checks,
    build_final_review_blocking_issue_details,
    build_final_review_changed_file_details,
    build_missing_plan_warning,
    build_pending_verification_checks,
    build_tool_error_details,
    build_unfinished_plan_warning,
    build_verification_checks,
    command_result_failed_suggested_check_labels,
    command_result_failed_suggested_check_result,
    command_result_matches_successful_suggested_check,
    command_result_suggested_check_commands,
    failed_suggested_check_labels,
    failed_suggested_check_results,
    final_review_has_active_completion_blocker,
    final_review_issue_is_verification_only,
    final_review_running_process_count,
    final_review_suggested_commands,
    format_completion_blocked_feedback,
    latest_observation_index,
    latest_successful_process_start_index,
    latest_successful_project_change_index,
    observation_runs_suggested_check_successfully,
    observations_show_multistep_coding_work,
    should_auto_run_final_review,
    successful_suggested_check_commands,
    successful_suggested_check_labels,
    suggested_check_label,
    suggested_check_statuses_after_latest_change,
)
from .agent_observation_utils import observation_failed, summarize
from .agent_runtime_utils import (
    append_session_event,
    compact_session_context,
    content_blocks_to_text,
    find_repeated_list_observation,
    normalize_assistant_content,
    summarize_command,
    to_jsonable,
    tool_error_observation,
)
from .session import summarize_session
from .types import (
    AgentLogger,
    ApprovalDeniedObservation,
    ApprovalHandler,
    ChatClient,
    ChatMessage,
    ContentBlock,
    FinalReviewAction,
    ListFilesObservation,
    Observation,
    PlanItem,
    RunCommandObservation,
    TaskStep,
    ToolErrorObservation,
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
    prior_context: str | None = None,
) -> AgentResult:
    # Start with an isolated run workspace for one task execution.
    current_workspace = workspace or create_run_workspace(base_dir)
    observations: list[Observation] = []
    steps: list[TaskStep] = []
    plan: list[PlanItem] = []
    messages = build_messages(task, current_workspace, prior_context=prior_context)
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

        parallel_tool_results = execute_parallel_tool_call_batch(
            current_workspace,
            tool_calls,
            observations,
            steps,
            iteration,
            command_timeout_ms,
            logger,
            execute=execute_action,
        )
        if parallel_tool_results is not None:
            messages.append(ChatMessage(role="user", content=parallel_tool_results))
            continue

        tool_results: list[ContentBlock] = []
        blocked_completion_feedback: str | None = None
        for block in tool_calls:
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
                step = start_task_step(current_workspace, steps, iteration, action, logger)
                log_action(logger, action)
                repeated_list = find_repeated_list_observation(action, observations)
                if repeated_list:
                    observation = ListFilesObservation(
                        kind="list_files",
                        path=repeated_list.path,
                        files=repeated_list.files,
                        total=repeated_list.total,
                        truncated=repeated_list.truncated,
                        message=(
                            f"Already listed {repeated_list.path}: {repeated_list.message} "
                            "Do not call list_files for this path again. Choose a useful tool call or answer directly."
                        ),
                    )
                else:
                    approval_request = build_approval_request(action)
                    if approval_request:
                        approval_request = attach_approval_preview(approval_request, action, observations)
                        append_session_event(
                            current_workspace.session_dir,
                            "approval_requested",
                            {"iteration": iteration, "step": step, "request": approval_request},
                        )
                        if logger:
                            logger("approval required", summarize_approval_request(approval_request))
                        decision = request_approval(approval_handler, approval_request)
                        append_session_event(
                            current_workspace.session_dir,
                            "approval_decision",
                            {"iteration": iteration, "step": step, "decision": decision},
                        )
                        if logger:
                            status = "approval approved" if decision.approved else "approval denied"
                            logger(status, summarize_approval_decision(approval_request, decision))
                        if not decision.approved:
                            observation = ApprovalDeniedObservation(
                                kind="approval_denied",
                                action_type=approval_request.action_type,
                                target=approval_request.target,
                                message=decision.message or "Action was denied by approval policy.",
                            )
                        else:
                            if not auto_checkpoint_attempted and should_auto_checkpoint_before_action(current_workspace, action):
                                auto_checkpoint_attempted = True
                                auto_checkpoint = create_auto_checkpoint_before_action(
                                    current_workspace,
                                    action,
                                    steps,
                                    iteration,
                                    command_timeout_ms,
                                    logger,
                                )
                                if auto_checkpoint is not None:
                                    observations.append(auto_checkpoint)
                            observation = execute_action_safely(current_workspace, action, command_timeout_ms, tool_name)
                    else:
                        if not auto_checkpoint_attempted and should_auto_checkpoint_before_action(current_workspace, action):
                            auto_checkpoint_attempted = True
                            auto_checkpoint = create_auto_checkpoint_before_action(
                                current_workspace,
                                action,
                                steps,
                                iteration,
                                command_timeout_ms,
                                logger,
                            )
                            if auto_checkpoint is not None:
                                observations.append(auto_checkpoint)
                        observation = execute_action_safely(current_workspace, action, command_timeout_ms, tool_name)
                if observation.kind == "update_plan":
                    plan = list(observation.plan)
                complete_task_step(current_workspace, step, observation, iteration, logger)
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
    if not success or iteration >= max_iterations:
        return None
    auto_run_final_review_if_needed(workspace, success, observations, iteration, command_timeout_ms, logger)
    blockers = build_completion_blockers(success, observations, plan)
    if not blockers:
        return None
    details = build_completion_blocker_details(success, observations)
    append_session_event(
        workspace.session_dir,
        "completion_blocked",
        {
            "iteration": iteration,
            "message": message,
            "blockers": blockers,
            "details": details,
        },
    )
    if logger:
        logger("completion blocked", summarize("; ".join(blockers), 500))
    return format_completion_blocked_feedback(blockers, details)


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
    auto_run_final_review_if_needed(workspace, success, observations, iterations, command_timeout_ms, logger)
    completion_blockers = build_completion_blockers(success, observations, plan)
    completion_ready = success and not completion_blockers
    result_status = session_result_status(success, completion_ready)
    completion_warnings = build_completion_warnings(success, observations, plan)
    verification_checks = build_verification_checks(success, observations)
    pending_verification_checks = build_pending_verification_checks(success, observations)
    failed_verification_checks = build_failed_verification_checks(success, observations)
    final_review_changed_files = build_final_review_changed_file_details(observations)
    append_session_event(
        workspace.session_dir,
        "result",
        {
            "success": success,
            "status": result_status,
            "message": message,
            "iterations": iterations,
            "observations": len(observations),
            "steps": len(steps),
            "plan": to_jsonable(plan),
            "completion_ready": completion_ready,
            "completion_blockers": completion_blockers,
            "completion_warnings": completion_warnings,
            "verification_checks": verification_checks,
            "pending_verification_checks": pending_verification_checks,
            "failed_verification_checks": failed_verification_checks,
            "final_review_changed_files": final_review_changed_files,
        },
    )
    session_summary = summarize_session(workspace.root, workspace.run_id)
    return AgentResult(
        success=success,
        message=message,
        run_dir=workspace.root,
        run_id=workspace.run_id,
        iterations=iterations,
        observations=observations,
        steps=steps,
        plan=plan,
        status=result_status,
        completion_ready=completion_ready,
        completion_blockers=completion_blockers,
        completion_warnings=completion_warnings,
        verification_checks=verification_checks,
        pending_verification_checks=pending_verification_checks,
        failed_verification_checks=failed_verification_checks,
        completion_blocked_count=session_summary.completion_blocked_count,
        latest_completion_blockers=session_summary.latest_completion_blockers,
        latest_completion_pending_verification_checks=session_summary.latest_completion_pending_verification_checks,
        latest_completion_failed_verification_checks=session_summary.latest_completion_failed_verification_checks,
        latest_completion_final_review_issues=session_summary.latest_completion_final_review_issues,
        latest_completion_final_review_changed_files=session_summary.latest_completion_final_review_changed_files,
        latest_completion_tool_errors=session_summary.latest_completion_tool_errors,
        latest_completion_checkpoint_failures=session_summary.latest_completion_checkpoint_failures,
        latest_completion_active_background_processes=session_summary.latest_completion_active_background_processes,
        latest_completion_denied_approvals=session_summary.latest_completion_denied_approvals,
        final_review_changed_files=session_summary.final_review_changed_files,
    )


def session_result_status(success: bool, completion_ready: bool) -> str:
    if not success:
        return "failed"
    if completion_ready:
        return "completed"
    return "blocked"


def auto_run_final_review_if_needed(
    workspace: RunWorkspace,
    success: bool,
    observations: list[Observation],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
) -> None:
    reason = auto_final_review_reason(success, observations)
    if reason is None:
        return

    if logger:
        logger("auto final_review", f"{reason}; running read-only final review.")
    action = FinalReviewAction(type="final_review")
    observation = execute_action_safely(workspace, action, command_timeout_ms, "final_review")
    observations.append(observation)
    result_payload = redact_jsonable_payload(to_jsonable(observation))
    append_session_event(
        workspace.session_dir,
        "tool_result",
        {
            "iteration": iteration,
            "id": "auto-final-review",
            "name": "final_review",
            "auto": True,
            "result": result_payload,
        },
    )
    if logger:
        logger("auto final_review result", observation_summary(observation))


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
