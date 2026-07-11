from __future__ import annotations

import argparse
from collections.abc import Sequence
from contextlib import nullcontext
from pathlib import Path
import sys

from .agent import run_agent
from .chat import run_chat
from .cli_context import build_context_limit_kwargs, resolve_one_shot_prior_context
from .cli_config import build_provider_env, resolve_project_root
from .cli_output import (
    build_approval_handler,
    format_error,
    print_agent_result,
    print_error_result,
    print_interrupted_result,
    print_output,
    prompt_user_input,
)
from .cli_permission_overrides import build_permission_overrides
from .cli_stream_output import JsonEventStream, build_code_result_payload, error_result_payload
from .commands import get_compact_context, get_resume_context
from .config import resolve_execution_config
from .providers import create_chat_client
from .project_trust import is_project_permissions_trusted
from .session_event_observers import observe_session_events
from .types import ApprovalPolicy
from .workspace_core import create_run_workspace


def resolve_task_text(parts: Sequence[str]) -> str:
    if len(parts) == 1 and parts[0] == "-":
        return sys.stdin.read().strip()
    return " ".join(parts)


def build_one_shot_kwargs_from_args(args: argparse.Namespace) -> dict[str, object]:
    return {
        "task": resolve_task_text(args.task),
        "request_mode": "chat" if args.chat else "code",
        "approval_policy": args.approval,
        "trust_project_permissions": args.trust_project_permissions,
        "resume_arg": args.resume,
        "compact_arg": args.compact,
        "resume_max_failures": args.resume_max_failures,
        "resume_max_files": args.resume_max_files,
        "resume_max_commands": args.resume_max_commands,
        "resume_max_checks": args.resume_max_checks,
        "resume_max_output_chars": args.resume_max_output_chars,
        "resume_max_text": args.resume_max_text,
        "compact_max_failures": args.compact_max_failures,
        "compact_max_files": args.compact_max_files,
        "compact_max_commands": args.compact_max_commands,
        "compact_max_checks": args.compact_max_checks,
        "compact_max_output_chars": args.compact_max_output_chars,
        "compact_max_text": args.compact_max_text,
        "base_dir": args.cwd,
        "max_iterations": args.max_iterations,
        "command_timeout_ms": args.command_timeout_ms,
        "max_output_tokens": args.max_output_tokens,
        "model_retries": args.model_retries,
        "model_retry_delay_ms": args.model_retry_delay_ms,
        "model_timeout_ms": args.model_timeout_ms,
        "output_json": args.json,
        "output_format": args.output_format,
        "permission_overrides": build_permission_overrides(args),
        "provider_args": args,
    }


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
    output_json: bool = False,
    output_format: str | None = None,
    permission_overrides=None,
    provider_args: argparse.Namespace | None = None,
    create_chat_client_func=create_chat_client,
    run_chat_func=run_chat,
    run_agent_func=run_agent,
    get_resume_context_func=get_resume_context,
    get_compact_context_func=get_compact_context,
) -> int:
    effective_output_format = output_format or ("json" if output_json else "text")
    stream_json = effective_output_format == "stream-json"
    machine_output = effective_output_format in {"json", "stream-json"}
    stream = JsonEventStream() if stream_json else None

    def emit_error(error: str, *, kind: str = "error", status: str = "failed", exit_code: int = 1) -> int:
        if stream is not None:
            stream.result(error_result_payload(error, kind=kind, status=status))
            return exit_code
        return print_error_result(error, output_json, exit_code=exit_code)

    try:
        if not task.strip():
            return emit_error("No task provided.")
        project_root = resolve_project_root(base_dir) or Path.cwd()
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
            )
            payload = {"kind": "chat", "success": True, "status": "completed", "message": response}
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
            project_root=project_root,
            resume_kwargs=resume_kwargs,
            compact_kwargs=compact_kwargs,
            get_resume_context_func=get_resume_context_func,
            get_compact_context_func=get_compact_context_func,
        )
        if prior_context.error is not None:
            return emit_error(prior_context.error)
        client = create_chat_client_func(provider_env)
        stream_workspace = create_run_workspace(project_root) if stream is not None else None
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
            "user_input_handler": None if machine_output else prompt_user_input,
            "prior_context": prior_context.context,
        }
        if stream_workspace is not None:
            run_kwargs["workspace"] = stream_workspace
        with event_scope:
            result = run_agent_func(task, **run_kwargs)
        result_payload = build_code_result_payload(result, prior_context)
        if stream is not None:
            stream.result(result_payload)
        elif output_json:
            print_output(result_payload, True)
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
