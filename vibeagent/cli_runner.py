from __future__ import annotations

import argparse
from collections.abc import Sequence
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
from .commands import get_compact_context, get_resume_context
from .config import resolve_execution_config
from .providers import create_chat_client
from .types import ApprovalPolicy


def resolve_task_text(parts: Sequence[str]) -> str:
    if len(parts) == 1 and parts[0] == "-":
        return sys.stdin.read().strip()
    return " ".join(parts)


def build_one_shot_kwargs_from_args(args: argparse.Namespace) -> dict[str, object]:
    return {
        "task": resolve_task_text(args.task),
        "request_mode": "chat" if args.chat else "code",
        "approval_policy": args.approval,
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
        "provider_args": args,
    }


def run_one_shot(
    task: str,
    request_mode: str,
    approval_policy: ApprovalPolicy,
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
    provider_args: argparse.Namespace | None = None,
    create_chat_client_func=create_chat_client,
    run_chat_func=run_chat,
    run_agent_func=run_agent,
    get_resume_context_func=get_resume_context,
    get_compact_context_func=get_compact_context,
) -> int:
    try:
        if not task.strip():
            return print_error_result("No task provided.", output_json)
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
            print_output({"kind": "chat", "success": True, "message": response}, output_json)
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
            return print_error_result(prior_context.error, output_json)
        client = create_chat_client_func(provider_env)
        result = run_agent_func(
            task,
            client=client,
            base_dir=project_root,
            max_iterations=execution_config.max_iterations,
            command_timeout_ms=execution_config.command_timeout_ms,
            max_output_tokens=execution_config.max_output_tokens,
            model_retries=execution_config.model_retries,
            model_retry_delay_ms=execution_config.model_retry_delay_ms,
            model_timeout_ms=execution_config.model_timeout_ms,
            approval_handler=build_approval_handler(approval_policy),
            user_input_handler=None if output_json else prompt_user_input,
            prior_context=prior_context.context,
        )
        if output_json:
            print_output(
                {
                    "kind": "code",
                    "success": result.success,
                    "status": result.status,
                    "message": result.message,
                    "runId": result.run_id,
                    "runDir": str(result.run_dir),
                    "iterations": result.iterations,
                    "steps": len(result.steps),
                    "priorContext": prior_context.to_json(),
                    "plan": [{"status": item.status, "step": item.step} for item in result.plan],
                    "completionReady": result.completion_ready,
                    "completionBlockers": result.completion_blockers,
                    "completionWarnings": result.completion_warnings,
                    "completionBlockedCount": result.completion_blocked_count,
                    "latestCompletionBlockers": result.latest_completion_blockers,
                    "latestCompletionPendingChecks": result.latest_completion_pending_verification_checks,
                    "latestCompletionFailedChecks": result.latest_completion_failed_verification_checks,
                    "latestCompletionFinalReviewIssues": result.latest_completion_final_review_issues,
                    "latestCompletionFinalReviewChangedFiles": result.latest_completion_final_review_changed_files,
                    "latestCompletionToolErrors": result.latest_completion_tool_errors,
                    "latestCompletionCheckpointFailures": result.latest_completion_checkpoint_failures,
                    "latestCompletionActiveProcesses": result.latest_completion_active_background_processes,
                    "latestCompletionDeniedApprovals": result.latest_completion_denied_approvals,
                    "changedFiles": result.final_review_changed_files,
                    "verificationChecks": result.verification_checks,
                    "pendingVerificationChecks": result.pending_verification_checks,
                    "failedVerificationChecks": result.failed_verification_checks,
                },
                True,
            )
        else:
            print_agent_result(result)
        return 0 if result.success and result.completion_ready else 1
    except KeyboardInterrupt:
        return print_interrupted_result(output_json)
    except Exception as error:
        return print_error_result(format_error(error), output_json, prefix=True)
