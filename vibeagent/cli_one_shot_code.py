from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .agent_result import AgentResult
from .cli_context import OneShotPriorContext, SessionContextGetter
from .cli_one_shot_agent_kwargs import build_one_shot_agent_kwargs
from .cli_one_shot_input import combine_optional_text, resolve_one_shot_context_from_limits
from .cli_one_shot_output import build_one_shot_code_payload, emit_one_shot_code_payload, one_shot_code_exit_code
from .cli_one_shot_stream import build_one_shot_stream_scope
from .cli_output_mode import CliOutputMode
from .cli_stream_output import JsonEventStream
from .config import ExecutionConfig
from .types import ApprovalPolicy
from .workspace_permissions import ProjectPermissions


def run_one_shot_code(
    task: str,
    *,
    project_root: Path,
    execution_config: ExecutionConfig,
    provider_env: dict[str, str | None],
    approval_policy: ApprovalPolicy,
    trust_project_permissions: bool,
    permission_overrides: ProjectPermissions | None,
    resolved_mcp_config_paths: tuple[Path, ...],
    strict_mcp_config: bool,
    output_mode: CliOutputMode,
    output_json: bool,
    print_mode: bool,
    elapsed_ms: int,
    stream: JsonEventStream | None,
    input_prior_context: str | None,
    system_prompt: str | None,
    append_system_prompt: str | None,
    task_metadata: dict[str, object] | None,
    resume_arg: str | None,
    compact_arg: str | None,
    auto_compact: bool,
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
    create_chat_client_func: Callable[[dict[str, str | None]], object],
    run_agent_func: Callable[..., AgentResult],
    get_resume_context_func: SessionContextGetter,
    get_compact_context_func: SessionContextGetter,
) -> tuple[int, OneShotPriorContext]:
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
        return 1, prior_context

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
        elapsed_ms=elapsed_ms,
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
    return one_shot_code_exit_code(result), prior_context
