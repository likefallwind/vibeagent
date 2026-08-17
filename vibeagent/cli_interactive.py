from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from threading import Lock
from typing import Any, Literal, cast

from . import __version__
from .agent import run_agent as default_run_agent
from .agent_result import AgentResult
from .btw import run_btw as default_run_btw
from .builtin_model_workflows import resolve_builtin_model_workflow
from .chat import run_chat as default_run_chat
from .session_recap import (
    SessionRecapState,
    attempt_automatic_session_recap,
    automatic_session_recaps_enabled,
    run_session_recap as default_run_session_recap,
)
from .directory_added_hooks import collect_directory_added_turn_context
from .cli_completion import interactive_prompt_completion
from .cli_output import (
    build_approval_handler,
    format_error,
    print_agent_result,
    prompt_project_permission_trust,
    prompt_user_input,
)
from .cli_model_stream import terminal_model_stream_scope
from .cli_project_command_expansion import (
    expand_code_task_project_command,
    project_command_task_metadata,
)
from .cli_idle_input import input_with_idle_callback
from .cli_idle_notification import IdleNotificationTimer
from .cli_interactive_idle import InteractiveIdleContext, run_interactive_idle_tasks
from .cli_system_prompt_state import update_system_prompt_state
from .cli_interactive_directories import (
    InteractiveAddDirectoryRequest,
    InteractiveDirectorySwitchRequest,
    apply_interactive_add_directory,
    switch_interactive_directory,
)
from .cli_interactive_session_navigation import (
    InteractiveSessionNavigationRequest,
    InteractiveSessionNavigationState,
    navigate_interactive_session,
)
from .cli_interactive_project_runtime import InteractiveProjectRuntime
from .cli_interactive_model import interactive_provider_env
from .cli_interactive_effort import configure_interactive_effort
from .autocompact_settings import (
    AutocompactSetting,
    run_autocompact_command,
)
from .cli_interactive_local_dispatch import (
    InteractiveLocalCommandContext,
    dispatch_interactive_local_command,
)
from .cli_interactive_code_turn import (
    InteractiveCodeTurnRequest,
    InteractiveCodeTurnServices,
    run_interactive_code_turn,
)
from .context_compaction import format_autocompact_setting
from .cli_interactive_provider_commands import run_interactive_provider_command
from .cli_interactive_session_management import interactive_session_prompt
from .commands import get_resume_context as default_get_resume_context, parse_local_command
from .config import resolve_execution_config
from .cli_goal import evaluate_and_store_goal
from .goal_loop import goal_turn_prompt
from .goal_state import (
    GoalState,
    clear_goal,
    format_goal_status,
    new_goal,
    read_session_goal,
    reset_restored_goal,
    write_goal,
)
from .interactive_shell import SHELL_MODE_USAGE, parse_shell_mode_input, run_interactive_shell
from .workspace_shell_response import resolve_respond_to_bash_commands
from .interactive_background import create_interactive_background_request
from .interactive_permission_mode import (
    initial_interactive_permission_state,
    update_interactive_permission_state,
)
from .providers import create_chat_client as default_create_chat_client
from .types import ApprovalPolicy, ChatClient, ChatMessage
from .dynamic_agent_profiles import DynamicAgentProfile
from .scheduled_task_store import scheduled_tasks_enabled
from .session_usage import summarize_run_usage
from .peer_commands import get_peer_sessions_text
from .peer_inbox_commands import handle_peer_inbox_command
from .plugin_commands import handle_plugin_command, reload_plugins_text
from .mcp_commands import handle_mcp_command
from .dynamic_workflow_agent import background_workflow_approval_handler, execute_workflow_agent_request
from .dynamic_workflow_commands import handle_workflows_command
from .dynamic_workflow_runtime import DynamicWorkflowManager
from .workspace_core import BrowserMode, create_local_workspace, create_run_workspace
from .workspace_hooks import read_project_hooks
from .workspace_permissions import ProjectPermissions, read_project_permissions
from .workspace_agents import format_project_agent_catalog
from .workspace_prompt_commands import format_project_prompt_commands
from .workspace_skills import format_project_skill_catalog
from .session_lifecycle_hooks import (
    create_interactive_config_change_runtime,
    create_interactive_file_changed_runtime,
    run_interactive_notification_hooks,
    run_interactive_session_hook,
)
from .workspace_core import RunWorkspace
from .anthropic_betas import normalize_anthropic_betas
from .debug_runtime import DebugOptions, DebugRuntime


def run_interactive_loop(
    *,
    command_namespace: dict[str, Any],
    create_chat_client_func: Callable[..., object] = default_create_chat_client,
    run_chat_func: Callable[..., str] = default_run_chat,
    run_btw_func: Callable[..., str] = default_run_btw,
    run_recap_func: Callable[..., str] = default_run_session_recap,
    run_agent_func: Callable[..., AgentResult] = default_run_agent,
    get_resume_context_func: Callable[..., tuple[str | None, str | None, str]] = default_get_resume_context,
    initial_resume_run_id: str | None = None,
    initial_resume_context: str | None = None,
    initial_resume_message: str | None = None,
    initial_agent: str | None = None,
    initial_dynamic_agent_profiles: tuple[DynamicAgentProfile, ...] = (),
    initial_effort: str | None = None,
    initial_effort_locked: bool = False,
    initial_autocompact_tokens: int | None = None,
    initial_autocompact_source: str = "auto",
    initial_autocompact_locked: bool = False,
    initial_background_memory_limit_bytes: int | None = None,
    initial_system_prompt: str | None = None,
    initial_append_system_prompt: str | None = None,
    initial_additional_directories: tuple[Path, ...] = (),
    initial_pending_workspace: RunWorkspace | None = None,
    initial_branch_source_run_id: str | None = None,
    initial_conversation_messages: tuple[ChatMessage, ...] = (),
    initial_attached_background_agent_id: str | None = None,
    initial_model: str | None = None,
    initial_provider_env_overrides: tuple[tuple[str, str], ...] = (),
    initial_approval: ApprovalPolicy = "ask",
    initial_permission_mode: str | None = None,
    initial_permission_overrides: ProjectPermissions = ProjectPermissions(),
    initial_bypass_permissions_available: bool = False,
    initial_safe_mode: bool = False,
    initial_bare_mode: bool = False,
    initial_brief: bool = False,
    initial_disable_slash_commands: bool = False,
    initial_verbose: bool = False,
    initial_ax_screen_reader: bool = False,
    initial_browser_mode: BrowserMode = "auto",
    initial_teammate_mode: str | None = None,
    initial_setting_sources: tuple[str, ...] = ("user", "project", "local"),
    initial_settings_override_json: str | None = None,
    initial_invocation_plugin_dirs: tuple[Path, ...] = (),
    initial_debug_options: DebugOptions = DebugOptions(),
) -> int:
    # Entry loop: parse local commands first, otherwise delegate to the agent.
    print(f"VibeAgent {__version__}")
    print("Type a programming task, or use /chat for daily conversation. Use /help for commands.")
    if initial_resume_message:
        print(initial_resume_message)
    project_permissions_trusted = prompt_project_permission_trust(Path.cwd())

    client = None
    model_override: str | None = initial_model
    effort_override: str | None = initial_effort
    effort_locked = initial_effort_locked
    autocompact_setting = AutocompactSetting(
        tokens=initial_autocompact_tokens,
        source=initial_autocompact_source,
        locked=initial_autocompact_locked,
    )
    mode = "code"
    permission_state = initial_interactive_permission_state(
        permission_mode=initial_permission_mode,
        approval_policy=initial_approval,
        permission_overrides=initial_permission_overrides,
        allow_bypass=initial_bypass_permissions_available,
    )
    approval_policy = permission_state.approval_policy
    permission_overrides = permission_state.permission_overrides
    safe_mode = initial_safe_mode
    bare_mode = initial_bare_mode
    brief = initial_brief
    disable_slash_commands = initial_disable_slash_commands
    verbose = initial_verbose
    ax_screen_reader = initial_ax_screen_reader
    browser_mode = initial_browser_mode
    setting_sources = initial_setting_sources
    settings_override_json = initial_settings_override_json
    invocation_plugin_dirs = initial_invocation_plugin_dirs
    invocation_anthropic_betas = normalize_anthropic_betas(
        dict(initial_provider_env_overrides).get("ANTHROPIC_BETA")
    )
    debug_runtime = DebugRuntime(initial_debug_options)
    approval_handler = build_approval_handler(approval_policy)
    project_runtime = InteractiveProjectRuntime(
        Path.cwd(),
        approval_policy,
        initial_session_id=initial_resume_run_id,
        safe_mode=safe_mode,
        bare_mode=bare_mode,
        setting_sources=setting_sources,
        settings_override_json=settings_override_json,
        invocation_plugin_dirs=invocation_plugin_dirs,
    )
    chat_history: list[ChatMessage] = []
    conversation_messages: list[ChatMessage] = list(initial_conversation_messages)
    resume_run_id: str | None = initial_resume_run_id
    resume_context: str | None = initial_resume_context
    system_prompt = initial_system_prompt
    append_system_prompt = initial_append_system_prompt
    additional_directories = initial_additional_directories
    pending_workspace = initial_pending_workspace
    pending_branch_source_run_id = initial_branch_source_run_id
    goal_state: GoalState | None = None
    workflow_client_lock = Lock()
    idle_notification = IdleNotificationTimer()
    recap_enabled = automatic_session_recaps_enabled()
    recap_states = {
        "code": SessionRecapState(automatic_enabled=recap_enabled),
        "chat": SessionRecapState(automatic_enabled=recap_enabled),
    }
    file_changed_runtime = None
    config_change_runtime = None
    if initial_resume_run_id is not None:
        restored_goal = read_session_goal(Path.cwd(), initial_resume_run_id)
        goal_state = reset_restored_goal(restored_goal) if restored_goal is not None else None

    def current_provider_env() -> dict[str, str | None]:
        return interactive_provider_env(
            Path.cwd(),
            model_override,
            setting_sources=setting_sources,
            settings_override_json=settings_override_json,
            provider_env_overrides=initial_provider_env_overrides,
        )

    def create_interactive_client(provider_env: dict[str, str | None]) -> ChatClient:
        return configure_interactive_effort(
            cast(ChatClient, create_chat_client_func(provider_env)),
            effort_override,
            locked=effort_locked,
        )

    def run_code_task(task: str, task_metadata: dict[str, object] | None = None) -> tuple[object, str | None]:
        nonlocal client, resume_run_id, resume_context, pending_workspace
        nonlocal pending_branch_source_run_id, conversation_messages
        nonlocal approval_policy, approval_handler, permission_state, permission_overrides
        turn = run_interactive_code_turn(
            InteractiveCodeTurnRequest(
                project_root=Path.cwd(),
                task=task,
                task_metadata=task_metadata,
                client=client,
                resume_run_id=resume_run_id,
                resume_context=resume_context,
                pending_workspace=pending_workspace,
                pending_branch_source_run_id=pending_branch_source_run_id,
                conversation_messages=tuple(conversation_messages),
                approval_policy=approval_policy,
                approval_handler=approval_handler,
                permission_state=permission_state,
                permission_overrides=permission_overrides,
                project_permissions_trusted=project_permissions_trusted,
                project_runtime=project_runtime,
                additional_directories=additional_directories,
                system_prompt=system_prompt,
                append_system_prompt=append_system_prompt,
                agent=initial_agent,
                dynamic_agent_profiles=initial_dynamic_agent_profiles,
                teammate_mode=initial_teammate_mode,
                autocompact_tokens=autocompact_setting.tokens,
                safe_mode=safe_mode,
                bare_mode=bare_mode,
                brief=brief,
                disable_slash_commands=disable_slash_commands,
                verbose=verbose,
                screen_reader=ax_screen_reader,
                browser_mode=browser_mode,
                setting_sources=setting_sources,
                settings_override_json=settings_override_json,
                invocation_plugin_dirs=invocation_plugin_dirs,
                debug_runtime=debug_runtime,
            ),
            InteractiveCodeTurnServices(
                create_client=lambda: create_interactive_client(current_provider_env()),
                run_agent=run_agent_func,
                get_resume_context=get_resume_context_func,
                resolve_execution_config=resolve_execution_config,
                collect_directory_context=collect_directory_added_turn_context,
                print_agent_result=print_agent_result,
                prompt_user_input=prompt_user_input,
            ),
        )
        client = turn.client
        resume_run_id = turn.resume_run_id
        resume_context = turn.resume_context
        pending_workspace = turn.pending_workspace
        pending_branch_source_run_id = None
        conversation_messages = list(turn.conversation_messages)
        approval_policy = turn.approval_policy
        approval_handler = turn.approval_handler
        permission_state = turn.permission_state
        permission_overrides = turn.permission_overrides
        if getattr(turn.agent_result, "success", False):
            recap_states["code"].record_turn()
        return turn.agent_result, turn.next_context

    def run_goal(steering_task: str | None = None) -> None:
        nonlocal goal_state
        while goal_state is not None and goal_state.status == "active":
            result, next_context = run_code_task(
                goal_turn_prompt(goal_state, steering_task),
                {"source": "goal", "condition": goal_state.condition},
            )
            steering_task = None
            write_goal(create_local_workspace(Path.cwd(), result.run_id), goal_state)
            if not getattr(result, "success", False):
                print("Goal remains active because the agent turn failed.")
                return
            execution_config = resolve_execution_config(Path.cwd())
            goal_state, evaluation = evaluate_and_store_goal(
                goal_state,
                result,  # type: ignore[arg-type]
                next_context,
                client=client,
                execution_config=execution_config,
                project_root=Path.cwd(),
                agent_tokens=summarize_run_usage(Path.cwd(), result.run_id).total_tokens,
            )
            print(f"Goal evaluator: {evaluation.reason}")
            if evaluation.achieved:
                print("Goal achieved.")
                return

    def reset_recap_state(selected_mode: Literal["code", "chat"]) -> None:
        recap_states[selected_mode] = SessionRecapState(automatic_enabled=recap_enabled)

    def maybe_generate_automatic_recap() -> None:
        selected_mode: Literal["code", "chat"] = "code" if mode == "code" else "chat"
        history = conversation_messages if selected_mode == "code" else chat_history
        if not history or not recap_states[selected_mode].automatic_due():
            return
        recap = attempt_automatic_session_recap(
            recap_states[selected_mode],
            history=history,
            provider_env=current_provider_env(),
            create_chat_client=create_interactive_client,
            run_recap=run_recap_func,
            execution_config=resolve_execution_config(Path.cwd()),
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
        )
        if recap is not None:
            print(f"\nSession recap: {recap}")

    def run_due_tasks_while_idle() -> None:
        run_interactive_idle_tasks(
            InteractiveIdleContext(
                project_root=Path.cwd(),
                project_runtime=project_runtime,
                file_changed_runtime=file_changed_runtime,
                config_change_runtime=config_change_runtime,
                idle_notification=idle_notification,
                current_resume_run_id=lambda: resume_run_id,
                current_pending_workspace=lambda: pending_workspace,
                additional_directories=additional_directories,
                safe_mode=safe_mode,
                bare_mode=bare_mode,
                disable_slash_commands=disable_slash_commands,
                setting_sources=setting_sources,
                settings_override_json=settings_override_json,
                invocation_plugin_dirs=invocation_plugin_dirs,
                current_approval_handler=lambda: approval_handler,
                current_approval_policy=lambda: approval_policy,
                command_timeout_ms=lambda: resolve_execution_config(
                    Path.cwd()
                ).command_timeout_ms,
                scheduled_tasks_enabled=scheduled_tasks_enabled,
                run_notification_hooks=run_interactive_notification_hooks,
                run_code_task=run_code_task,
                maybe_generate_automatic_recap=maybe_generate_automatic_recap,
            )
        )

    def get_workflow_manager() -> DynamicWorkflowManager:
        nonlocal client, resume_run_id
        if project_runtime.workflow is not None:
            return project_runtime.workflow
        workspace = pending_workspace or (
            create_local_workspace(
                Path.cwd(),
                resume_run_id,
                additional_roots=additional_directories,
                safe_mode=safe_mode,
                bare_mode=bare_mode,
                setting_sources=setting_sources,
                settings_override_json=settings_override_json,
                invocation_plugin_dirs=invocation_plugin_dirs,
            )
            if resume_run_id is not None
            else create_run_workspace(
                Path.cwd(),
                additional_roots=additional_directories,
                safe_mode=safe_mode,
                bare_mode=bare_mode,
                setting_sources=setting_sources,
                settings_override_json=settings_override_json,
                invocation_plugin_dirs=invocation_plugin_dirs,
            )
        )
        if initial_dynamic_agent_profiles:
            workspace = replace(
                workspace,
                dynamic_agent_profiles=initial_dynamic_agent_profiles,
            )
        resume_run_id = workspace.run_id
        hooks = read_project_hooks(workspace)
        permissions = read_project_permissions(workspace)
        if workspace.project_config_trusted and permissions.enabled:
            permissions = replace(permissions, allow_rules_trusted=True)

        def execute_agent(request, cancel_requested):
            nonlocal client
            with workflow_client_lock:
                client = client or create_interactive_client(current_provider_env())
            return execute_workflow_agent_request(
                workspace,
                request,
                client,
                execution_config=resolve_execution_config(Path.cwd()),
                approval_handler=background_workflow_approval_handler(approval_policy, approval_handler),
                approval_policy=approval_policy,
                hooks=hooks,
                permissions=permissions,
                cancel_requested=cancel_requested,
            )

        return project_runtime.set_workflow(
            DynamicWorkflowManager(workspace, execute_agent)
        )

    def run_active_session_hook(
        event: Literal["session_end", "pre_compact", "post_compact"],
        value: str,
        summary: str | None = None,
    ) -> str | None:
        if safe_mode:
            return None
        try:
            return run_interactive_session_hook(
                Path.cwd(),
                resume_run_id,
                pending_workspace,
                additional_directories,
                event,
                value,
                summary=summary,
                command_timeout_ms=resolve_execution_config(
                    Path.cwd()
                ).command_timeout_ms,
                approval_handler=approval_handler,
                approval_policy=approval_policy,
            )
        except Exception as error:
            print(f"Lifecycle hook warning: {format_error(error)}")
            return None

    while True:
        try:
            idle_notification = IdleNotificationTimer()
            file_changed_runtime = None
            config_change_runtime = None
            if resume_run_id is not None and not safe_mode:
                try:
                    execution_config = resolve_execution_config(Path.cwd())
                    file_changed_runtime = create_interactive_file_changed_runtime(
                        Path.cwd(),
                        resume_run_id,
                        pending_workspace,
                        additional_directories,
                        command_timeout_ms=execution_config.command_timeout_ms,
                        approval_handler=approval_handler,
                        approval_policy=approval_policy,
                    )
                    config_change_runtime = create_interactive_config_change_runtime(
                        Path.cwd(),
                        resume_run_id,
                        pending_workspace,
                        additional_directories,
                        command_timeout_ms=execution_config.command_timeout_ms,
                        approval_handler=approval_handler,
                        approval_policy=approval_policy,
                    )
                except Exception as error:
                    print(f"Runtime change hook warning: {format_error(error)}")
            with interactive_prompt_completion(Path.cwd(), additional_directories):
                task = input_with_idle_callback(
                    interactive_session_prompt(Path.cwd(), resume_run_id, pending_workspace),
                    run_due_tasks_while_idle,
                    input_func=input,
                ).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            run_active_session_hook("session_end", "prompt_input_exit")
            project_runtime.close(additional_directories)
            return 0

        if not task:
            continue

        shell_task_metadata: dict[str, object] | None = None
        shell_command = parse_shell_mode_input(task)
        if shell_command is not None:
            if not shell_command:
                print(SHELL_MODE_USAGE)
                continue
            try:
                shell_settings_workspace = pending_workspace or create_local_workspace(
                    Path.cwd(),
                    resume_run_id or "interactive-shell-settings",
                    additional_roots=additional_directories,
                    safe_mode=safe_mode,
                    bare_mode=bare_mode,
                    setting_sources=setting_sources,
                    settings_override_json=settings_override_json,
                    invocation_plugin_dirs=invocation_plugin_dirs,
                )
                respond_to_shell = resolve_respond_to_bash_commands(
                    shell_settings_workspace
                )
                execution_config = resolve_execution_config(Path.cwd())
                shell_result = run_interactive_shell(
                    Path.cwd(),
                    shell_command,
                    run_id=resume_run_id,
                    timeout_ms=execution_config.command_timeout_ms,
                )
                print(shell_result.text)
                resume_run_id = shell_result.run_id
                selected, next_context, _ = get_resume_context_func(shell_result.run_id)
                if selected is not None:
                    resume_run_id = selected
                if next_context:
                    resume_context = next_context
            except KeyboardInterrupt:
                print("\nInterrupted.")
                continue
            except Exception as error:
                print(f"Shell error: {format_error(error)}")
                continue
            if not respond_to_shell:
                continue
            task = (
                "Review the interactive shell command and its recorded output in "
                "the prior session context. Respond with the appropriate next "
                "coding action or explanation. Do not rerun the command unless needed."
            )
            shell_task_metadata = {"source": "interactive_shell"}

        if disable_slash_commands and task.strip().startswith("/"):
            print("Slash commands and skills are disabled by --disable-slash-commands.")
            continue
        command = parse_local_command(task)
        custom_command: dict[str, object] | None = None
        if command is None and task.startswith("/"):
            if safe_mode:
                print("Custom commands and skill invocations are disabled by safe mode.")
                continue
            try:
                custom_command = expand_code_task_project_command(
                    Path.cwd(),
                    task,
                    workspace=pending_workspace or create_local_workspace(
                        Path.cwd(),
                        resume_run_id or "plugin-command-expansion",
                        additional_roots=additional_directories,
                        safe_mode=safe_mode,
                        bare_mode=bare_mode,
                        setting_sources=setting_sources,
                        settings_override_json=settings_override_json,
                        invocation_plugin_dirs=invocation_plugin_dirs,
                    ),
                )
            except ValueError as error:
                print(str(error))
                continue
            if custom_command is not None:
                task = str(custom_command["prompt"])
        if command and command.type == "exit":
            run_active_session_hook("session_end", "prompt_input_exit")
            project_runtime.close(additional_directories)
            return 0
        if command and command.type == "background":
            if mode != "code":
                print("/bg is available in coding mode only.")
                continue
            if resume_run_id is None:
                print("/bg requires an active coding session. Run a coding task first.")
                continue
            run_active_session_hook("session_end", "background")
            project_runtime.close(additional_directories)
            raise create_interactive_background_request(
                Path.cwd(),
                resume_run_id,
                command.argument,
                approval_policy=approval_policy,
                model=model_override,
                agent=initial_agent,
                dynamic_agent_profiles=initial_dynamic_agent_profiles,
                effort=effort_override,
                autocompact_tokens=autocompact_setting.tokens,
                memory_limit_bytes=initial_background_memory_limit_bytes,
                system_prompt=system_prompt,
                append_system_prompt=append_system_prompt,
                additional_directories=additional_directories,
                safe_mode=safe_mode,
                bare_mode=bare_mode,
                setting_sources=setting_sources,
                settings_override_json=settings_override_json,
                anthropic_betas=invocation_anthropic_betas,
                invocation_plugin_dirs=invocation_plugin_dirs,
                verbose=verbose,
                ax_screen_reader=ax_screen_reader,
                browser_mode=browser_mode,
                bypass_permissions_available=permission_state.bypass_available,
                attached_agent_id=initial_attached_background_agent_id,
            )
        if command and command.type in {"model", "effort", "btw", "recap"}:
            update = run_interactive_provider_command(
                command.type,
                command.argument,
                project_root=Path.cwd(),
                current_override=model_override,
                current_effort=effort_override,
                effort_locked=effort_locked,
                current_client=client,
                create_chat_client=create_chat_client_func,
                run_btw=run_btw_func,
                run_recap=run_recap_func,
                history=conversation_messages if mode == "code" else chat_history,
                system_prompt=system_prompt,
                append_system_prompt=append_system_prompt,
                setting_sources=setting_sources,
                settings_override_json=settings_override_json,
                provider_env_overrides=initial_provider_env_overrides,
            )
            if update.model_changed or update.effort_changed:
                with workflow_client_lock:
                    client = update.client
            else:
                client = update.client
            if update.model_changed:
                model_override = update.model_override
            if update.effort_changed:
                effort_override = update.effort_override
            if command.type == "recap" and update.provider_succeeded:
                recap_states[mode].record_attempt()
                recap_states[mode].record_success()
            print(update.text)
            continue
        if command and command.type == "autocompact":
            settings_workspace = pending_workspace or create_local_workspace(
                Path.cwd(),
                resume_run_id or "interactive-autocompact",
                safe_mode=safe_mode,
                bare_mode=bare_mode,
                setting_sources=setting_sources,
                settings_override_json=settings_override_json,
            )
            try:
                update = run_autocompact_command(
                    settings_workspace,
                    command.argument,
                    current=autocompact_setting,
                )
            except ValueError as error:
                print(str(error))
                continue
            autocompact_setting = update.setting
            print(update.text)
            continue
        project_command_namespace = command_namespace
        if command and (invocation_plugin_dirs or bare_mode) and command.type in {"custom_commands", "agents", "skills"}:
            catalog_workspace = pending_workspace or create_local_workspace(
                Path.cwd(),
                resume_run_id or "plugin-catalog",
                additional_roots=additional_directories,
                safe_mode=safe_mode,
                bare_mode=bare_mode,
                setting_sources=setting_sources,
                settings_override_json=settings_override_json,
                invocation_plugin_dirs=invocation_plugin_dirs,
            )
            if initial_dynamic_agent_profiles:
                catalog_workspace = replace(
                    catalog_workspace,
                    dynamic_agent_profiles=initial_dynamic_agent_profiles,
                )
            project_command_namespace = dict(command_namespace)
            project_command_namespace["get_custom_commands_text"] = lambda: format_project_prompt_commands(
                Path.cwd(), workspace=catalog_workspace
            )
            project_command_namespace["get_agents_text"] = lambda max_agents=20: (
                format_project_agent_catalog(catalog_workspace, max_agents=max_agents)
                or "No project agent profiles found."
            )
            project_command_namespace["get_skills_text"] = lambda max_skills=20: (
                format_project_skill_catalog(catalog_workspace, max_skills=max_skills)
                or "No project skills found."
            )
        if command and (
            local_text := dispatch_interactive_local_command(
                command,
                command_namespace,
                InteractiveLocalCommandContext(
                    project_root=Path.cwd(),
                    mode=mode,
                    approval_policy=approval_policy,
                    resume_run_id=resume_run_id,
                    resume_context=resume_context,
                    chat_turns=len(chat_history) // 2,
                    effort=effort_override or "auto",
                    autocompact=format_autocompact_setting(
                        autocompact_setting.tokens
                    ),
                    system_prompt_set=bool(system_prompt),
                    append_system_prompt_set=bool(append_system_prompt),
                    permission_mode=permission_state.mode,
                    safe_mode=safe_mode,
                ),
                project_command_namespace=project_command_namespace,
            )
        ) is not None:
            print(local_text)
            continue
        if command and command.type == "clear":
            run_active_session_hook("session_end", "clear")
            if goal_state is not None and resume_run_id is not None:
                goal_state = clear_goal(goal_state)
                write_goal(create_local_workspace(Path.cwd(), resume_run_id), goal_state)
            goal_state = None
            chat_history.clear()
            resume_run_id = None
            resume_context = None
            conversation_messages.clear()
            reset_recap_state("code")
            reset_recap_state("chat")
            pending_workspace = None
            pending_branch_source_run_id = None
            print("Cleared chat history and resume context.")
            continue
        if command and command.type == "goal":
            argument = command.argument
            if argument is None:
                print(format_goal_status(goal_state))
                continue
            if argument.strip().lower() in {"clear", "stop", "off", "reset", "none", "cancel"}:
                if goal_state is not None and resume_run_id is not None:
                    goal_state = clear_goal(goal_state)
                    write_goal(create_local_workspace(Path.cwd(), resume_run_id), goal_state)
                goal_state = None
                print("Goal cleared.")
                continue
            goal_state = new_goal(argument)
            try:
                run_goal()
            except KeyboardInterrupt:
                print("\nInterrupted. Goal remains active.")
            except Exception as error:
                print(f"\nGoal error: {format_error(error)}")
            continue
        if command and command.type == "workflows":
            if safe_mode:
                print("Custom workflows are disabled by safe mode.")
                continue
            print(handle_workflows_command(get_workflow_manager(), command.argument))
            continue
        if command and command.type == "plugin":
            if safe_mode:
                print("Plugins are disabled by safe mode.")
                continue
            plugin_result = handle_plugin_command(Path.cwd(), command.argument)
            if plugin_result.changed:
                project_runtime.close_workflow()
            if plugin_result.changed:
                from .lsp_runtime import close_project_lsp

                close_project_lsp(Path.cwd())
                project_runtime.start_plugin_updates()
            print(plugin_result.text)
            continue
        if command and command.type == "mcp":
            if safe_mode:
                print("MCP servers are disabled by safe mode.")
                continue
            print(handle_mcp_command(Path.cwd(), command.argument).text)
            continue
        if command and command.type == "reload_plugins":
            if safe_mode:
                print("Plugins are disabled by safe mode.")
                continue
            project_runtime.close_workflow()
            from .lsp_runtime import close_project_lsp

            close_project_lsp(Path.cwd())
            plugin_workspace = pending_workspace or create_local_workspace(
                Path.cwd(),
                resume_run_id or "plugin-reload",
                additional_roots=additional_directories,
                safe_mode=safe_mode,
                bare_mode=bare_mode,
                setting_sources=setting_sources,
                settings_override_json=settings_override_json,
                invocation_plugin_dirs=invocation_plugin_dirs,
            )
            print(reload_plugins_text(Path.cwd(), workspace=plugin_workspace))
            continue
        if command and command.type == "list_agents_local":
            print(get_peer_sessions_text())
            continue
        if command and command.type == "peer_inbox":
            print(handle_peer_inbox_command(project_runtime.peer, command.argument))
            continue
        if command and command.type == "system_prompt":
            system_prompt, text = update_system_prompt_state(system_prompt, command.argument, label="System prompt")
            print(text)
            continue
        if command and command.type == "append_system_prompt":
            append_system_prompt, text = update_system_prompt_state(
                append_system_prompt,
                command.argument,
                label="Appended system prompt",
            )
            print(text)
            continue
        if command and command.type == "add_dir":
            directory_update = apply_interactive_add_directory(
                InteractiveAddDirectoryRequest(
                    project_root=Path.cwd(),
                    argument=command.argument,
                    additional_directories=additional_directories,
                    pending_workspace=pending_workspace,
                    resume_run_id=resume_run_id,
                    project_runtime=project_runtime,
                    approval_policy=approval_policy,
                    approval_handler=approval_handler,
                    safe_mode=safe_mode,
                    bare_mode=bare_mode,
                    setting_sources=setting_sources,
                    settings_override_json=settings_override_json,
                    invocation_plugin_dirs=invocation_plugin_dirs,
                )
            )
            additional_directories = directory_update.additional_directories
            pending_workspace = directory_update.pending_workspace
            for message in directory_update.messages:
                print(message)
            continue
        if command and command.type == "cd":
            directory_switch = switch_interactive_directory(
                InteractiveDirectorySwitchRequest(
                    project_root=Path.cwd(),
                    argument=command.argument,
                    additional_directories=additional_directories,
                    pending_workspace=pending_workspace,
                    pending_branch_source_run_id=pending_branch_source_run_id,
                    resume_run_id=resume_run_id,
                    project_permissions_trusted=project_permissions_trusted,
                    project_runtime=project_runtime,
                    goal_state=goal_state,
                    approval_policy=approval_policy,
                    safe_mode=safe_mode,
                    bare_mode=bare_mode,
                    setting_sources=setting_sources,
                    settings_override_json=settings_override_json,
                    invocation_plugin_dirs=invocation_plugin_dirs,
                ),
                run_session_end_hook=lambda: run_active_session_hook(
                    "session_end",
                    "other",
                ),
                prompt_project_permission_trust=prompt_project_permission_trust,
            )
            project_runtime = directory_switch.project_runtime
            project_permissions_trusted = directory_switch.project_permissions_trusted
            additional_directories = directory_switch.additional_directories
            pending_workspace = directory_switch.pending_workspace
            pending_branch_source_run_id = directory_switch.pending_branch_source_run_id
            resume_run_id = directory_switch.resume_run_id
            if directory_switch.changed:
                client = None
                file_changed_runtime = None
                config_change_runtime = None
            for message in directory_switch.messages:
                print(message)
            continue
        if command and command.type == "approval":
            previous_state = permission_state
            permission_state, text = update_interactive_permission_state(
                permission_state,
                command.argument,
            )
            approval_policy = permission_state.approval_policy
            permission_overrides = permission_state.permission_overrides
            if approval_policy != previous_state.approval_policy:
                approval_handler = build_approval_handler(approval_policy)
                project_runtime.update_approval_policy(approval_policy)
            print(text)
            continue
        if command:
            navigation = navigate_interactive_session(
                InteractiveSessionNavigationRequest(
                    project_root=Path.cwd(),
                    command=command,
                    command_namespace=command_namespace,
                    state=InteractiveSessionNavigationState(
                        resume_run_id=resume_run_id,
                        resume_context=resume_context,
                        pending_workspace=pending_workspace,
                        pending_branch_source_run_id=pending_branch_source_run_id,
                        additional_directories=additional_directories,
                        conversation_messages=tuple(conversation_messages),
                        goal_state=goal_state,
                    ),
                    project_runtime=project_runtime,
                    safe_mode=safe_mode,
                    bare_mode=bare_mode,
                    disable_slash_commands=disable_slash_commands,
                    setting_sources=setting_sources,
                    settings_override_json=settings_override_json,
                    invocation_plugin_dirs=invocation_plugin_dirs,
                ),
                get_resume_context=get_resume_context_func,
                run_lifecycle_hook=lambda event, value, summary: run_active_session_hook(
                    event,
                    value,
                    summary,
                ),
            )
            if navigation.handled:
                resume_run_id = navigation.state.resume_run_id
                resume_context = navigation.state.resume_context
                pending_workspace = navigation.state.pending_workspace
                pending_branch_source_run_id = (
                    navigation.state.pending_branch_source_run_id
                )
                additional_directories = navigation.state.additional_directories
                conversation_messages = list(navigation.state.conversation_messages)
                goal_state = navigation.state.goal_state
                if navigation.reset_code_recap:
                    reset_recap_state("code")
                for message in navigation.messages:
                    print(message)
                continue
        try:
            builtin_workflow = resolve_builtin_model_workflow(command)
        except ValueError as error:
            print(str(error))
            continue
        if builtin_workflow is not None:
            task = builtin_workflow.task
        request_mode = (
            "code"
            if shell_task_metadata is not None
            or custom_command is not None
            or builtin_workflow is not None
            else mode
        )
        if command and command.type == "chat":
            if not command.argument:
                mode = "chat"
                print("Chat mode. Use /code to switch back to coding mode.")
                continue
            task = command.argument
            request_mode = "chat"
        elif command and command.type == "code":
            if not command.argument:
                mode = "code"
                print("Coding mode. Use /chat to switch to daily conversation mode.")
                continue
            task = command.argument
            request_mode = "code"

        try:
            # Reuse client across turns so auth/model config is loaded once.
            execution_config = resolve_execution_config(Path.cwd())
            client = client or create_interactive_client(current_provider_env())
            if request_mode == "chat":
                debug_runtime.emit("api", "chat_request", {"inputChars": len(task)})
                with terminal_model_stream_scope(client) as stream_renderer:
                    try:
                        response = run_chat_func(
                            task,
                            client=client,
                            history=chat_history,
                            max_output_tokens=execution_config.max_output_tokens,
                            model_retries=execution_config.model_retries,
                            model_retry_delay_ms=execution_config.model_retry_delay_ms,
                            model_timeout_ms=execution_config.model_timeout_ms,
                            system_prompt=system_prompt,
                            append_system_prompt=append_system_prompt,
                            **(
                                {"model_stream_handler": stream_renderer.chat_event}
                                if stream_renderer is not None
                                else {}
                            ),
                        )
                    except Exception as error:
                        debug_runtime.emit(
                            "api",
                            "chat_error",
                            {"type": type(error).__name__, "message": format_error(error)},
                        )
                        raise
                debug_runtime.emit("api", "chat_response", {"outputChars": len(response)})
                chat_history.extend(
                    [
                        ChatMessage(role="user", content=task),
                        ChatMessage(role="assistant", content=response),
                    ]
                )
                recap_states["chat"].record_turn()
                if stream_renderer is None or not stream_renderer.matches_final_message(response):
                    print(f"\n{response}")
                continue

            if goal_state is not None and goal_state.status == "active":
                run_goal(task)
            else:
                run_code_task(
                    task,
                    (
                        shell_task_metadata
                        if shell_task_metadata is not None
                        else project_command_task_metadata(custom_command)
                        if custom_command is not None
                        else builtin_workflow.metadata if builtin_workflow is not None else None
                    ),
                )
        except KeyboardInterrupt:
            print("\nInterrupted.")
        except Exception as error:
            print(f"\nError: {format_error(error)}")
