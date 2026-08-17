from __future__ import annotations

from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

from .agent_result import AgentResult
from .cli_interactive_project_runtime import InteractiveProjectRuntime
from .cli_model_stream import terminal_model_stream_scope
from .cli_output import build_approval_handler, format_error
from .cli_subagent_panel import SubagentPanel
from .cli_verbose_output import VerboseTranscriptRenderer
from .config_execution import ExecutionConfig
from .debug_runtime import DebugRuntime, combine_agent_loggers
from .dynamic_agent_profiles import DynamicAgentProfile
from .interactive_permission_mode import (
    InteractivePermissionState,
    initial_interactive_permission_state,
)
from .model_streaming import supports_model_streaming
from .session_event_observers import observe_session_events
from .session_names import transfer_session_name
from .types import (
    ApprovalHandler,
    ApprovalPolicy,
    ChatClient,
    ChatMessage,
    UserInputHandler,
)
from .workspace_core import BrowserMode, RunWorkspace, create_local_workspace, create_run_workspace
from .workspace_permissions import ProjectPermissions
from .workspace_teammate_mode import resolve_teammate_mode
from .workspace_view_mode import resolve_verbose_mode


@dataclass(frozen=True)
class InteractiveCodeTurnRequest:
    project_root: Path
    task: str
    task_metadata: dict[str, object] | None
    client: ChatClient | None
    resume_run_id: str | None
    resume_context: str | None
    pending_workspace: RunWorkspace | None
    pending_branch_source_run_id: str | None
    conversation_messages: tuple[ChatMessage, ...]
    approval_policy: ApprovalPolicy
    approval_handler: ApprovalHandler | None
    permission_state: InteractivePermissionState
    permission_overrides: ProjectPermissions
    project_permissions_trusted: bool
    project_runtime: InteractiveProjectRuntime
    additional_directories: tuple[Path, ...]
    system_prompt: str | None
    append_system_prompt: str | None
    agent: str | None
    dynamic_agent_profiles: tuple[DynamicAgentProfile, ...]
    teammate_mode: str | None
    autocompact_tokens: int | None
    safe_mode: bool
    bare_mode: bool
    brief: bool
    disable_slash_commands: bool
    verbose: bool
    screen_reader: bool
    browser_mode: BrowserMode
    setting_sources: tuple[str, ...]
    settings_override_json: str | None
    invocation_plugin_dirs: tuple[Path, ...]
    debug_runtime: DebugRuntime


@dataclass(frozen=True)
class InteractiveCodeTurnServices:
    create_client: Callable[[], ChatClient]
    run_agent: Callable[..., AgentResult]
    get_resume_context: Callable[[str], tuple[str | None, str | None, str]]
    resolve_execution_config: Callable[[Path], ExecutionConfig]
    collect_directory_context: Callable[
        [RunWorkspace, str | None],
        tuple[str | None, tuple[str, ...]],
    ]
    print_agent_result: Callable[..., None]
    prompt_user_input: UserInputHandler | None


@dataclass(frozen=True)
class InteractiveCodeTurnResult:
    agent_result: AgentResult
    next_context: str | None
    client: ChatClient
    resume_run_id: str | None
    resume_context: str | None
    pending_workspace: RunWorkspace
    conversation_messages: tuple[ChatMessage, ...]
    approval_policy: ApprovalPolicy
    approval_handler: ApprovalHandler | None
    permission_state: InteractivePermissionState
    permission_overrides: ProjectPermissions


def run_interactive_code_turn(
    request: InteractiveCodeTurnRequest,
    services: InteractiveCodeTurnServices,
) -> InteractiveCodeTurnResult:
    execution_config = services.resolve_execution_config(request.project_root)
    active_workspace = request.pending_workspace
    settings_workspace = active_workspace or create_local_workspace(
        request.project_root,
        request.resume_run_id or "view-mode",
        additional_roots=request.additional_directories,
        safe_mode=request.safe_mode,
        bare_mode=request.bare_mode,
        disable_slash_commands=request.disable_slash_commands,
        setting_sources=request.setting_sources,
        settings_override_json=request.settings_override_json,
        invocation_plugin_dirs=request.invocation_plugin_dirs,
    )
    verbose_mode = resolve_verbose_mode(settings_workspace, explicit=request.verbose)
    teammate_mode = resolve_teammate_mode(
        settings_workspace,
        explicit=request.teammate_mode,
    )
    if active_workspace is None and (request.debug_runtime.enabled or verbose_mode):
        active_workspace = create_run_workspace(
            request.project_root,
            additional_roots=request.additional_directories,
            safe_mode=request.safe_mode,
            bare_mode=request.bare_mode,
            disable_slash_commands=request.disable_slash_commands,
            setting_sources=request.setting_sources,
            settings_override_json=request.settings_override_json,
            invocation_plugin_dirs=request.invocation_plugin_dirs,
        )
    notification_workspace = active_workspace or settings_workspace
    if request.safe_mode:
        turn_append_system_prompt, directory_hook_errors = (
            request.append_system_prompt,
            (),
        )
    else:
        turn_append_system_prompt, directory_hook_errors = (
            services.collect_directory_context(
                notification_workspace,
                request.append_system_prompt,
            )
        )
    for error in directory_hook_errors:
        print(f"DirectoryAdded hook warning: {error}")

    client = request.client or services.create_client()
    panel = SubagentPanel(
        request.project_root,
        safe_mode=request.safe_mode,
        workspace=notification_workspace,
        brief=request.brief,
        teammate_mode=teammate_mode,
        screen_reader=request.screen_reader,
    )
    panel.authorize_custom(request.approval_handler, request.approval_policy)
    initial_panel_error = panel.config_error
    if panel.config_error:
        print(f"Plugin subagentStatusLine warning: {panel.config_error}")
    panel_kwargs: dict[str, object] = {}
    selected_approval_handler = request.approval_handler
    selected_user_input_handler = services.prompt_user_input
    if panel.enabled or request.brief:
        panel_kwargs = {
            "logger": combine_agent_loggers(panel.log, request.debug_runtime.logger),
            "workspace_observer": panel.bind,
        }
        selected_approval_handler = panel.wrap_approval_handler(request.approval_handler)
        selected_user_input_handler = panel.wrap_user_input_handler(selected_user_input_handler)
    elif request.debug_runtime.logger is not None:
        panel_kwargs = {"logger": request.debug_runtime.logger}

    source_run_id = request.resume_run_id
    verbose_renderer = (
        VerboseTranscriptRenderer(
            sys.stdout,
            show_model_text=not supports_model_streaming(client),
            on_display_start=panel.pause,
            on_display_end=panel.resume,
        )
        if verbose_mode
        else None
    )
    verbose_scope = (
        observe_session_events(active_workspace.session_dir, verbose_renderer.observe)
        if active_workspace is not None and verbose_renderer is not None
        else nullcontext()
    )
    try:
        with (
            request.debug_runtime.event_scope(active_workspace),
            verbose_scope,
            terminal_model_stream_scope(
                client,
                on_display_start=panel.pause,
                on_display_end=panel.resume,
            ) as stream_renderer,
        ):
            result = services.run_agent(
                request.task,
                client=client,
                max_iterations=execution_config.max_iterations,
                command_timeout_ms=execution_config.command_timeout_ms,
                max_output_tokens=execution_config.max_output_tokens,
                model_retries=execution_config.model_retries,
                model_retry_delay_ms=execution_config.model_retry_delay_ms,
                model_timeout_ms=execution_config.model_timeout_ms,
                approval_handler=selected_approval_handler,
                approval_policy=request.approval_policy,
                permission_overrides=request.permission_overrides,
                bypass_permissions_available=request.permission_state.bypass_available,
                trust_project_permissions=request.project_permissions_trusted,
                user_input_handler=selected_user_input_handler,
                prior_context=request.resume_context,
                prior_messages=(
                    list(request.conversation_messages)
                    if request.conversation_messages
                    else None
                ),
                system_prompt=request.system_prompt,
                append_system_prompt=turn_append_system_prompt,
                task_metadata=request.task_metadata,
                task_source_run_id=(
                    request.pending_branch_source_run_id
                    or (
                        request.resume_run_id
                        if active_workspace is None and request.resume_context is not None
                        else None
                    )
                ),
                workspace=active_workspace,
                peer_runtime=request.project_runtime.peer,
                agent=request.agent,
                dynamic_agent_profiles=request.dynamic_agent_profiles,
                additional_directories=request.additional_directories,
                autocompact_tokens=request.autocompact_tokens,
                safe_mode=request.safe_mode,
                bare_mode=request.bare_mode,
                brief=request.brief,
                disable_slash_commands=request.disable_slash_commands,
                browser_mode=request.browser_mode,
                setting_sources=request.setting_sources,
                settings_override_json=request.settings_override_json,
                invocation_plugin_dirs=request.invocation_plugin_dirs,
                **(
                    {"model_stream_handler": stream_renderer.agent_event}
                    if stream_renderer is not None
                    else {}
                ),
                **panel_kwargs,
            )
    finally:
        panel.close()
    if panel.config_error and panel.config_error != initial_panel_error:
        print(f"Plugin subagentStatusLine warning: {panel.config_error}")
    services.print_agent_result(
        result,
        message_already_displayed=(
            stream_renderer.matches_final_message(result.displayed_message)
            if stream_renderer is not None
            else False
        ),
    )

    approval_policy = request.approval_policy
    permission_state = request.permission_state
    permission_overrides = request.permission_overrides
    approval_handler = request.approval_handler
    result_approval_policy = getattr(result, "approval_policy", None)
    if (
        result_approval_policy in {"ask", "allow", "auto", "deny", "dontAsk", "plan"}
        and result_approval_policy != approval_policy
    ):
        approval_policy = result_approval_policy
        permission_state = initial_interactive_permission_state(
            permission_mode=None,
            approval_policy=approval_policy,
            permission_overrides=permission_overrides,
            allow_bypass=(
                permission_state.bypass_available or approval_policy == "allow"
            ),
        )
        permission_overrides = permission_state.permission_overrides
        approval_handler = build_approval_handler(approval_policy)
        request.project_runtime.update_approval_policy(approval_policy)

    conversation_messages = tuple(getattr(result, "conversation", []))
    if active_workspace is None:
        try:
            transfer_session_name(request.project_root, source_run_id, result.run_id)
        except (OSError, ValueError) as error:
            print(f"Session name persistence warning: {format_error(error)}")
    pending_workspace = create_local_workspace(
        request.project_root,
        result.run_id,
        additional_roots=request.additional_directories,
        safe_mode=request.safe_mode,
        bare_mode=request.bare_mode,
        setting_sources=request.setting_sources,
        settings_override_json=request.settings_override_json,
        invocation_plugin_dirs=request.invocation_plugin_dirs,
    )
    request.project_runtime.register_session(result.run_id)
    selected, next_context, _ = services.get_resume_context(result.run_id)
    resume_run_id = request.resume_run_id
    resume_context = request.resume_context
    if next_context:
        resume_run_id = selected
        resume_context = next_context
    return InteractiveCodeTurnResult(
        agent_result=result,
        next_context=next_context,
        client=client,
        resume_run_id=resume_run_id,
        resume_context=resume_context,
        pending_workspace=pending_workspace,
        conversation_messages=conversation_messages,
        approval_policy=approval_policy,
        approval_handler=approval_handler,
        permission_state=permission_state,
        permission_overrides=permission_overrides,
    )


__all__ = [
    "InteractiveCodeTurnRequest",
    "InteractiveCodeTurnResult",
    "InteractiveCodeTurnServices",
    "run_interactive_code_turn",
]
