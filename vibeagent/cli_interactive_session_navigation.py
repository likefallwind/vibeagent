from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

from .cli_checkpoint_local_flags import run_interactive_checkpoint_command
from .cli_interactive_branch import prepare_interactive_branch_switch
from .cli_interactive_project_runtime import InteractiveProjectRuntime
from .cli_interactive_rewind import run_interactive_rewind_command
from .cli_interactive_session_management import run_interactive_session_management
from .cli_output import format_error
from .cli_session_local_flags import (
    CompactBlocked,
    run_interactive_resume_command,
    run_interactive_session_command,
)
from .command_types import LocalCommand
from .goal_state import GoalState, read_session_goal, reset_restored_goal
from .session_additional_directories import (
    merge_additional_directories,
    restore_session_additional_directories,
)
from .session_conversation import load_session_conversation
from .types import ChatMessage
from .workspace_core import RunWorkspace, create_local_workspace


LifecycleEvent = Literal["session_end", "pre_compact", "post_compact"]
LifecycleHook = Callable[[LifecycleEvent, str, str | None], object]


@dataclass(frozen=True)
class InteractiveSessionNavigationState:
    resume_run_id: str | None
    resume_context: str | None
    pending_workspace: RunWorkspace | None
    pending_branch_source_run_id: str | None
    additional_directories: tuple[Path, ...]
    conversation_messages: tuple[ChatMessage, ...]
    goal_state: GoalState | None


@dataclass(frozen=True)
class InteractiveSessionNavigationRequest:
    project_root: Path
    command: LocalCommand
    command_namespace: dict[str, Any]
    state: InteractiveSessionNavigationState
    project_runtime: InteractiveProjectRuntime
    safe_mode: bool
    bare_mode: bool
    disable_slash_commands: bool
    setting_sources: tuple[str, ...]
    settings_override_json: str | None
    invocation_plugin_dirs: tuple[Path, ...]


@dataclass(frozen=True)
class InteractiveSessionNavigationResult:
    handled: bool
    state: InteractiveSessionNavigationState
    messages: tuple[str, ...] = ()
    reset_code_recap: bool = False


def navigate_interactive_session(
    request: InteractiveSessionNavigationRequest,
    *,
    get_resume_context: Callable[..., tuple[str | None, str | None, str]],
    run_lifecycle_hook: LifecycleHook,
) -> InteractiveSessionNavigationResult:
    command = request.command
    state = request.state
    session_update = run_interactive_session_management(
        command,
        project_root=request.project_root,
        run_id=state.resume_run_id,
        pending_workspace=state.pending_workspace,
    )
    if session_update is not None:
        return _handled(
            replace(
                state,
                resume_run_id=session_update.run_id,
                pending_workspace=session_update.pending_workspace,
            ),
            session_update.text,
        )

    session_text = run_interactive_session_command(
        command,
        request.command_namespace,
    )
    if session_text is not None:
        return _handled(state, session_text)

    rewind = run_interactive_rewind_command(
        command,
        project_root=request.project_root,
        run_id=state.resume_run_id,
        get_resume_context=get_resume_context,
    )
    if rewind is not None:
        if rewind.workspace is None or rewind.context is None:
            return _handled(state, rewind.text)
        request.project_runtime.close_workflow()
        return InteractiveSessionNavigationResult(
            handled=True,
            state=replace(
                state,
                pending_workspace=rewind.workspace,
                pending_branch_source_run_id=None,
                resume_run_id=rewind.workspace.run_id,
                resume_context=rewind.context,
                additional_directories=rewind.workspace.additional_roots,
                goal_state=None,
                conversation_messages=(),
            ),
            messages=(rewind.text,),
            reset_code_recap=True,
        )

    checkpoint_text = run_interactive_checkpoint_command(
        command,
        request.command_namespace,
        state.resume_run_id,
    )
    if checkpoint_text is not None:
        return _handled(state, checkpoint_text)

    resume_result = run_interactive_resume_command(
        command,
        request.command_namespace,
        before_compact=lambda: run_lifecycle_hook("pre_compact", "manual", None),
        after_compact=lambda summary: run_lifecycle_hook(
            "post_compact",
            "manual",
            summary,
        ),
    )
    if resume_result is not None:
        if isinstance(resume_result, CompactBlocked):
            return _handled(
                state,
                f"Compaction blocked by PreCompact hook: {resume_result.message}",
            )
        return _apply_resume(
            request,
            resume_result,
            run_lifecycle_hook=run_lifecycle_hook,
        )

    if command.type == "branch":
        return _apply_branch(
            request,
            get_resume_context=get_resume_context,
            run_lifecycle_hook=run_lifecycle_hook,
        )
    return InteractiveSessionNavigationResult(False, state)


def _apply_resume(
    request: InteractiveSessionNavigationRequest,
    resume_result: tuple[str | None, str | None, str],
    *,
    run_lifecycle_hook: LifecycleHook,
) -> InteractiveSessionNavigationResult:
    state = request.state
    selected, context, text = resume_result
    restored_directories = restore_session_additional_directories(
        request.project_root,
        selected,
    )
    try:
        next_directories = merge_additional_directories(
            request.project_root,
            state.additional_directories,
            restored_directories.directories,
        )
    except ValueError as error:
        return _handled(state, f"Resume error: {format_error(error)}")

    request.project_runtime.close_workflow()
    if request.command.type == "resume" and selected != state.resume_run_id:
        run_lifecycle_hook("session_end", "resume", None)
    restored_conversation = (
        load_session_conversation(request.project_root, selected)
        if request.command.type == "resume"
        else None
    )
    pending_workspace = (
        create_local_workspace(
            request.project_root,
            selected,
            additional_roots=next_directories,
            safe_mode=request.safe_mode,
            bare_mode=request.bare_mode,
            setting_sources=request.setting_sources,
            settings_override_json=request.settings_override_json,
            invocation_plugin_dirs=request.invocation_plugin_dirs,
        )
        if request.command.type == "resume" and selected is not None
        else None
    )
    restored_goal = (
        read_session_goal(request.project_root, selected)
        if selected is not None
        else None
    )
    messages = [text]
    if restored_conversation is not None and restored_conversation.warning:
        messages.append(restored_conversation.warning)
    if restored_directories.message:
        messages.append(restored_directories.message)
    return InteractiveSessionNavigationResult(
        handled=True,
        state=replace(
            state,
            resume_run_id=selected,
            resume_context=context,
            pending_workspace=pending_workspace,
            pending_branch_source_run_id=None,
            additional_directories=next_directories,
            conversation_messages=(
                tuple(restored_conversation.messages)
                if restored_conversation is not None
                else ()
            ),
            goal_state=(
                reset_restored_goal(restored_goal)
                if restored_goal is not None
                else None
            ),
        ),
        messages=tuple(messages),
        reset_code_recap=True,
    )


def _apply_branch(
    request: InteractiveSessionNavigationRequest,
    *,
    get_resume_context: Callable[..., tuple[str | None, str | None, str]],
    run_lifecycle_hook: LifecycleHook,
) -> InteractiveSessionNavigationResult:
    state = request.state
    branch = prepare_interactive_branch_switch(
        request.project_root,
        state.resume_run_id,
        request.command.argument,
        state.additional_directories,
        get_resume_context=get_resume_context,
    )
    if branch.error is not None or branch.workspace is None or branch.source_run_id is None:
        return _handled(
            state,
            f"Branch error: {branch.error or 'branch state is incomplete.'}",
        )

    request.project_runtime.close_workflow()
    run_lifecycle_hook("session_end", "resume", None)
    pending_workspace = replace(
        branch.workspace,
        safe_mode=request.safe_mode,
        bare_mode=request.bare_mode,
        disable_slash_commands=request.disable_slash_commands,
        setting_sources=request.setting_sources,
        settings_override_json=request.settings_override_json,
        invocation_plugin_dirs=request.invocation_plugin_dirs,
    )
    restored_conversation = load_session_conversation(
        request.project_root,
        branch.source_run_id,
    )
    restored_goal = read_session_goal(request.project_root, branch.workspace.run_id)
    messages = [branch.text]
    if restored_conversation.warning:
        messages.append(restored_conversation.warning)
    return InteractiveSessionNavigationResult(
        handled=True,
        state=replace(
            state,
            pending_workspace=pending_workspace,
            pending_branch_source_run_id=branch.source_run_id,
            resume_run_id=branch.workspace.run_id,
            resume_context=branch.context,
            conversation_messages=tuple(restored_conversation.messages),
            goal_state=(
                reset_restored_goal(restored_goal)
                if restored_goal is not None
                else None
            ),
        ),
        messages=tuple(messages),
        reset_code_recap=True,
    )


def _handled(
    state: InteractiveSessionNavigationState,
    message: str,
) -> InteractiveSessionNavigationResult:
    return InteractiveSessionNavigationResult(True, state, (message,))


__all__ = [
    "InteractiveSessionNavigationRequest",
    "InteractiveSessionNavigationResult",
    "InteractiveSessionNavigationState",
    "navigate_interactive_session",
]
