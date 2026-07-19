from __future__ import annotations

import argparse
from pathlib import Path
from time import monotonic

from .agent import run_agent
from .chat import run_chat
from .cli_config import build_provider_env, resolve_project_root
from .cli_mcp_args import resolve_mcp_config_paths
from .cli_one_shot_agent_kwargs import build_one_shot_agent_kwargs
from .cli_one_shot_input import (
    build_one_shot_kwargs_from_args,
    combine_optional_text,
    resolve_one_shot_code_task,
    resolve_one_shot_context_from_limits,
    resolve_task_input,
    resolve_task_text,
)
from .cli_one_shot_output import (
    build_one_shot_chat_payload,
    build_one_shot_code_payload,
    emit_one_shot_error,
    emit_one_shot_chat_payload,
    emit_one_shot_code_payload,
    one_shot_code_exit_code,
)
from .cli_one_shot_stream import build_one_shot_stream_scope
from .cli_output import (
    format_error,
    print_error_result,
    print_interrupted_result,
)
from .cli_output_mode import resolve_cli_output_mode
from .cli_stream_output import JsonEventStream
from .commands import get_compact_context, get_resume_context
from .config import resolve_execution_config
from .providers import create_chat_client
from .types import ApprovalPolicy


def run_one_shot(
    task: str,
    request_mode: str,
    approval_policy: ApprovalPolicy,
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
    compact_max_failures: int | None = None,
    compact_max_files: int | None = None,
    compact_max_commands: int | None = None,
    compact_max_checks: int | None = None,
    compact_max_output_chars: int | None = None,
    compact_max_text: int | None = None,
    base_dir: str | None = None,
    max_iterations: int | None = None,
    command_timeout_ms: int | None = None,
    max_output_tokens: int | None = None,
    model_retries: int | None = None,
    model_retry_delay_ms: int | None = None,
    model_timeout_ms: int | None = None,
    mcp_config_paths: list[str] | tuple[str, ...] | None = None,
    strict_mcp_config: bool = False,
    system_prompt: str | None = None,
    append_system_prompt: str | None = None,
    input_prior_context: str | None = None,
    output_json: bool = False,
    output_format: str | None = None,
    print_mode: bool = False,
    permission_overrides=None,
    provider_args: argparse.Namespace | None = None,
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
        project_root = resolve_project_root(base_dir) or Path.cwd()
        try:
            task, task_metadata = resolve_one_shot_code_task(
                task,
                request_mode=request_mode,
                project_root=project_root,
            )
        except ValueError as error:
            return emit_error(str(error), exit_code=2)
        try:
            resolved_mcp_config_paths = resolve_mcp_config_paths(project_root, mcp_config_paths)
        except ValueError as error:
            return emit_error(str(error), exit_code=2)
        config_root = project_root
        execution_config = resolve_execution_config(
            config_root,
            max_iterations=max_iterations,
            command_timeout_ms=command_timeout_ms,
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
        )
        provider_env = build_provider_env(provider_args, config_root)
        if request_mode == "chat":
            client = create_chat_client_func(provider_env)
            response = run_chat_func(
                task,
                client=client,
                history=[],
                max_output_tokens=execution_config.max_output_tokens,
                model_retries=execution_config.model_retries,
                model_retry_delay_ms=execution_config.model_retry_delay_ms,
                model_timeout_ms=execution_config.model_timeout_ms,
                system_prompt=system_prompt,
                append_system_prompt=append_system_prompt,
            )
            payload = build_one_shot_chat_payload(
                response,
                machine_output=output_mode.machine,
                elapsed_ms=elapsed_milliseconds(started_at),
            )
            emit_one_shot_chat_payload(payload, stream=stream, output_json=output_json)
            return 0

        prior_context = resolve_one_shot_context_from_limits(
            resume_arg=resume_arg,
            compact_arg=compact_arg,
            auto_compact=auto_compact,
            project_root=project_root,
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
            get_resume_context_func=get_resume_context_func,
            get_compact_context_func=get_compact_context_func,
        )
        if prior_context.error is not None:
            return emit_error(prior_context.error)
        merged_prior_context = combine_optional_text(prior_context.context, input_prior_context)
        client = create_chat_client_func(provider_env)
        stream_scope = build_one_shot_stream_scope(
            stream,
            project_root=project_root,
            mcp_config_paths=resolved_mcp_config_paths,
            strict_mcp_config=strict_mcp_config,
        )
        run_kwargs = build_one_shot_agent_kwargs(
            client=client,
            project_root=project_root,
            execution_config=execution_config,
            approval_policy=approval_policy,
            trust_project_permissions=trust_project_permissions,
            permission_overrides=permission_overrides,
            mcp_config_paths=resolved_mcp_config_paths,
            strict_mcp_config=strict_mcp_config,
            machine_output=output_mode.machine,
            stream_json=output_mode.stream_json,
            prior_context=merged_prior_context,
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
            task_metadata=task_metadata,
            workspace=stream_scope.workspace,
        )
        with stream_scope.event_scope:
            result = run_agent_func(task, **run_kwargs)
        result_payload = build_one_shot_code_payload(
            result,
            prior_context,
            machine_output=output_mode.machine,
            elapsed_ms=elapsed_milliseconds(started_at),
            project_root=project_root,
            provider_env=provider_env,
        )
        emit_one_shot_code_payload(
            result,
            result_payload,
            stream=stream,
            output_json=output_json,
            print_mode=print_mode,
        )
        return one_shot_code_exit_code(result)
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
