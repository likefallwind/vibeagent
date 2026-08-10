from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from .agent_delegate_completion import clip_delegate_summary, delegate_completion_message, finish_delegate_task
from .agent_delegate_context import (
    CODE_DELEGATE_SYSTEM_PROMPT,
    DELEGATE_MESSAGE_COMPACT_THRESHOLD,
    DELEGATE_SYSTEM_PROMPT,
    build_compacted_delegate_context,
    build_delegate_messages,
    compact_delegate_message_history,
)
from .agent_delegate_hooks import DelegateLifecycleHooks
from .agent_delegate_loop import DelegateLoopContext, run_delegate_iterations
from .agent_delegate_profile import DelegateProfileRuntime, load_delegate_profile_runtime
from .agent_delegate_tools import (
    DELEGATE_TOOL_DEFINITIONS,
    code_delegate_initial_tool_names,
    delegate_tool_definitions,
    execute_delegate_tool_call,
)
from .agent_runtime_utils import append_session_event
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    ChatClient,
    DelegateTaskAction,
    DelegateTaskObservation,
    Observation,
    TaskStep,
)
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks
from .workspace_permissions import ProjectPermissions


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
    hooks: ProjectHooks = ProjectHooks(),
    permissions: ProjectPermissions = ProjectPermissions(),
    cancel_requested: Callable[[], bool] | None = None,
) -> DelegateTaskObservation:
    profile = load_delegate_profile_runtime(workspace, action)
    delegate_workspace = profile.workspace or workspace
    if profile.mode is not None:
        action = replace(action, mode=profile.mode)
    if profile.max_turns is not None:
        action = replace(action, max_iterations=profile.max_turns)
    profile_prompt = profile.prompt
    allowed_tool_names = profile.allowed_tool_names
    disallowed_tool_names = profile.disallowed_tool_names
    observations = parent_observations if action.mode == "code" and parent_observations is not None else []
    steps = parent_steps if action.mode == "code" and parent_steps is not None else []
    messages = build_delegate_messages(delegate_workspace, action, profile_prompt=profile_prompt)

    _record_delegate_start(
        delegate_workspace,
        action,
        parent_iteration,
        subagent_id,
        approval_policy,
        profile,
        logger,
    )
    policy_error = _delegate_policy_error(action, approval_policy, profile.error)
    if policy_error is not None:
        return finish_delegate_task(
            delegate_workspace,
            action,
            subagent_id,
            ok=False,
            summary="",
            iterations=0,
            tool_calls=[],
            message=policy_error,
            logger=logger,
        )

    lifecycle = DelegateLifecycleHooks(
        workspace=delegate_workspace,
        action=action,
        subagent_id=subagent_id,
        hooks=hooks,
        command_timeout_ms=command_timeout_ms,
        logger=logger,
        approval_handler=approval_handler,
        approval_policy=approval_policy,
        permissions=permissions,
    )
    lifecycle.start(messages)

    active_tool_names = (
        code_delegate_initial_tool_names(
            approval_policy,
            allowed_tool_names,
            disallowed_tool_names,
            profile.enabled_tool_names,
        )
        if action.mode == "code"
        else set()
    )
    return run_delegate_iterations(
        DelegateLoopContext(
            workspace=delegate_workspace,
            action=action,
            client=client,
            messages=messages,
            observations=observations,
            steps=steps,
            parent_iteration=parent_iteration,
            subagent_id=subagent_id,
            lifecycle=lifecycle,
            profile_prompt=profile_prompt,
            allowed_tool_names=allowed_tool_names,
            disallowed_tool_names=disallowed_tool_names,
            active_tool_names=active_tool_names,
            delegate_observation_start=len(observations),
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
            command_timeout_ms=command_timeout_ms,
            logger=logger,
            approval_handler=approval_handler,
            approval_policy=approval_policy,
            hooks=hooks,
            permissions=permissions,
            cancel_requested=cancel_requested,
        )
    )


def _delegate_policy_error(
    action: DelegateTaskAction,
    approval_policy: ApprovalPolicy,
    profile_error: str | None,
) -> str | None:
    if profile_error is not None:
        return f"Project agent profile could not be loaded: {profile_error}"
    if action.run_in_background and action.mode != "explore":
        return "Background task delegation only supports explore mode, including project agent profiles."
    if action.mode == "code" and approval_policy == "plan":
        return "Code delegation is unavailable while Plan mode is active."
    return None


def _record_delegate_start(
    workspace: RunWorkspace,
    action: DelegateTaskAction,
    parent_iteration: int,
    subagent_id: str,
    approval_policy: ApprovalPolicy,
    profile: DelegateProfileRuntime,
    logger: AgentLogger | None,
) -> None:
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
            "profile_skills": list(profile.skills),
            "profile_disallowed_tools": sorted(profile.disallowed_tool_names),
            "profile_memory_scope": profile.memory_scope,
            "approval_policy": approval_policy,
        },
    )
    if logger:
        logger(f"{action.mode} subagent started", action.task)
