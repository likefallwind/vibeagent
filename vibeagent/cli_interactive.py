from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .agent import run_agent as default_run_agent
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
from .cli_project_local_flags import run_interactive_project_command, run_interactive_project_state_command
from .cli_read_local_flags import run_interactive_read_command
from .cli_review_local_flags import run_interactive_review_command
from .cli_runtime_local_flags import run_interactive_runtime_command
from .cli_session_local_flags import run_interactive_resume_command, run_interactive_session_command
from .cli_text_edit_local_flags import run_interactive_text_edit_command
from .commands import get_resume_context as default_get_resume_context, parse_local_command
from .config import resolve_execution_config
from .providers import create_chat_client as default_create_chat_client
from .types import ApprovalPolicy, ChatMessage
from .workspace_prompt_commands import expand_project_prompt_command


def run_interactive_loop(
    *,
    command_namespace: dict[str, Any],
    create_chat_client_func: Callable[..., object] = default_create_chat_client,
    run_chat_func: Callable[..., str] = default_run_chat,
    run_agent_func: Callable[..., object] = default_run_agent,
    get_resume_context_func: Callable[..., tuple[str | None, str | None, str]] = default_get_resume_context,
) -> int:
    # Entry loop: parse local commands first, otherwise delegate to the agent.
    print("VibeAgent v0.1")
    print("Type a programming task, or use /chat for daily conversation. Use /help for commands.")
    project_permissions_trusted = prompt_project_permission_trust(Path.cwd())

    client = None
    mode = "code"
    approval_policy: ApprovalPolicy = "ask"
    approval_handler = build_approval_handler(approval_policy)
    chat_history: list[ChatMessage] = []
    resume_run_id: str | None = None
    resume_context: str | None = None
    while True:
        try:
            task = input("\nvibeagent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not task:
            continue

        command = parse_local_command(task)
        custom_command: dict[str, object] | None = None
        if command is None and task.startswith("/"):
            try:
                custom_command = expand_project_prompt_command(Path.cwd(), task)
            except ValueError as error:
                print(str(error))
                continue
            if custom_command is not None:
                task = str(custom_command["prompt"])
        if command and command.type == "exit":
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
            )
        ) is not None:
            print(state_text)
            continue
        if command and (review_text := run_interactive_review_command(command, command_namespace)) is not None:
            print(review_text)
            continue
        if command and command.type == "clear":
            chat_history.clear()
            resume_run_id = None
            resume_context = None
            print("Cleared chat history and resume context.")
            continue
        if command and command.type == "approval":
            previous_policy = approval_policy
            approval_policy, text = handle_approval_command(command.argument, approval_policy)
            if approval_policy != previous_policy:
                approval_handler = build_approval_handler(approval_policy)
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
                )
                chat_history.extend(
                    [
                        ChatMessage(role="user", content=task),
                        ChatMessage(role="assistant", content=response),
                    ]
                )
                print(f"\n{response}")
                continue

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
                task_metadata=(
                    {
                        "source": "project_command",
                        "name": custom_command["name"],
                        "path": custom_command["path"],
                        "arguments": custom_command["arguments"],
                    }
                    if custom_command is not None
                    else None
                ),
            )
            print_agent_result(result)
            selected, next_context, _ = get_resume_context_func(result.run_id)
            if next_context:
                resume_run_id = selected
                resume_context = next_context
        except KeyboardInterrupt:
            print("\nInterrupted.")
        except Exception as error:
            print(f"\nError: {format_error(error)}")
