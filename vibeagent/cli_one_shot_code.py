from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
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
from .cli_goal import evaluate_and_store_goal
from .commands import parse_local_command
from .goal_loop import goal_turn_prompt
from .goal_state import GoalState, new_goal, read_session_goal, reset_restored_goal, write_goal
from .session_usage import summarize_run_usage
from .peer_runtime import create_peer_runtime
from .types import ApprovalPolicy
from .workspace_core import create_local_workspace
from .workspace_permissions import ProjectPermissions
from .session_additional_directories import (
    merge_additional_directories,
    restore_session_additional_directories,
)
from .session_branching import create_session_branch
from .session_names import name_session, normalize_session_name


def run_one_shot_code(
    task: str,
    *,
    project_root: Path,
    execution_config: ExecutionConfig,
    provider_env: dict[str, str | None],
    approval_policy: ApprovalPolicy,
    agent: str | None = None,
    session_name: str | None = None,
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
    additional_directories: tuple[Path, ...] = (),
    task_metadata: dict[str, object] | None,
    resume_arg: str | None,
    compact_arg: str | None,
    auto_compact: bool,
    fork_session: bool = False,
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

    restored_directories = restore_session_additional_directories(project_root, prior_context.run_id)
    try:
        additional_directories = merge_additional_directories(
            project_root,
            additional_directories,
            restored_directories.directories,
        )
    except ValueError as error:
        return 1, replace(prior_context, error=str(error))

    merged_prior_context = combine_optional_text(prior_context.context, input_prior_context)
    client = create_chat_client_func(provider_env)
    goal_state, steering_task = _resolve_one_shot_goal(task, prior_context, project_root)
    if goal_state is not None:
        task = goal_turn_prompt(goal_state, steering_task)
    stream_scope = build_one_shot_stream_scope(
        stream,
        project_root=project_root,
        mcp_config_paths=resolved_mcp_config_paths,
        strict_mcp_config=strict_mcp_config,
        additional_roots=additional_directories,
        force_workspace=fork_session or session_name is not None,
    )
    peer_runtime = create_peer_runtime(project_root, approval_policy)
    run_kwargs = build_one_shot_agent_kwargs(
        client=client,
        project_root=project_root,
        execution_config=execution_config,
        approval_policy=approval_policy,
        agent=agent,
        trust_project_permissions=trust_project_permissions,
        permission_overrides=permission_overrides,
        mcp_config_paths=resolved_mcp_config_paths,
        strict_mcp_config=strict_mcp_config,
        machine_output=output_mode.machine,
        stream_json=output_mode.stream_json,
        prior_context=merged_prior_context,
        system_prompt=system_prompt,
        append_system_prompt=append_system_prompt,
        additional_directories=additional_directories,
        task_metadata=task_metadata,
        workspace=stream_scope.workspace,
        peer_runtime=peer_runtime,
    )
    if prior_context.run_id is not None:
        run_kwargs["task_source_run_id"] = prior_context.run_id
    goal_turns = 0
    recorded_session_tokens: dict[str, int] = {}
    try:
        with stream_scope.event_scope:
            if fork_session:
                if prior_context.run_id is None or stream_scope.workspace is None:
                    raise ValueError("--fork-session requires a resolved source session.")
                create_session_branch(
                    project_root,
                    prior_context.run_id,
                    additional_directories=additional_directories,
                    workspace=stream_scope.workspace,
                )
            if session_name is not None:
                if stream_scope.workspace is None:
                    raise ValueError("--name requires a persistent coding session workspace.")
                name_session(project_root, stream_scope.workspace.run_id, normalize_session_name(session_name))
            while True:
                result = run_agent_func(task, **run_kwargs)
                goal_turns += 1
                if goal_state is None:
                    break
                workspace = create_local_workspace(project_root, result.run_id)
                write_goal(workspace, goal_state)
                if not result.success:
                    break
                selected, next_context, _ = get_resume_context_func(result.run_id, project_root)
                session_tokens = summarize_run_usage(project_root, result.run_id).total_tokens
                agent_tokens = max(0, session_tokens - recorded_session_tokens.get(result.run_id, 0))
                recorded_session_tokens[result.run_id] = session_tokens
                goal_state, evaluation = evaluate_and_store_goal(
                    goal_state,
                    result,
                    next_context,
                    client=client,
                    execution_config=execution_config,
                    project_root=project_root,
                    agent_tokens=agent_tokens,
                )
                if evaluation.achieved:
                    break
                task = goal_turn_prompt(goal_state)
                run_kwargs["prior_context"] = next_context
                run_kwargs["prior_messages"] = result.conversation
                run_kwargs["workspace"] = create_local_workspace(
                    project_root,
                    result.run_id,
                    additional_roots=additional_directories,
                )
                run_kwargs.pop("task_source_run_id", None)
    finally:
        if peer_runtime is not None:
            peer_runtime.close()
    result_payload = build_one_shot_code_payload(
        result,
        prior_context,
        machine_output=output_mode.machine,
        elapsed_ms=elapsed_ms,
        project_root=project_root,
        provider_env=provider_env,
    )
    if goal_state is not None:
        result_payload["goal"] = {
            "condition": goal_state.condition,
            "status": goal_state.status,
            "evaluatedTurns": goal_state.evaluated_turns,
            "totalTokens": goal_state.total_tokens,
            "lastReason": goal_state.last_reason,
        }
        result_payload["goalTurns"] = goal_turns
    if fork_session:
        result_payload["sessionBranch"] = {
            "runId": result.run_id,
            "sourceRunId": prior_context.run_id,
        }
    if session_name is not None:
        result_payload["sessionName"] = normalize_session_name(session_name)
    emit_one_shot_code_payload(
        result,
        result_payload,
        stream=stream,
        output_json=output_json,
        print_mode=print_mode,
    )
    return one_shot_code_exit_code(result), prior_context


def _resolve_one_shot_goal(
    task: str,
    prior_context: OneShotPriorContext,
    project_root: Path,
) -> tuple[GoalState | None, str | None]:
    command = parse_local_command(task)
    if command is not None and command.type == "goal":
        argument = command.argument
        if argument is None or argument.strip().lower() in {"clear", "stop", "off", "reset", "none", "cancel"}:
            raise ValueError("One-shot /goal requires a non-empty completion condition.")
        return new_goal(argument), None
    if prior_context.source != "resume":
        return None, None
    restored = read_session_goal(project_root, prior_context.run_id)
    active = reset_restored_goal(restored) if restored is not None else None
    return active, task if active is not None else None
