from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from threading import Lock
from typing import Any, Literal, cast

from . import __version__
from .agent import run_agent as default_run_agent
from .agent_runtime_utils import append_session_event
from .async_hook_runtime import (
    async_hook_notifications_prompt,
    close_session_async_hooks,
    collect_async_hook_notifications,
)
from .btw import run_btw as default_run_btw
from .chat import run_chat as default_run_chat
from .session_recap import (
    SessionRecapState,
    attempt_automatic_session_recap,
    automatic_session_recaps_enabled,
    run_session_recap as default_run_session_recap,
)
from .directory_added_hooks import (
    collect_directory_added_turn_context,
    schedule_directory_added_hooks,
)
from .cli_checkpoint_local_flags import run_interactive_checkpoint_command
from .cli_completion import interactive_prompt_completion
from .cli_code_intel_local_flags import run_interactive_code_intel_command
from .cli_command_local_flags import run_interactive_command_execution
from .cli_edit_local_flags import run_interactive_edit_command
from .cli_git_local_flags import run_interactive_git_command
from .cli_json_local_flags import run_interactive_json_command
from .cli_output import (
    build_approval_handler,
    format_error,
    handle_approval_command,
    print_agent_result,
    prompt_project_permission_trust,
    prompt_user_input,
)
from .cli_model_stream import terminal_model_stream_scope
from .cli_patch_local_flags import run_interactive_patch_command
from .cli_project_command_expansion import (
    expand_code_task_project_command,
    project_command_task_metadata,
)
from .cli_project_local_flags import run_interactive_project_command, run_interactive_project_state_command
from .cli_interactive_read_commands import run_interactive_read_command
from .cli_idle_input import input_with_idle_callback
from .cli_idle_notification import IdleNotificationTimer
from .cli_review_local_flags import run_interactive_review_command
from .cli_runtime_local_flags import run_interactive_runtime_command
from .cli_session_local_flags import run_interactive_resume_command, run_interactive_session_command
from .cli_system_prompt_state import update_system_prompt_state
from .cli_additional_directory_state import update_additional_directory_state
from .cli_interactive_branch import prepare_interactive_branch_switch
from .cli_interactive_model import interactive_provider_env
from .cli_interactive_effort import configure_interactive_effort
from .context_compaction import format_autocompact_setting
from .cli_interactive_provider_commands import run_interactive_provider_command
from .cli_interactive_rewind import run_interactive_rewind_command
from .cli_interactive_session_management import interactive_session_prompt, run_interactive_session_management
from .cli_subagent_panel import SubagentPanel
from .cli_text_edit_local_flags import run_interactive_text_edit_command
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
from .providers import create_chat_client as default_create_chat_client
from .types import ApprovalPolicy, ChatClient, ChatMessage
from .dynamic_agent_profiles import DynamicAgentProfile
from .scheduled_task_store import collect_due_scheduled_tasks, scheduled_tasks_enabled
from .session_usage import summarize_run_usage
from .session_names import transfer_session_name
from .agent_peer_notifications import peer_messages_as_task
from .peer_runtime import create_peer_runtime
from .peer_commands import get_peer_sessions_text
from .peer_inbox_commands import handle_peer_inbox_command
from .plugin_commands import handle_plugin_command, reload_plugins_text
from .mcp_commands import handle_mcp_command
from .plugin_auto_update import (
    PluginAutoUpdateRuntime,
    format_plugin_auto_update_notification,
)
from .dynamic_workflow_agent import background_workflow_approval_handler, execute_workflow_agent_request
from .dynamic_workflow_commands import handle_workflows_command
from .dynamic_workflow_runtime import DynamicWorkflowManager
from .workspace_core import create_local_workspace, create_run_workspace
from .monitor_runtime import (
    collect_monitor_notifications,
    monitor_notifications_prompt,
    stop_session_monitors,
)
from .workspace_hooks import read_project_hooks
from .workspace_permissions import read_project_permissions
from .session_additional_directories import (
    merge_additional_directories,
    record_session_additional_directories,
    restore_session_additional_directories,
)
from .session_conversation import load_session_conversation
from .session_lifecycle_hooks import (
    create_interactive_config_change_runtime,
    create_interactive_file_changed_runtime,
    run_interactive_notification_hooks,
    run_interactive_session_hook,
)
from .workspace_core import RunWorkspace


def run_interactive_loop(
    *,
    command_namespace: dict[str, Any],
    create_chat_client_func: Callable[..., object] = default_create_chat_client,
    run_chat_func: Callable[..., str] = default_run_chat,
    run_btw_func: Callable[..., str] = default_run_btw,
    run_recap_func: Callable[..., str] = default_run_session_recap,
    run_agent_func: Callable[..., object] = default_run_agent,
    get_resume_context_func: Callable[..., tuple[str | None, str | None, str]] = default_get_resume_context,
    initial_resume_run_id: str | None = None,
    initial_resume_context: str | None = None,
    initial_resume_message: str | None = None,
    initial_agent: str | None = None,
    initial_dynamic_agent_profiles: tuple[DynamicAgentProfile, ...] = (),
    initial_effort: str | None = None,
    initial_effort_locked: bool = False,
    initial_autocompact_tokens: int | None = None,
    initial_system_prompt: str | None = None,
    initial_append_system_prompt: str | None = None,
    initial_additional_directories: tuple[Path, ...] = (),
    initial_pending_workspace: RunWorkspace | None = None,
    initial_branch_source_run_id: str | None = None,
    initial_conversation_messages: tuple[ChatMessage, ...] = (),
) -> int:
    # Entry loop: parse local commands first, otherwise delegate to the agent.
    print(f"VibeAgent {__version__}")
    print("Type a programming task, or use /chat for daily conversation. Use /help for commands.")
    if initial_resume_message:
        print(initial_resume_message)
    project_permissions_trusted = prompt_project_permission_trust(Path.cwd())

    client = None
    model_override: str | None = None
    effort_override: str | None = initial_effort
    effort_locked = initial_effort_locked
    mode = "code"
    approval_policy: ApprovalPolicy = "ask"
    approval_handler = build_approval_handler(approval_policy)
    peer_runtime = create_peer_runtime(Path.cwd(), approval_policy)
    plugin_auto_updates = PluginAutoUpdateRuntime(Path.cwd())
    plugin_auto_updates.start()
    chat_history: list[ChatMessage] = []
    conversation_messages: list[ChatMessage] = list(initial_conversation_messages)
    resume_run_id: str | None = initial_resume_run_id
    owned_monitor_session_ids = {
        initial_resume_run_id
    } if initial_resume_run_id is not None else set()
    resume_context: str | None = initial_resume_context
    system_prompt = initial_system_prompt
    append_system_prompt = initial_append_system_prompt
    additional_directories = initial_additional_directories
    pending_workspace = initial_pending_workspace
    pending_branch_source_run_id = initial_branch_source_run_id
    goal_state: GoalState | None = None
    workflow_manager: DynamicWorkflowManager | None = None
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

    def create_interactive_client(provider_env: dict[str, str | None]) -> ChatClient:
        return configure_interactive_effort(
            cast(ChatClient, create_chat_client_func(provider_env)),
            effort_override,
            locked=effort_locked,
        )

    def run_code_task(task: str, task_metadata: dict[str, object] | None = None) -> tuple[object, str | None]:
        nonlocal client, resume_run_id, resume_context, pending_workspace, pending_branch_source_run_id
        nonlocal conversation_messages, approval_policy, approval_handler
        execution_config = resolve_execution_config(Path.cwd())
        notification_workspace = pending_workspace or create_local_workspace(
            Path.cwd(),
            resume_run_id or "pending-directory-hooks",
            additional_roots=additional_directories,
        )
        turn_append_system_prompt, directory_hook_errors = collect_directory_added_turn_context(
            notification_workspace,
            append_system_prompt,
        )
        for error in directory_hook_errors:
            print(f"DirectoryAdded hook warning: {error}")
        client = client or create_interactive_client(interactive_provider_env(Path.cwd(), model_override))
        panel = SubagentPanel(Path.cwd())
        panel.authorize_custom(approval_handler, approval_policy)
        initial_panel_error = panel.config_error
        if panel.config_error:
            print(f"Plugin subagentStatusLine warning: {panel.config_error}")
        panel_kwargs: dict[str, object] = {}
        selected_approval_handler = approval_handler
        selected_user_input_handler = prompt_user_input
        if panel.enabled:
            panel_kwargs = {
                "logger": panel.log,
                "workspace_observer": panel.bind,
            }
            selected_approval_handler = panel.wrap_approval_handler(approval_handler)
            selected_user_input_handler = panel.wrap_user_input_handler(prompt_user_input)
        source_run_id = resume_run_id
        active_workspace = pending_workspace
        try:
            with terminal_model_stream_scope(
                client,
                on_display_start=panel.pause,
                on_display_end=panel.resume,
            ) as stream_renderer:
                result = run_agent_func(
                    task,
                    client=client,
                    max_iterations=execution_config.max_iterations,
                    command_timeout_ms=execution_config.command_timeout_ms,
                    max_output_tokens=execution_config.max_output_tokens,
                    model_retries=execution_config.model_retries,
                    model_retry_delay_ms=execution_config.model_retry_delay_ms,
                    model_timeout_ms=execution_config.model_timeout_ms,
                    approval_handler=selected_approval_handler,
                    approval_policy=approval_policy,
                    trust_project_permissions=project_permissions_trusted,
                    user_input_handler=selected_user_input_handler,
                    prior_context=resume_context,
                    prior_messages=conversation_messages or None,
                    system_prompt=system_prompt,
                    append_system_prompt=turn_append_system_prompt,
                    task_metadata=task_metadata,
                    task_source_run_id=(
                        pending_branch_source_run_id
                        or (
                            resume_run_id
                            if active_workspace is None and resume_context is not None
                            else None
                        )
                    ),
                    workspace=active_workspace,
                    peer_runtime=peer_runtime,
                    agent=initial_agent,
                    dynamic_agent_profiles=initial_dynamic_agent_profiles,
                    additional_directories=additional_directories,
                    autocompact_tokens=initial_autocompact_tokens,
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
        print_agent_result(
            result,
            message_already_displayed=(
                stream_renderer.matches_final_message(result.displayed_message)
                if stream_renderer is not None
                else False
            ),
        )
        result_approval_policy = getattr(result, "approval_policy", None)
        if (
            result_approval_policy in {"ask", "allow", "auto", "deny", "dontAsk", "plan"}
            and result_approval_policy != approval_policy
        ):
            approval_policy = result_approval_policy
            approval_handler = build_approval_handler(approval_policy)
            if peer_runtime is not None:
                peer_runtime.update_approval_policy(approval_policy)
        conversation_messages = list(getattr(result, "conversation", []))
        if getattr(result, "success", False):
            recap_states["code"].record_turn()
        if active_workspace is None:
            try:
                transfer_session_name(Path.cwd(), source_run_id, result.run_id)
            except (OSError, ValueError) as error:
                print(f"Session name persistence warning: {format_error(error)}")
        pending_workspace = create_local_workspace(
            Path.cwd(),
            result.run_id,
            additional_roots=additional_directories,
        )
        owned_monitor_session_ids.add(result.run_id)
        pending_branch_source_run_id = None
        selected, next_context, _ = get_resume_context_func(result.run_id)
        if next_context:
            resume_run_id = selected
            resume_context = next_context
        return result, next_context

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
            provider_env=interactive_provider_env(Path.cwd(), model_override),
            create_chat_client=create_interactive_client,
            run_recap=run_recap_func,
            execution_config=resolve_execution_config(Path.cwd()),
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
        )
        if recap is not None:
            print(f"\nSession recap: {recap}")

    def run_due_tasks_while_idle() -> None:
        try:
            if file_changed_runtime is not None:
                changed = file_changed_runtime.poll(iteration=0)
                for message in changed.system_messages:
                    print(f"\n{message}")
            if config_change_runtime is not None:
                changed = config_change_runtime.poll(iteration=0)
                for message in changed.system_messages:
                    print(f"\n{message}")
            if idle_notification.due() and resume_run_id is not None:
                notification = run_interactive_notification_hooks(
                    Path.cwd(),
                    resume_run_id,
                    pending_workspace,
                    additional_directories,
                    "idle_prompt",
                    "VibeAgent is waiting for your input.",
                    title="VibeAgent is waiting",
                    command_timeout_ms=resolve_execution_config(
                        Path.cwd()
                    ).command_timeout_ms,
                    approval_handler=approval_handler,
                    approval_policy=approval_policy,
                )
                for message in notification.system_messages:
                    print(f"\n{message}")
            for notification in plugin_auto_updates.collect_notifications():
                print(f"\n{format_plugin_auto_update_notification(notification)}")
            if peer_runtime is not None:
                peer_task = peer_messages_as_task(peer_runtime)
                if peer_task is not None:
                    task, metadata = peer_task
                    print("\nPeer session message received.")
                    run_code_task(task, metadata)
            if resume_run_id is None:
                maybe_generate_automatic_recap()
                return
            workspace = create_local_workspace(
                Path.cwd(),
                resume_run_id,
                additional_roots=additional_directories,
            )
            async_hook_notifications = collect_async_hook_notifications(
                workspace,
                rewake_only=True,
            )
            if async_hook_notifications:
                print("\nAsynchronous hook requested attention.")
                run_code_task(
                    async_hook_notifications_prompt(async_hook_notifications),
                    {
                        "source": "async_hook_rewake",
                        "asyncHookProcessIds": [
                            item.process_id for item in async_hook_notifications
                        ],
                    },
                )
            monitor_notifications = collect_monitor_notifications(workspace)
            if monitor_notifications:
                print("\nMonitor event received.")
                run_code_task(
                    monitor_notifications_prompt(monitor_notifications),
                    {
                        "source": "monitor",
                        "monitorTaskIds": sorted(
                            {item.task_id for item in monitor_notifications}
                        ),
                    },
                )
            if not scheduled_tasks_enabled():
                maybe_generate_automatic_recap()
                return
            workspace = create_local_workspace(
                Path.cwd(),
                resume_run_id,
                additional_roots=additional_directories,
            )
            due = collect_due_scheduled_tasks(workspace)
            if due:
                append_session_event(
                    workspace.session_dir,
                    "scheduled_tasks_delivered",
                    {
                        "iteration": 0,
                        "count": len(due),
                        "task_ids": [scheduled.id for scheduled in due],
                        "idle": True,
                    },
                )
            for scheduled in due:
                print(f"\nScheduled task {scheduled.id}: {scheduled.prompt}")
                run_code_task(
                    scheduled.prompt,
                    {
                        "source": "scheduled_task",
                        "scheduledTaskId": scheduled.id,
                        "scheduledFor": scheduled.scheduled_for,
                    },
                )
            maybe_generate_automatic_recap()
        except KeyboardInterrupt:
            raise
        except Exception as error:
            print(f"\nIdle task error: {format_error(error)}")

    def get_workflow_manager() -> DynamicWorkflowManager:
        nonlocal client, resume_run_id, workflow_manager
        if workflow_manager is not None:
            return workflow_manager
        workspace = pending_workspace or (
            create_local_workspace(
                Path.cwd(),
                resume_run_id,
                additional_roots=additional_directories,
            )
            if resume_run_id is not None
            else create_run_workspace(Path.cwd(), additional_roots=additional_directories)
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
                client = client or create_interactive_client(interactive_provider_env(Path.cwd(), model_override))
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

        workflow_manager = DynamicWorkflowManager(workspace, execute_agent)
        return workflow_manager

    def stop_owned_background_runtime() -> None:
        for session_id in owned_monitor_session_ids:
            stop_session_monitors(Path.cwd(), session_id)
            close_session_async_hooks(
                create_local_workspace(
                    Path.cwd(),
                    session_id,
                    additional_roots=additional_directories,
                )
            )

    def run_active_session_hook(
        event: Literal["session_end", "pre_compact", "post_compact"],
        value: str,
        summary: str | None = None,
    ) -> None:
        try:
            run_interactive_session_hook(
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

    while True:
        try:
            idle_notification = IdleNotificationTimer()
            file_changed_runtime = None
            config_change_runtime = None
            if resume_run_id is not None:
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
            stop_owned_background_runtime()
            if workflow_manager is not None:
                workflow_manager.close()
            if peer_runtime is not None:
                peer_runtime.close()
            plugin_auto_updates.close()
            return 0

        if not task:
            continue

        shell_command = parse_shell_mode_input(task)
        if shell_command is not None:
            if not shell_command:
                print(SHELL_MODE_USAGE)
                continue
            try:
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
            except Exception as error:
                print(f"Shell error: {format_error(error)}")
            continue

        command = parse_local_command(task)
        custom_command: dict[str, object] | None = None
        if command is None and task.startswith("/"):
            try:
                custom_command = expand_code_task_project_command(Path.cwd(), task)
            except ValueError as error:
                print(str(error))
                continue
            if custom_command is not None:
                task = str(custom_command["prompt"])
        if command and command.type == "exit":
            run_active_session_hook("session_end", "prompt_input_exit")
            stop_owned_background_runtime()
            if workflow_manager is not None:
                workflow_manager.close()
            if peer_runtime is not None:
                peer_runtime.close()
            plugin_auto_updates.close()
            return 0
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
        if command and (
            project_text := run_interactive_project_command(command, command_namespace, approval_policy, Path.cwd())
        ) is not None:
            print(project_text)
            continue
        if command and (command_text := run_interactive_command_execution(command, command_namespace)) is not None:
            print(command_text)
            continue
        if command and (read_text := run_interactive_read_command(command, command_namespace)) is not None:
            print(read_text)
            continue
        if command and (code_intel_text := run_interactive_code_intel_command(command, command_namespace)) is not None:
            print(code_intel_text)
            continue
        if command and (json_text := run_interactive_json_command(command, command_namespace)) is not None:
            print(json_text)
            continue
        if command and (text_edit_text := run_interactive_text_edit_command(command, command_namespace)) is not None:
            print(text_edit_text)
            continue
        if command and (edit_text := run_interactive_edit_command(command, command_namespace)) is not None:
            print(edit_text)
            continue
        if command and (patch_text := run_interactive_patch_command(command, command_namespace)) is not None:
            print(patch_text)
            continue
        if command and (git_text := run_interactive_git_command(command, command_namespace)) is not None:
            print(git_text)
            continue
        if command and (runtime_text := run_interactive_runtime_command(command, command_namespace)) is not None:
            print(runtime_text)
            continue
        if command and (
            state_text := run_interactive_project_state_command(
                command,
                command_namespace,
                mode=mode,
                approval_policy=approval_policy,
                resume_run_id=resume_run_id,
                resume_context=resume_context,
                chat_turns=len(chat_history) // 2,
                effort=effort_override or "auto",
                autocompact=format_autocompact_setting(initial_autocompact_tokens),
                system_prompt_set=bool(system_prompt),
                append_system_prompt_set=bool(append_system_prompt),
            )
        ) is not None:
            print(state_text)
            continue
        if command and (review_text := run_interactive_review_command(command, command_namespace)) is not None:
            print(review_text)
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
            print(handle_workflows_command(get_workflow_manager(), command.argument))
            continue
        if command and command.type == "plugin":
            plugin_result = handle_plugin_command(Path.cwd(), command.argument)
            if plugin_result.changed and workflow_manager is not None:
                workflow_manager.close()
                workflow_manager = None
            if plugin_result.changed:
                from .lsp_runtime import close_project_lsp

                close_project_lsp(Path.cwd())
                plugin_auto_updates.start()
            print(plugin_result.text)
            continue
        if command and command.type == "mcp":
            print(handle_mcp_command(Path.cwd(), command.argument).text)
            continue
        if command and command.type == "reload_plugins":
            if workflow_manager is not None:
                workflow_manager.close()
                workflow_manager = None
            from .lsp_runtime import close_project_lsp

            close_project_lsp(Path.cwd())
            print(reload_plugins_text(Path.cwd()))
            continue
        if command and command.type == "list_agents_local":
            print(get_peer_sessions_text())
            continue
        if command and command.type == "peer_inbox":
            print(handle_peer_inbox_command(peer_runtime, command.argument))
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
            previous_directories = additional_directories
            update = update_additional_directory_state(
                additional_directories,
                command.argument,
                project_root=Path.cwd(),
            )
            if update.changed:
                additional_directories = update.directories
                if pending_workspace is not None:
                    pending_workspace = replace(
                        pending_workspace,
                        additional_roots=additional_directories,
                    )
                elif resume_run_id is not None:
                    pending_workspace = create_local_workspace(
                        Path.cwd(),
                        resume_run_id,
                        additional_roots=additional_directories,
                    )
                if workflow_manager is not None:
                    workflow_manager.close()
                    workflow_manager = None
                try:
                    record_session_additional_directories(
                        Path.cwd(),
                        resume_run_id,
                        additional_directories,
                    )
                except (OSError, ValueError) as error:
                    print(f"Additional directory persistence warning: {format_error(error)}")
                added = tuple(
                    directory
                    for directory in additional_directories
                    if directory not in previous_directories
                )
                if added:
                    try:
                        if pending_workspace is None:
                            pending_workspace = create_run_workspace(
                                Path.cwd(),
                                additional_roots=additional_directories,
                            )
                        hooks = read_project_hooks(pending_workspace)
                        permissions = read_project_permissions(pending_workspace)
                        if pending_workspace.project_config_trusted and permissions.enabled:
                            permissions = replace(permissions, allow_rules_trusted=True)
                        for directory in added:
                            schedule_directory_added_hooks(
                                pending_workspace,
                                directory,
                                "slash_command",
                                hooks=hooks,
                                permissions=permissions,
                                approval_policy=approval_policy,
                                approval_handler=approval_handler,
                            )
                    except (OSError, RuntimeError, ValueError) as error:
                        print(f"DirectoryAdded hook warning: {format_error(error)}")
            print(update.text)
            continue
        if command and command.type == "approval":
            previous_policy = approval_policy
            approval_policy, text = handle_approval_command(command.argument, approval_policy)
            if approval_policy != previous_policy:
                approval_handler = build_approval_handler(approval_policy)
                if peer_runtime is not None:
                    peer_runtime.update_approval_policy(approval_policy)
            print(text)
            continue
        if command and (
            session_update := run_interactive_session_management(
                command,
                project_root=Path.cwd(),
                run_id=resume_run_id,
                pending_workspace=pending_workspace,
            )
        ) is not None:
            resume_run_id = session_update.run_id
            pending_workspace = session_update.pending_workspace
            print(session_update.text)
            continue
        if command and (session_text := run_interactive_session_command(command, command_namespace)) is not None:
            print(session_text)
            continue
        if command and (
            rewind := run_interactive_rewind_command(
                command,
                project_root=Path.cwd(),
                run_id=resume_run_id,
                get_resume_context=get_resume_context_func,
            )
        ) is not None:
            if rewind.workspace is not None and rewind.context is not None:
                if workflow_manager is not None:
                    workflow_manager.close()
                    workflow_manager = None
                pending_workspace = rewind.workspace
                pending_branch_source_run_id = None
                resume_run_id = rewind.workspace.run_id
                resume_context = rewind.context
                additional_directories = rewind.workspace.additional_roots
                goal_state = None
                conversation_messages.clear()
                reset_recap_state("code")
            print(rewind.text)
            continue
        if command and (
            checkpoint_text := run_interactive_checkpoint_command(command, command_namespace, resume_run_id)
        ) is not None:
            print(checkpoint_text)
            continue
        if command and (
            resume_result := run_interactive_resume_command(
                command,
                command_namespace,
                before_compact=lambda: run_active_session_hook(
                    "pre_compact", "manual"
                ),
                after_compact=lambda summary: run_active_session_hook(
                    "post_compact", "manual", summary
                ),
            )
        ) is not None:
            selected, context, text = resume_result
            restored_directories = restore_session_additional_directories(Path.cwd(), selected)
            try:
                next_additional_directories = merge_additional_directories(
                    Path.cwd(),
                    additional_directories,
                    restored_directories.directories,
                )
            except ValueError as error:
                print(f"Resume error: {format_error(error)}")
                continue
            if workflow_manager is not None:
                workflow_manager.close()
                workflow_manager = None
            if command.type == "resume" and selected != resume_run_id:
                run_active_session_hook("session_end", "resume")
            resume_run_id = selected
            resume_context = context
            restored_conversation = (
                load_session_conversation(Path.cwd(), selected)
                if command.type == "resume"
                else None
            )
            conversation_messages = (
                list(restored_conversation.messages)
                if restored_conversation is not None
                else []
            )
            reset_recap_state("code")
            pending_workspace = (
                create_local_workspace(
                    Path.cwd(),
                    selected,
                    additional_roots=next_additional_directories,
                )
                if command.type == "resume" and selected is not None
                else None
            )
            pending_branch_source_run_id = None
            additional_directories = next_additional_directories
            restored_goal = read_session_goal(Path.cwd(), selected) if selected is not None else None
            goal_state = reset_restored_goal(restored_goal) if restored_goal is not None else None
            print(text)
            if restored_conversation is not None and restored_conversation.warning:
                print(restored_conversation.warning)
            if restored_directories.message:
                print(restored_directories.message)
            continue
        if command and command.type == "branch":
            branch = prepare_interactive_branch_switch(
                Path.cwd(),
                resume_run_id,
                command.argument,
                additional_directories,
                get_resume_context=get_resume_context_func,
            )
            if branch.error is not None or branch.workspace is None or branch.source_run_id is None:
                print(f"Branch error: {branch.error or 'branch state is incomplete.'}")
                continue
            if workflow_manager is not None:
                workflow_manager.close()
                workflow_manager = None
            run_active_session_hook("session_end", "resume")
            pending_workspace = branch.workspace
            pending_branch_source_run_id = branch.source_run_id
            resume_run_id = branch.workspace.run_id
            resume_context = branch.context
            restored_conversation = load_session_conversation(Path.cwd(), branch.source_run_id)
            conversation_messages = list(restored_conversation.messages)
            reset_recap_state("code")
            restored_goal = read_session_goal(Path.cwd(), resume_run_id)
            goal_state = reset_restored_goal(restored_goal) if restored_goal is not None else None
            print(branch.text)
            if restored_conversation.warning:
                print(restored_conversation.warning)
            continue
        request_mode = "code" if custom_command is not None else mode
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
            client = client or create_interactive_client(interactive_provider_env(Path.cwd(), model_override))
            if request_mode == "chat":
                with terminal_model_stream_scope(client) as stream_renderer:
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
                    project_command_task_metadata(custom_command)
                    if custom_command is not None
                    else None,
                )
        except KeyboardInterrupt:
            print("\nInterrupted.")
        except Exception as error:
            print(f"\nError: {format_error(error)}")
