from __future__ import annotations

import argparse
from contextlib import nullcontext
from pathlib import Path
from time import monotonic

from .agent import run_agent
from .chat import run_chat
from .cli_context import build_context_limit_kwargs, resolve_one_shot_prior_context
from .cli_config import build_provider_env, resolve_project_root
from .cli_mcp_args import resolve_mcp_config_paths
from .cli_machine_output import add_duration_fields
from .cli_one_shot_input import (
    build_one_shot_kwargs_from_args,
    combine_optional_text,
    resolve_task_input,
    resolve_task_text,
)
from .cli_output import (
    build_approval_handler,
    format_error,
    print_agent_result,
    print_error_result,
    print_interrupted_result,
    print_output,
    prompt_user_input,
)
from .cli_result_payloads import (
    build_chat_result_payload,
    build_code_result_payload,
    error_result_payload,
)
from .cli_stream_output import JsonEventStream
from .commands import get_compact_context, get_resume_context, parse_local_command
from .config import resolve_cost_rates, resolve_execution_config
from .providers import create_chat_client
from .project_trust import is_project_permissions_trusted
from .session_event_observers import observe_session_events
from .session_usage import build_run_cost_report, build_run_usage_report
from .types import ApprovalPolicy
from .workspace_core import create_run_workspace
from .workspace_prompt_commands import expand_project_prompt_command


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
    effective_output_format = output_format or ("json" if output_json else "text")
    stream_json = effective_output_format == "stream-json"
    machine_output = effective_output_format in {"json", "stream-json"}
    stream = JsonEventStream() if stream_json else None

    def emit_error(error: str, *, kind: str = "error", status: str = "failed", exit_code: int = 1) -> int:
        payload_exit_code = exit_code if machine_output else None
        payload = error_result_payload(error, kind=kind, status=status, exit_code=payload_exit_code)
        if machine_output:
            add_duration_fields(payload, elapsed_milliseconds(started_at))
        if stream is not None:
            stream.result(payload)
            return exit_code
        if output_json:
            print_output(payload, True)
            return exit_code
        return print_error_result(error, output_json, exit_code=exit_code)

    try:
        if not task.strip():
            return emit_error("No task provided.")
        project_root = resolve_project_root(base_dir) or Path.cwd()
        task_metadata: dict[str, object] | None = None
        if request_mode == "code":
            try:
                task, task_metadata = expand_one_shot_project_command(project_root, task)
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
            payload = build_chat_result_payload(response)
            if machine_output:
                add_duration_fields(payload, elapsed_milliseconds(started_at))
                payload["numTurns"] = 1
                payload["num_turns"] = 1
            if stream is not None:
                stream.result(payload)
            else:
                print_output(payload, output_json)
            return 0

        resume_kwargs = build_context_limit_kwargs(
            max_failures=resume_max_failures,
            max_files=resume_max_files,
            max_commands=resume_max_commands,
            max_checks=resume_max_checks,
            max_output_chars=resume_max_output_chars,
            max_text=resume_max_text,
        )
        compact_kwargs = build_context_limit_kwargs(
            max_failures=compact_max_failures,
            max_files=compact_max_files,
            max_commands=compact_max_commands,
            max_checks=compact_max_checks,
            max_output_chars=compact_max_output_chars,
            max_text=compact_max_text,
        )
        prior_context = resolve_one_shot_prior_context(
            resume_arg=resume_arg,
            compact_arg=compact_arg,
            auto_compact=auto_compact,
            project_root=project_root,
            resume_kwargs=resume_kwargs,
            compact_kwargs=compact_kwargs,
            get_resume_context_func=get_resume_context_func,
            get_compact_context_func=get_compact_context_func,
        )
        if prior_context.error is not None:
            return emit_error(prior_context.error)
        merged_prior_context = combine_optional_text(prior_context.context, input_prior_context)
        client = create_chat_client_func(provider_env)
        stream_workspace = (
            create_run_workspace(
                project_root,
                mcp_config_paths=resolved_mcp_config_paths,
                strict_mcp_config=strict_mcp_config,
            )
            if stream is not None
            else None
        )
        event_scope = (
            observe_session_events(stream_workspace.session_dir, stream.session_event)
            if stream is not None and stream_workspace is not None
            else nullcontext()
        )
        run_kwargs = {
            "client": client,
            "base_dir": project_root,
            "max_iterations": execution_config.max_iterations,
            "command_timeout_ms": execution_config.command_timeout_ms,
            "max_output_tokens": execution_config.max_output_tokens,
            "model_retries": execution_config.model_retries,
            "model_retry_delay_ms": execution_config.model_retry_delay_ms,
            "model_timeout_ms": execution_config.model_timeout_ms,
            "approval_handler": None if stream_json and approval_policy == "ask" else build_approval_handler(approval_policy),
            "approval_policy": approval_policy,
            "trust_project_permissions": trust_project_permissions or is_project_permissions_trusted(project_root),
            "permission_overrides": permission_overrides,
            "mcp_config_paths": resolved_mcp_config_paths,
            "strict_mcp_config": strict_mcp_config,
            "user_input_handler": None if machine_output else prompt_user_input,
            "prior_context": merged_prior_context,
            "system_prompt": system_prompt,
            "append_system_prompt": append_system_prompt,
            "task_metadata": task_metadata,
        }
        if stream_workspace is not None:
            run_kwargs["workspace"] = stream_workspace
        with event_scope:
            result = run_agent_func(task, **run_kwargs)
        result_payload = build_code_result_payload(result, prior_context)
        if machine_output:
            add_duration_fields(result_payload, elapsed_milliseconds(started_at))
            result_payload["usage"] = build_run_usage_report(project_root, result.run_id)
            cost_rates, cost_errors = resolve_cost_rates(provider_env)
            result_payload["cost"] = build_run_cost_report(project_root, result.run_id, cost_rates, cost_errors)
        if stream is not None:
            stream.result(result_payload)
        elif output_json:
            print_output(result_payload, True)
        elif print_mode:
            print_output({"message": result.message}, False)
        else:
            print_agent_result(result)
        return 0 if result.success and result.completion_ready else 1
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


def expand_one_shot_project_command(project_root: Path, task: str) -> tuple[str, dict[str, object] | None]:
    stripped = task.strip()
    if not stripped.startswith("/") or parse_local_command(stripped) is not None:
        return task, None
    custom_command = expand_project_prompt_command(project_root, stripped)
    if custom_command is None:
        return task, None
    metadata = {
        "source": "project_command",
        "name": custom_command["name"],
        "path": custom_command["path"],
        "arguments": custom_command["arguments"],
    }
    return str(custom_command["prompt"]), metadata
