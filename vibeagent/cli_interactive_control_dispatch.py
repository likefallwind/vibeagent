from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .cli_interactive_directories import (
    InteractiveAddDirectoryRequest,
    InteractiveDirectorySwitchRequest,
    apply_interactive_add_directory,
    switch_interactive_directory,
)
from .cli_interactive_project_runtime import InteractiveProjectRuntime
from .cli_interactive_session_navigation import (
    InteractiveSessionNavigationRequest,
    InteractiveSessionNavigationState,
    navigate_interactive_session,
)
from .cli_system_prompt_state import update_system_prompt_state
from .command_types import LocalCommand
from .dynamic_workflow_commands import handle_workflows_command
from .dynamic_workflow_runtime import DynamicWorkflowManager
from .goal_state import GoalState
from .interactive_permission_mode import (
    InteractivePermissionState,
    update_interactive_permission_state,
)
from .lsp_runtime import close_project_lsp
from .mcp_commands import handle_mcp_command
from .peer_commands import get_peer_sessions_text
from .peer_inbox_commands import handle_peer_inbox_command
from .plugin_commands import handle_plugin_command, reload_plugins_text
from .types import ApprovalHandler, ApprovalPolicy, ChatClient, ChatMessage
from .workspace_core import RunWorkspace, create_local_workspace
from .workspace_permissions import ProjectPermissions


@dataclass(frozen=True)
class InteractiveControlState:
    client: ChatClient | None
    project_runtime: InteractiveProjectRuntime
    project_permissions_trusted: bool
    additional_directories: tuple[Path, ...]
    pending_workspace: RunWorkspace | None
    pending_branch_source_run_id: str | None
    resume_run_id: str | None
    resume_context: str | None
    conversation_messages: tuple[ChatMessage, ...]
    goal_state: GoalState | None
    permission_state: InteractivePermissionState
    approval_policy: ApprovalPolicy
    approval_handler: ApprovalHandler | None
    permission_overrides: ProjectPermissions
    system_prompt: str | None
    append_system_prompt: str | None


@dataclass(frozen=True)
class InteractiveControlRequest:
    project_root: Path
    command: LocalCommand
    command_namespace: dict[str, Any]
    state: InteractiveControlState
    safe_mode: bool
    bare_mode: bool
    disable_slash_commands: bool
    setting_sources: tuple[str, ...]
    settings_override_json: str | None
    invocation_plugin_dirs: tuple[Path, ...]


@dataclass(frozen=True)
class InteractiveControlResult:
    state: InteractiveControlState
    messages: tuple[str, ...]
    reset_code_recap: bool = False


def dispatch_interactive_control_command(
    request: InteractiveControlRequest,
    *,
    get_workflow_manager: Callable[[], DynamicWorkflowManager],
    get_resume_context: Callable[..., tuple[str | None, str | None, str]],
    run_lifecycle_hook: Callable[[str, str, str | None], object],
    prompt_project_permission_trust: Callable[[Path], bool],
    build_approval_handler: Callable[[ApprovalPolicy], ApprovalHandler | None],
) -> InteractiveControlResult | None:
    command = request.command
    state = request.state
    if command.type == "workflows":
        if request.safe_mode:
            return _result(state, "Custom workflows are disabled by safe mode.")
        manager = get_workflow_manager()
        return _result(
            replace(state, resume_run_id=manager.workspace.run_id),
            handle_workflows_command(manager, command.argument),
        )
    if command.type == "plugin":
        if request.safe_mode:
            return _result(state, "Plugins are disabled by safe mode.")
        plugin_result = handle_plugin_command(request.project_root, command.argument)
        if plugin_result.changed:
            state.project_runtime.close_workflow()
            close_project_lsp(request.project_root)
            state.project_runtime.start_plugin_updates()
        return _result(state, plugin_result.text)
    if command.type == "mcp":
        if request.safe_mode:
            return _result(state, "MCP servers are disabled by safe mode.")
        return _result(state, handle_mcp_command(request.project_root, command.argument).text)
    if command.type == "reload_plugins":
        if request.safe_mode:
            return _result(state, "Plugins are disabled by safe mode.")
        state.project_runtime.close_workflow()
        close_project_lsp(request.project_root)
        workspace = state.pending_workspace or create_local_workspace(
            request.project_root,
            state.resume_run_id or "plugin-reload",
            additional_roots=state.additional_directories,
            safe_mode=request.safe_mode,
            bare_mode=request.bare_mode,
            setting_sources=request.setting_sources,
            settings_override_json=request.settings_override_json,
            invocation_plugin_dirs=request.invocation_plugin_dirs,
        )
        return _result(
            state,
            reload_plugins_text(request.project_root, workspace=workspace),
        )
    if command.type == "list_agents_local":
        return _result(state, get_peer_sessions_text())
    if command.type == "peer_inbox":
        return _result(
            state,
            handle_peer_inbox_command(state.project_runtime.peer, command.argument),
        )
    if command.type == "system_prompt":
        system_prompt, text = update_system_prompt_state(
            state.system_prompt,
            command.argument,
            label="System prompt",
        )
        return _result(replace(state, system_prompt=system_prompt), text)
    if command.type == "append_system_prompt":
        append_system_prompt, text = update_system_prompt_state(
            state.append_system_prompt,
            command.argument,
            label="Appended system prompt",
        )
        return _result(
            replace(state, append_system_prompt=append_system_prompt),
            text,
        )
    if command.type == "add_dir":
        update = apply_interactive_add_directory(
            InteractiveAddDirectoryRequest(
                project_root=request.project_root,
                argument=command.argument,
                additional_directories=state.additional_directories,
                pending_workspace=state.pending_workspace,
                resume_run_id=state.resume_run_id,
                project_runtime=state.project_runtime,
                approval_policy=state.approval_policy,
                approval_handler=state.approval_handler,
                safe_mode=request.safe_mode,
                bare_mode=request.bare_mode,
                setting_sources=request.setting_sources,
                settings_override_json=request.settings_override_json,
                invocation_plugin_dirs=request.invocation_plugin_dirs,
            )
        )
        return InteractiveControlResult(
            replace(
                state,
                additional_directories=update.additional_directories,
                pending_workspace=update.pending_workspace,
            ),
            update.messages,
        )
    if command.type == "cd":
        update = switch_interactive_directory(
            InteractiveDirectorySwitchRequest(
                project_root=request.project_root,
                argument=command.argument,
                additional_directories=state.additional_directories,
                pending_workspace=state.pending_workspace,
                pending_branch_source_run_id=state.pending_branch_source_run_id,
                resume_run_id=state.resume_run_id,
                project_permissions_trusted=state.project_permissions_trusted,
                project_runtime=state.project_runtime,
                goal_state=state.goal_state,
                approval_policy=state.approval_policy,
                safe_mode=request.safe_mode,
                bare_mode=request.bare_mode,
                setting_sources=request.setting_sources,
                settings_override_json=request.settings_override_json,
                invocation_plugin_dirs=request.invocation_plugin_dirs,
            ),
            run_session_end_hook=lambda: run_lifecycle_hook("session_end", "other", None),
            prompt_project_permission_trust=prompt_project_permission_trust,
        )
        return InteractiveControlResult(
            replace(
                state,
                client=None if update.changed else state.client,
                project_runtime=update.project_runtime,
                project_permissions_trusted=update.project_permissions_trusted,
                additional_directories=update.additional_directories,
                pending_workspace=update.pending_workspace,
                pending_branch_source_run_id=update.pending_branch_source_run_id,
                resume_run_id=update.resume_run_id,
            ),
            update.messages,
        )
    if command.type == "approval":
        permission_state, text = update_interactive_permission_state(
            state.permission_state,
            command.argument,
        )
        approval_policy = permission_state.approval_policy
        approval_handler = state.approval_handler
        if approval_policy != state.permission_state.approval_policy:
            approval_handler = build_approval_handler(approval_policy)
            state.project_runtime.update_approval_policy(approval_policy)
        return _result(
            replace(
                state,
                permission_state=permission_state,
                approval_policy=approval_policy,
                approval_handler=approval_handler,
                permission_overrides=permission_state.permission_overrides,
            ),
            text,
        )

    navigation = navigate_interactive_session(
        InteractiveSessionNavigationRequest(
            project_root=request.project_root,
            command=command,
            command_namespace=request.command_namespace,
            state=InteractiveSessionNavigationState(
                resume_run_id=state.resume_run_id,
                resume_context=state.resume_context,
                pending_workspace=state.pending_workspace,
                pending_branch_source_run_id=state.pending_branch_source_run_id,
                additional_directories=state.additional_directories,
                conversation_messages=state.conversation_messages,
                goal_state=state.goal_state,
            ),
            project_runtime=state.project_runtime,
            safe_mode=request.safe_mode,
            bare_mode=request.bare_mode,
            disable_slash_commands=request.disable_slash_commands,
            setting_sources=request.setting_sources,
            settings_override_json=request.settings_override_json,
            invocation_plugin_dirs=request.invocation_plugin_dirs,
        ),
        get_resume_context=get_resume_context,
        run_lifecycle_hook=run_lifecycle_hook,
    )
    if not navigation.handled:
        return None
    return InteractiveControlResult(
        replace(
            state,
            resume_run_id=navigation.state.resume_run_id,
            resume_context=navigation.state.resume_context,
            pending_workspace=navigation.state.pending_workspace,
            pending_branch_source_run_id=navigation.state.pending_branch_source_run_id,
            additional_directories=navigation.state.additional_directories,
            conversation_messages=navigation.state.conversation_messages,
            goal_state=navigation.state.goal_state,
        ),
        navigation.messages,
        reset_code_recap=navigation.reset_code_recap,
    )


def _result(state: InteractiveControlState, message: str) -> InteractiveControlResult:
    return InteractiveControlResult(state, (message,))


__all__ = [
    "InteractiveControlRequest",
    "InteractiveControlResult",
    "InteractiveControlState",
    "dispatch_interactive_control_command",
]
