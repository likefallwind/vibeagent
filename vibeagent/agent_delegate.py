from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from .auto_mode import AutoModeRuntime
from .agent_delegate_completion import clip_delegate_summary, delegate_completion_message, finish_delegate_task
from .agent_delegate_context import (
    CODE_DELEGATE_SYSTEM_PROMPT,
    DELEGATE_MESSAGE_COMPACT_THRESHOLD,
    DELEGATE_SYSTEM_PROMPT,
    append_resumed_subagent_prompt,
    build_compacted_delegate_context,
    build_delegate_messages,
    compact_delegate_message_history,
)
from .agent_delegate_hooks import DelegateLifecycleHooks
from .agent_hook_prompt import HookModelRuntime
from .agent_model import complete_with_retries
from .agent_delegate_inbox import DelegateInbox
from .agent_delegate_loop import DelegateLoopContext, run_delegate_iterations
from .agent_delegate_profile import (
    DelegateProfileRuntime,
    load_delegate_profile_runtime,
    resolve_profile_permissions,
)
from .agent_delegate_tools import (
    DELEGATE_TOOL_DEFINITIONS,
    code_delegate_initial_tool_names,
    delegate_tool_definitions,
    execute_delegate_tool_call,
)
from .agent_profile_client import configure_agent_profile_client
from .permission_tool_visibility import globally_denied_tool_names
from .agent_runtime_utils import append_session_event
from .agent_team_runtime import TEAM_COORDINATION_TOOL_NAMES, teammate_spawn_error
from .nested_delegate_runtime import NestedDelegateRuntime
from .subagent_transcripts import (
    SubagentTranscript,
    checkpoint_subagent_transcript,
    complete_subagent_transcript,
    create_subagent_transcript,
    resume_subagent_transcript,
)
from .subagent_worktrees import (
    SubagentWorktreeError,
    SubagentWorktreeOutcome,
    SubagentWorktreeRuntime,
    finalize_subagent_worktree,
    prepare_subagent_worktree,
)
from .worktree_hooks import WorktreeHookContext
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    ChatClient,
    ChatMessage,
    DelegateTaskAction,
    DelegateTaskObservation,
    Observation,
    TaskStep,
)
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks
from .workspace_hooks import merge_project_hooks, subagent_project_hooks
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
    resume_transcript: SubagentTranscript | None = None,
    followup_message: str | None = None,
    inbound_messages: Callable[[bool], list[str]] | None = None,
    depth: int = 1,
    parent_subagent_id: str | None = None,
    tool_ceiling_names: frozenset[str] | None = None,
    additional_system_prompt: str | None = None,
    parent_tool_use_id: str | None = None,
) -> DelegateTaskObservation:
    profile = load_delegate_profile_runtime(workspace, action)
    profile_error = profile.error
    if profile_error is None:
        try:
            client = configure_agent_profile_client(
                client,
                model=profile.model,
                effort=profile.effort,
            )
        except ValueError as error:
            profile_error = str(error)
    delegate_workspace = replace(
        profile.workspace or workspace,
        maintain_shell_cwd=False,
    )
    if profile.mode is not None:
        action = replace(action, mode=profile.mode)
    parent_approval_policy = approval_policy
    approval_policy, permissions = resolve_profile_permissions(
        profile,
        approval_policy,
        permissions,
    )
    if (
        profile.permission_mode == "plan"
        and parent_approval_policy != "plan"
        and action.mode != "explore"
    ):
        action = replace(action, mode="explore")
    hooks = merge_project_hooks(hooks, subagent_project_hooks(profile.hooks))
    if profile.max_turns is not None:
        action = replace(action, max_iterations=profile.max_turns)
    if action.isolation is None and profile.isolation is not None:
        action = replace(action, isolation="worktree")
    profile_prompt = _merge_system_prompts(
        profile.prompt,
        additional_system_prompt,
        workspace.append_subagent_system_prompt,
    )
    allowed_tool_names = profile.allowed_tool_names
    disallowed_tool_names = (
        profile.disallowed_tool_names | globally_denied_tool_names(permissions)
    )
    if tool_ceiling_names is not None:
        allowed_tool_names = (
            tool_ceiling_names
            if allowed_tool_names is None
            else allowed_tool_names & tool_ceiling_names
        )
        disallowed_tool_names = (
            disallowed_tool_names
            | (TEAM_COORDINATION_TOOL_NAMES - tool_ceiling_names)
        )
    _record_delegate_start(
        delegate_workspace,
        action,
        parent_iteration,
        subagent_id,
        approval_policy,
        profile,
        logger,
        depth,
        parent_subagent_id,
        parent_tool_use_id,
    )
    policy_error = _delegate_policy_error(
        delegate_workspace,
        action,
        approval_policy,
        profile_error,
        depth,
        resume_transcript is not None,
        subagent_id,
    )
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

    worktree_runtime: SubagentWorktreeRuntime | None = None
    if action.isolation == "worktree":
        try:
            worktree_runtime = prepare_subagent_worktree(
                delegate_workspace,
                subagent_id,
                resume_transcript.worktree if resume_transcript is not None else None,
                WorktreeHookContext(
                    hooks, permissions, approval_policy, approval_handler,
                    command_timeout_ms, logger,
                ),
            )
            delegate_workspace = worktree_runtime.workspace
        except SubagentWorktreeError as error:
            return finish_delegate_task(
                delegate_workspace,
                action,
                subagent_id,
                ok=False,
                summary="",
                iterations=0,
                tool_calls=[],
                message=f"Subagent worktree isolation failed: {error}",
                logger=logger,
            )

    transcript_started = False
    try:
        observations = parent_observations if action.mode == "code" and parent_observations is not None else []
        steps = parent_steps if action.mode == "code" and parent_steps is not None else []
        if resume_transcript is None:
            messages = build_delegate_messages(delegate_workspace, action, profile_prompt=profile_prompt)
        else:
            messages = append_resumed_subagent_prompt(
                list(resume_transcript.messages),
                workspace.append_subagent_system_prompt,
            )
            messages.append(ChatMessage(role="user", content=f"Follow-up from the parent agent:\n{followup_message or ''}"))

        if resume_transcript is None:
            create_subagent_transcript(
                delegate_workspace,
                subagent_id,
                action,
                messages,
                worktree_runtime.record if worktree_runtime is not None else None,
                depth=depth,
                parent_id=parent_subagent_id,
            )
        else:
            resume_subagent_transcript(
                delegate_workspace,
                resume_transcript,
                messages,
                worktree_runtime.record if worktree_runtime is not None else None,
            )
        transcript_started = True

        hook_model_runtime = HookModelRuntime(
            client=client,
            complete_with_retries=complete_with_retries,
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            logger=logger,
        )
        auto_mode_runtime = AutoModeRuntime(
            model=hook_model_runtime,
            messages_provider=lambda: messages,
            interactive=approval_handler is not None,
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
            hook_model_runtime=hook_model_runtime,
        )
        lifecycle.start(messages)
    except Exception as error:
        worktree_outcome = _finalize_delegate_worktree(
            workspace, subagent_id, worktree_runtime,
            WorktreeHookContext(hooks, permissions, approval_policy, approval_handler, command_timeout_ms, logger),
        )
        result = finish_delegate_task(
            delegate_workspace,
            action,
            subagent_id,
            ok=False,
            summary="",
            iterations=0,
            tool_calls=[],
            message=f"Subagent setup failed: {type(error).__name__}: {error}",
            logger=logger,
        )
        if worktree_outcome is not None:
            result = _attach_worktree_outcome(result, worktree_outcome)
        if transcript_started:
            complete_subagent_transcript(delegate_workspace, subagent_id, action, messages, result)
        return result

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
    transcript_checkpoint = lambda current: checkpoint_subagent_transcript(
        delegate_workspace, subagent_id, action, current
    )
    inbox = (
        DelegateInbox(
            workspace=delegate_workspace,
            subagent_id=subagent_id,
            parent_iteration=parent_iteration,
            receive=inbound_messages,
            checkpoint=transcript_checkpoint,
        )
        if inbound_messages is not None
        else None
    )
    worktree_outcome: SubagentWorktreeOutcome | None = None
    nested_runtime = NestedDelegateRuntime(
        workspace=delegate_workspace,
        subagent_id=subagent_id,
        depth=depth,
        mode=action.mode,
        team_member_name=action.teammate_name,
        cancel_requested=cancel_requested,
        execute_child=lambda child_action, child_id, child_depth, parent_id, child_parent_iteration, child_parent_tool_use_id, child_cancel, child_inbound: execute_delegate_task_action(
            delegate_workspace,
            child_action,
            client,
            parent_iteration=child_parent_iteration,
            subagent_id=child_id,
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
            cancel_requested=child_cancel,
            inbound_messages=child_inbound,
            depth=child_depth,
            parent_subagent_id=parent_id,
            parent_tool_use_id=child_parent_tool_use_id,
            tool_ceiling_names=tool_ceiling_names,
        ),
    )
    try:
        result = run_delegate_iterations(
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
                nested_runtime=nested_runtime,
                hook_model_runtime=hook_model_runtime,
                auto_mode_runtime=auto_mode_runtime,
                transcript_checkpoint=transcript_checkpoint,
                inbox=inbox,
            )
        )
    except Exception as error:
        result = finish_delegate_task(
            delegate_workspace,
            action,
            subagent_id,
            ok=False,
            summary="",
            iterations=0,
            tool_calls=[],
            message=f"Subagent execution failed: {type(error).__name__}: {error}",
            logger=logger,
        )
    finally:
        worktree_outcome = _finalize_delegate_worktree(
            workspace, subagent_id, worktree_runtime,
            WorktreeHookContext(hooks, permissions, approval_policy, approval_handler, command_timeout_ms, logger),
        )
    if worktree_outcome is not None:
        result = _attach_worktree_outcome(result, worktree_outcome)
    result = replace(
        result,
        depth=depth,
        parent_id=parent_subagent_id,
        teammate_name=action.teammate_name,
    )
    complete_subagent_transcript(delegate_workspace, subagent_id, action, messages, result)
    return result


def _finalize_delegate_worktree(
    workspace: RunWorkspace,
    subagent_id: str,
    runtime: SubagentWorktreeRuntime | None,
    hook_context: WorktreeHookContext | None = None,
) -> SubagentWorktreeOutcome | None:
    if runtime is None:
        return None
    outcome = finalize_subagent_worktree(workspace, runtime, hook_context)
    append_session_event(
        workspace.session_dir,
        "subagent_worktree_finalized",
        {
            "subagent_id": subagent_id,
            "path": outcome.path,
            "branch": outcome.branch,
            "preserved": outcome.preserved,
            "message": outcome.message,
        },
    )
    return outcome


def _attach_worktree_outcome(
    result: DelegateTaskObservation,
    outcome: SubagentWorktreeOutcome,
) -> DelegateTaskObservation:
    return replace(
        result,
        isolation="worktree",
        worktree_path=outcome.path,
        worktree_branch=outcome.branch,
        worktree_preserved=outcome.preserved,
        message=f"{result.message} {outcome.message}".strip(),
    )


def _merge_system_prompts(*prompts: str | None) -> str | None:
    sections = [
        section.strip()
        for section in prompts
        if section and section.strip()
    ]
    return "\n\n".join(sections) or None


def _delegate_policy_error(
    workspace: RunWorkspace,
    action: DelegateTaskAction,
    approval_policy: ApprovalPolicy,
    profile_error: str | None,
    depth: int,
    resuming: bool,
    subagent_id: str,
) -> str | None:
    if profile_error is not None:
        return f"Project agent profile could not be loaded: {profile_error}"
    if action.mode == "code" and approval_policy == "plan":
        return "Code delegation is unavailable while Plan mode is active."
    if action.teammate_name is not None and action.teammate_name != subagent_id:
        return "Teammate name must match its stable background task ID."
    spawn_error = teammate_spawn_error(
        workspace,
        action.teammate_name,
        depth=depth,
        allow_existing=resuming,
    )
    if spawn_error is not None:
        return spawn_error
    return None


def _record_delegate_start(
    workspace: RunWorkspace,
    action: DelegateTaskAction,
    parent_iteration: int,
    subagent_id: str,
    approval_policy: ApprovalPolicy,
    profile: DelegateProfileRuntime,
    logger: AgentLogger | None,
    depth: int,
    parent_subagent_id: str | None,
    parent_tool_use_id: str | None,
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
            "profile_model": profile.model,
            "profile_effort": profile.effort,
            "profile_disallowed_tools": sorted(profile.disallowed_tool_names),
            "profile_memory_scope": profile.memory_scope,
            "isolation": action.isolation,
            "approval_policy": approval_policy,
            "depth": depth,
            "parent_subagent_id": parent_subagent_id,
            "parent_tool_use_id": parent_tool_use_id or subagent_id,
        },
    )
    if action.teammate_name is not None:
        append_session_event(
            workspace.session_dir,
            "teammate_spawned",
            {
                "iteration": parent_iteration,
                "name": action.teammate_name,
                "subagent_id": subagent_id,
                "agent": action.agent,
                "mode": action.mode,
            },
        )
    if logger:
        logger(f"{action.mode} subagent started", action.task)
