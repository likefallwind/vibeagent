from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from threading import Lock
from typing import Any

from .agent import run_agent as default_run_agent
from .agent_runtime_utils import append_session_event
from .chat import run_chat as default_run_chat
from .cli_checkpoint_local_flags import run_interactive_checkpoint_command
from .cli_code_intel_local_flags import run_interactive_code_intel_command
from .cli_command_local_flags import run_interactive_command_execution
from .cli_config import build_provider_env
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
from .cli_patch_local_flags import run_interactive_patch_command
from .cli_project_command_expansion import (
    expand_code_task_project_command,
    project_command_task_metadata,
)
from .cli_project_local_flags import run_interactive_project_command, run_interactive_project_state_command
from .cli_interactive_read_commands import run_interactive_read_command
from .cli_idle_input import input_with_idle_callback
from .cli_review_local_flags import run_interactive_review_command
from .cli_runtime_local_flags import run_interactive_runtime_command
from .cli_session_local_flags import run_interactive_resume_command, run_interactive_session_command
from .cli_system_prompt_state import update_system_prompt_state
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
from .providers import create_chat_client as default_create_chat_client
from .types import ApprovalPolicy, ChatMessage
from .scheduled_task_store import collect_due_scheduled_tasks, scheduled_tasks_enabled
from .session_usage import summarize_run_usage
from .agent_peer_notifications import peer_messages_as_task
from .peer_runtime import create_peer_runtime
from .peer_commands import get_peer_sessions_text
from .peer_inbox_commands import handle_peer_inbox_command
from .plugin_commands import handle_plugin_command, reload_plugins_text
from .dynamic_workflow_agent import background_workflow_approval_handler, execute_workflow_agent_request
from .dynamic_workflow_commands import handle_workflows_command
from .dynamic_workflow_runtime import DynamicWorkflowManager
from .workspace_core import create_local_workspace, create_run_workspace
from .workspace_hooks import read_project_hooks
from .workspace_permissions import read_project_permissions


def run_interactive_loop(
    *,
    command_namespace: dict[str, Any],
    create_chat_client_func: Callable[..., object] = default_create_chat_client,
    run_chat_func: Callable[..., str] = default_run_chat,
    run_agent_func: Callable[..., object] = default_run_agent,
    get_resume_context_func: Callable[..., tuple[str | None, str | None, str]] = default_get_resume_context,
    initial_resume_run_id: str | None = None,
    initial_resume_context: str | None = None,
    initial_resume_message: str | None = None,
) -> int:
    # Entry loop: parse local commands first, otherwise delegate to the agent.
    print("VibeAgent v0.1")
    print("Type a programming task, or use /chat for daily conversation. Use /help for commands.")
    if initial_resume_message:
        print(initial_resume_message)
    project_permissions_trusted = prompt_project_permission_trust(Path.cwd())

    client = None
    mode = "code"
    approval_policy: ApprovalPolicy = "ask"
    approval_handler = build_approval_handler(approval_policy)
    peer_runtime = create_peer_runtime(Path.cwd(), approval_policy)
    chat_history: list[ChatMessage] = []
    resume_run_id: str | None = initial_resume_run_id
    resume_context: str | None = initial_resume_context
    system_prompt: str | None = None
    append_system_prompt: str | None = None
    goal_state: GoalState | None = None
    workflow_manager: DynamicWorkflowManager | None = None
    workflow_client_lock = Lock()
    if initial_resume_run_id is not None:
        restored_goal = read_session_goal(Path.cwd(), initial_resume_run_id)
        goal_state = reset_restored_goal(restored_goal) if restored_goal is not None else None

    def run_code_task(task: str, task_metadata: dict[str, object] | None = None) -> tuple[object, str | None]:
        nonlocal client, resume_run_id, resume_context
        execution_config = resolve_execution_config(Path.cwd())
        client = client or create_chat_client_func(build_provider_env(None, Path.cwd()))
        result = run_agent_func(
            task,
            client=client,
            max_iterations=execution_config.max_iterations,
            command_timeout_ms=execution_config.command_timeout_ms,
            max_output_tokens=execution_config.max_output_tokens,
            model_retries=execution_config.model_retries,
            model_retry_delay_ms=execution_config.model_retry_delay_ms,
            model_timeout_ms=execution_config.model_timeout_ms,
            approval_handler=approval_handler,
            approval_policy=approval_policy,
            trust_project_permissions=project_permissions_trusted,
            user_input_handler=prompt_user_input,
            prior_context=resume_context,
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
            task_metadata=task_metadata,
            task_source_run_id=resume_run_id,
            peer_runtime=peer_runtime,
        )
        print_agent_result(result)
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

    def run_due_tasks_while_idle() -> None:
        try:
            if peer_runtime is not None:
                peer_task = peer_messages_as_task(peer_runtime)
                if peer_task is not None:
                    task, metadata = peer_task
                    print("\nPeer session message received.")
                    run_code_task(task, metadata)
            if resume_run_id is None or not scheduled_tasks_enabled():
                return
            workspace = create_local_workspace(Path.cwd(), resume_run_id)
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
        except KeyboardInterrupt:
            raise
        except Exception as error:
            print(f"\nIdle task error: {format_error(error)}")

    def get_workflow_manager() -> DynamicWorkflowManager:
        nonlocal client, resume_run_id, workflow_manager
        if workflow_manager is not None:
            return workflow_manager
        workspace = (
            create_local_workspace(Path.cwd(), resume_run_id)
            if resume_run_id is not None
            else create_run_workspace(Path.cwd())
        )
        resume_run_id = workspace.run_id
        hooks = read_project_hooks(workspace)
        permissions = read_project_permissions(workspace)
        if workspace.project_config_trusted and permissions.enabled:
            permissions = replace(permissions, allow_rules_trusted=True)

        def execute_agent(request, cancel_requested):
            nonlocal client
            with workflow_client_lock:
                client = client or create_chat_client_func(build_provider_env(None, Path.cwd()))
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

    while True:
        try:
            task = input_with_idle_callback(
                "\nvibeagent> ",
                run_due_tasks_while_idle,
                input_func=input,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            if workflow_manager is not None:
                workflow_manager.close()
            if peer_runtime is not None:
                peer_runtime.close()
            return 0

        if not task:
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
            if workflow_manager is not None:
                workflow_manager.close()
            if peer_runtime is not None:
                peer_runtime.close()
            return 0
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
            if goal_state is not None and resume_run_id is not None:
                goal_state = clear_goal(goal_state)
                write_goal(create_local_workspace(Path.cwd(), resume_run_id), goal_state)
            goal_state = None
            chat_history.clear()
            resume_run_id = None
            resume_context = None
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
            print(plugin_result.text)
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
        if command and command.type == "approval":
            previous_policy = approval_policy
            approval_policy, text = handle_approval_command(command.argument, approval_policy)
            if approval_policy != previous_policy:
                approval_handler = build_approval_handler(approval_policy)
                if peer_runtime is not None:
                    peer_runtime.update_approval_policy(approval_policy)
            print(text)
            continue
        if command and (session_text := run_interactive_session_command(command, command_namespace)) is not None:
            print(session_text)
            continue
        if command and (checkpoint_text := run_interactive_checkpoint_command(command, command_namespace)) is not None:
            print(checkpoint_text)
            continue
        if command and (resume_result := run_interactive_resume_command(command, command_namespace)) is not None:
            selected, context, text = resume_result
            resume_run_id = selected
            resume_context = context
            restored_goal = read_session_goal(Path.cwd(), selected) if selected is not None else None
            goal_state = reset_restored_goal(restored_goal) if restored_goal is not None else None
            print(text)
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
            client = client or create_chat_client_func(build_provider_env(None, Path.cwd()))
            if request_mode == "chat":
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
                )
                chat_history.extend(
                    [
                        ChatMessage(role="user", content=task),
                        ChatMessage(role="assistant", content=response),
                    ]
                )
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
