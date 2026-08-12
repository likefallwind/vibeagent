from __future__ import annotations

import argparse
from contextlib import nullcontext
from decimal import Decimal
from pathlib import Path
from time import monotonic

from .agent import run_agent
from .chat import run_chat
from .cli_config import resolve_project_root
from .cli_ephemeral_session import ephemeral_session_scope
from .cli_one_shot_chat import run_one_shot_chat
from .cli_one_shot_code import run_one_shot_code
from .cli_one_shot_input import (
    build_one_shot_kwargs_from_args,
    resolve_task_input,
    resolve_task_text,
)
from .cli_one_shot_output import emit_one_shot_error
from .cli_one_shot_setup import resolve_one_shot_project_setup, resolve_one_shot_runtime_setup
from .cli_output import (
    format_error,
    print_error_result,
    print_interrupted_result,
)
from .cli_output_mode import resolve_cli_output_mode
from .cli_stream_output import JsonEventStream
from .commands import get_compact_context, get_resume_context
from .providers import create_chat_client
from .types import ApprovalPolicy
from .dynamic_agent_profiles import DynamicAgentProfile
from .background_agent_config import BackgroundAgentConfig


def run_one_shot(
    task: str,
    request_mode: str,
    approval_policy: ApprovalPolicy,
    agent: str | None = None,
    dynamic_agent_profiles: tuple[DynamicAgentProfile, ...] = (),
    session_name: str | None = None,
    trust_project_permissions: bool = False,
    resume_arg: str | None = None,
    compact_arg: str | None = None,
    resume_max_failures: int | None = None,
    resume_max_files: int | None = None,
    resume_max_commands: int | None = None,
    resume_max_checks: int | None = None,
    resume_max_output_chars: int | None = None,
    resume_max_text: int | None = None,
    auto_compact: bool = True,
    fork_session: bool = False,
    compact_max_failures: int | None = None,
    compact_max_files: int | None = None,
    compact_max_commands: int | None = None,
    compact_max_checks: int | None = None,
    compact_max_output_chars: int | None = None,
    compact_max_text: int | None = None,
    base_dir: str | None = None,
    additional_directories: tuple[Path, ...] = (),
    max_iterations: int | None = None,
    command_timeout_ms: int | None = None,
    max_output_tokens: int | None = None,
    model_retries: int | None = None,
    model_retry_delay_ms: int | None = None,
    model_timeout_ms: int | None = None,
    mcp_config_paths: list[str] | tuple[str, ...] | None = None,
    strict_mcp_config: bool = False,
    safe_mode: bool = False,
    system_prompt: str | None = None,
    append_system_prompt: str | None = None,
    append_subagent_system_prompt: str | None = None,
    input_prior_context: str | None = None,
    output_json: bool = False,
    output_format: str | None = None,
    print_mode: bool = False,
    session_persistence: bool = True,
    structured_output_schema: dict[str, object] | None = None,
    max_budget_usd: Decimal | None = None,
    fallback_model: str | None = None,
    include_partial_messages: bool = False,
    forward_subagent_text: bool = False,
    replay_user_messages: bool = False,
    input_user_messages: tuple[str, ...] = (),
    effort: str | None = None,
    effort_locked: bool = False,
    autocompact_tokens: int | None = None,
    setup_trigger: str | None = None,
    tool_names: frozenset[str] | None = None,
    permission_overrides=None,
    provider_args: argparse.Namespace | None = None,
    background_agent_config: BackgroundAgentConfig | None = None,
    create_chat_client_func=create_chat_client,
    run_chat_func=run_chat,
    run_agent_func=run_agent,
    get_resume_context_func=get_resume_context,
    get_compact_context_func=get_compact_context,
) -> int:
    started_at = monotonic()
    output_mode = resolve_cli_output_mode(output_json, output_format)
    stream = JsonEventStream() if output_mode.stream_json else None

    def emit_error(error: str, *, kind: str = "error", status: str = "failed", exit_code: int = 1) -> int:
        return emit_one_shot_error(
            error,
            stream=stream,
            output_json=output_json,
            machine_output=output_mode.machine,
            elapsed_ms=elapsed_milliseconds(started_at),
            kind=kind,
            status=status,
            exit_code=exit_code,
        )

    try:
        if not task.strip():
            return emit_error("No task provided.")
        if replay_user_messages and (stream is None or request_mode != "code"):
            return emit_error("User message replay requires stream-json coding output.", exit_code=2)
        project_root = resolve_project_root(base_dir) or Path.cwd()
        try:
            project_setup = resolve_one_shot_project_setup(
                task,
                request_mode=request_mode,
                project_root=project_root,
                mcp_config_paths=mcp_config_paths,
                safe_mode=safe_mode,
            )
        except ValueError as error:
            return emit_error(str(error), exit_code=2)
        task = project_setup.task
        task_metadata = project_setup.task_metadata
        resolved_mcp_config_paths = project_setup.mcp_config_paths
        runtime_setup = resolve_one_shot_runtime_setup(
            config_root=project_root,
            provider_args=provider_args,
            max_iterations=max_iterations,
            command_timeout_ms=command_timeout_ms,
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
            trust_project_settings=trust_project_permissions,
        )
        execution_config = runtime_setup.execution_config
        provider_env = runtime_setup.provider_env
        if request_mode == "chat":
            return run_one_shot_chat(
                task,
                provider_env=provider_env,
                execution_config=execution_config,
                system_prompt=system_prompt,
                append_system_prompt=append_system_prompt,
                machine_output=output_mode.machine,
                output_json=output_json,
                elapsed_ms=elapsed_milliseconds(started_at),
                stream=stream,
                effort=effort,
                effort_locked=effort_locked,
                include_partial_messages=include_partial_messages,
                create_chat_client_func=create_chat_client_func,
                run_chat_func=run_chat_func,
            )

        session_scope = (
            nullcontext(None)
            if session_persistence or request_mode == "chat"
            else ephemeral_session_scope(
                project_root,
                mcp_config_paths=resolved_mcp_config_paths,
                strict_mcp_config=strict_mcp_config,
                additional_roots=additional_directories,
                safe_mode=safe_mode,
            )
        )
        with session_scope as ephemeral:
            exit_code, prior_context = run_one_shot_code(
                task,
                project_root=project_root,
                execution_config=execution_config,
                provider_env=provider_env,
                approval_policy=approval_policy,
                agent=agent,
                dynamic_agent_profiles=dynamic_agent_profiles,
                session_name=session_name,
                trust_project_permissions=trust_project_permissions,
                permission_overrides=permission_overrides,
                resolved_mcp_config_paths=resolved_mcp_config_paths,
                strict_mcp_config=strict_mcp_config,
                safe_mode=safe_mode,
                output_mode=output_mode,
                output_json=output_json,
                print_mode=print_mode,
                structured_output_schema=structured_output_schema,
                max_budget_usd=max_budget_usd,
                fallback_model=fallback_model,
                include_partial_messages=include_partial_messages,
                forward_subagent_text=forward_subagent_text,
                replay_user_messages=replay_user_messages,
                input_user_messages=input_user_messages,
                effort=effort,
                effort_locked=effort_locked,
                autocompact_tokens=autocompact_tokens,
                setup_trigger=setup_trigger,
                tool_names=tool_names,
                elapsed_ms=elapsed_milliseconds(started_at),
                stream=stream,
                input_prior_context=input_prior_context,
                system_prompt=system_prompt,
                append_system_prompt=append_system_prompt,
                append_subagent_system_prompt=append_subagent_system_prompt,
                additional_directories=additional_directories,
                task_metadata=task_metadata,
                resume_arg=resume_arg,
                compact_arg=compact_arg,
                auto_compact=auto_compact,
                fork_session=fork_session,
                resume_max_failures=resume_max_failures,
                resume_max_files=resume_max_files,
                resume_max_commands=resume_max_commands,
                resume_max_checks=resume_max_checks,
                resume_max_output_chars=resume_max_output_chars,
                resume_max_text=resume_max_text,
                compact_max_failures=compact_max_failures,
                compact_max_files=compact_max_files,
                compact_max_commands=compact_max_commands,
                compact_max_checks=compact_max_checks,
                compact_max_output_chars=compact_max_output_chars,
                compact_max_text=compact_max_text,
                ephemeral_workspace=ephemeral.workspace if ephemeral is not None else None,
                session_record_root=ephemeral.record_root if ephemeral is not None else None,
                create_chat_client_func=create_chat_client_func,
                run_agent_func=run_agent_func,
                background_agent_config=background_agent_config,
                get_resume_context_func=get_resume_context_func,
                get_compact_context_func=get_compact_context_func,
            )
        if prior_context.error is not None:
            return emit_error(prior_context.error)
        return exit_code
    except KeyboardInterrupt:
        if stream is not None:
            return emit_error("Interrupted.", kind="interrupted", status="interrupted", exit_code=130)
        return print_interrupted_result(output_json)
    except Exception as error:
        if stream is not None:
            return emit_error(format_error(error))
        return print_error_result(format_error(error), output_json, prefix=True)


def elapsed_milliseconds(started_at: float) -> int:
    return max(0, round((monotonic() - started_at) * 1000))
