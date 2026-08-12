from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import time

from .actions import ActionParseError, execute_action, parse_tool_action
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
from .agent_loop import AgentLoopRuntime, run_agent_loop
from .agent_model import complete_with_retries
from .model_streaming import AgentModelStreamHandler
from .agent_observation_utils import observation_failed
from .agent_profile_client import configure_agent_profile_client
from .agent_parallel_safety import PARALLEL_SAFE_TOOL_NAMES, is_parallel_safe_action
from .plugin_monitor_runtime import PluginMonitorRuntime
from .agent_result import AgentResult
from .agent_run_setup import prepare_agent_run
from .agent_runtime_utils import append_session_event, tool_error_observation
from .agent_steps import observation_summary
from .agent_tool_execution import execute_parsed_tool_action
from .agent_execution_support import (
    create_auto_checkpoint_before_action as _shared_create_auto_checkpoint_before_action,
    execute_action_safely as _shared_execute_action_safely,
    should_auto_checkpoint_before_action as _shared_should_auto_checkpoint_before_action,
)
from .agent_auto_checkpoint import (
    create_auto_checkpoint_for_prompt as _create_auto_checkpoint_for_prompt,
)
from .agent_run_completion import (
    auto_run_final_review_if_needed as _auto_run_final_review_if_needed,
    completion_blocked_feedback_if_needed as _completion_blocked_feedback_if_needed,
    finish_agent_run as _finish_agent_run,
    session_result_status as _session_result_status,
)
from .session import summarize_session
from .session_turn_lock import lock_existing_session_turn
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    ChatClient,
    ChatMessage,
    Observation,
    PlanItem,
    TaskStep,
    UserInputHandler,
)
from .workspace_core import RunWorkspace
from .dynamic_agent_profiles import DynamicAgentProfile
from .workspace_permissions import ProjectPermissions
from .peer_runtime import PeerSessionRuntime
from .deferred_tool_state import DeferredToolState
from .async_hook_runtime import close_session_async_hooks


@lock_existing_session_turn
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
    prior_messages: list[ChatMessage] | None = None,
    approval_policy: ApprovalPolicy = "ask",
    task_metadata: dict[str, object] | None = None,
    task_source_run_id: str | None = None,
    trust_project_permissions: bool = False,
    permission_overrides: ProjectPermissions | None = None,
    mcp_config_paths: tuple[Path, ...] = (),
    strict_mcp_config: bool = False,
    safe_mode: bool = False,
    system_prompt: str | None = None,
    append_system_prompt: str | None = None,
    append_subagent_system_prompt: str | None = None,
    peer_runtime: PeerSessionRuntime | None = None,
    agent: str | None = None,
    tool_names: frozenset[str] | None = None,
    workspace_observer: Callable[[RunWorkspace], None] | None = None,
    additional_directories: tuple[Path, ...] = (),
    dynamic_agent_profiles: tuple[DynamicAgentProfile, ...] = (),
    deferred_tool_state: DeferredToolState | None = None,
    defer_tool_calls: bool = False,
    close_async_hooks_on_finish: bool = False,
    setup_trigger: str | None = None,
    autocompact_tokens: int | None = None,
    model_stream_handler: AgentModelStreamHandler | None = None,
) -> AgentResult:
    setup = prepare_agent_run(
        task,
        base_dir=base_dir,
        workspace=workspace,
        prior_context=prior_context,
        prior_messages=prior_messages,
        approval_policy=approval_policy,
        task_metadata=task_metadata,
        task_source_run_id=task_source_run_id,
        trust_project_permissions=trust_project_permissions,
        permission_overrides=permission_overrides,
        mcp_config_paths=mcp_config_paths,
        strict_mcp_config=strict_mcp_config,
        safe_mode=safe_mode,
        system_prompt=system_prompt,
        append_system_prompt=append_system_prompt,
        append_subagent_system_prompt=append_subagent_system_prompt,
        agent=agent,
        tool_names=tool_names,
        additional_directories=additional_directories,
        dynamic_agent_profiles=dynamic_agent_profiles,
        autocompact_tokens=autocompact_tokens,
    )
    if workspace_observer is not None:
        workspace_observer(setup.workspace)
    if peer_runtime is not None:
        peer_runtime.update_workspace(setup.workspace, setup.approval_policy)
    profile_client = configure_agent_profile_client(
        client,
        model=setup.main_profile.model,
        effort=setup.main_profile.effort,
    )
    if model_stream_handler is not None and any(
        hook.event == "MessageDisplay" for hook in setup.project_hooks.hooks
    ):
        append_session_event(
            setup.workspace.session_dir,
            "model_streaming_disabled",
            {"reason": "message_display_hook"},
        )
        model_stream_handler = None
    plugin_monitors = PluginMonitorRuntime(setup.workspace)
    try:
        return run_agent_loop(
            setup.task,
            profile_client,
            setup,
            max_iterations=(
                min(max_iterations, setup.main_profile.max_turns)
                if setup.main_profile.max_turns is not None
                else max_iterations
            ),
            command_timeout_ms=command_timeout_ms,
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
            logger=logger,
            approval_handler=approval_handler,
            user_input_handler=user_input_handler,
            prior_context=prior_context,
            approval_policy=setup.approval_policy,
            system_prompt=system_prompt,
            append_system_prompt=setup.append_system_prompt,
            runtime=AgentLoopRuntime(
                complete_with_retries=complete_with_retries,
                execute_action=execute_action,
                execute_action_safely=execute_action_safely,
                completion_blocked_feedback_if_needed=completion_blocked_feedback_if_needed,
                finish_agent_run=finish_agent_run,
                should_auto_checkpoint_before_action=should_auto_checkpoint_before_action,
                create_auto_checkpoint_before_action=create_auto_checkpoint_before_action,
                create_auto_checkpoint_for_prompt=create_auto_checkpoint_for_prompt,
                sleep=time.sleep,
            ),
            peer_runtime=peer_runtime,
            plugin_monitor_runtime=plugin_monitors,
            deferred_tool_state=deferred_tool_state,
            defer_tool_calls=defer_tool_calls,
            setup_trigger=setup_trigger,
            model_stream_handler=model_stream_handler,
        )
    finally:
        if close_async_hooks_on_finish:
            close_session_async_hooks(setup.workspace)
        plugin_monitors.close()


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
    *,
    stop_reason: str | None = None,
    deferred_tool_use: dict[str, object] | None = None,
    is_error: bool = False,
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
        stop_reason=stop_reason,
        deferred_tool_use=deferred_tool_use,
        is_error=is_error,
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


def create_auto_checkpoint_for_prompt(
    workspace: RunWorkspace,
    task: str,
    steps: list[TaskStep],
    command_timeout_ms: int,
    logger: AgentLogger | None,
) -> Observation | None:
    return _create_auto_checkpoint_for_prompt(
        workspace,
        task,
        steps,
        command_timeout_ms,
        logger,
        execute_action_safely,
    )
