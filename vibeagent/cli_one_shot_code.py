from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from .agent_result import AgentResult
from .cli_context import OneShotPriorContext, SessionContextGetter
from .cli_one_shot_agent_kwargs import build_one_shot_agent_kwargs
from .cli_one_shot_input import combine_optional_text, resolve_one_shot_context_from_limits
from .cli_one_shot_output import (
    apply_model_fallback_result,
    apply_model_budget_result,
    apply_structured_output_result,
    build_one_shot_code_payload,
    emit_one_shot_code_payload,
    one_shot_code_exit_code,
)
from .cli_one_shot_stream import build_one_shot_stream_scope
from .cli_output_mode import CliOutputMode
from .cli_stream_output import JsonEventStream
from .config import ExecutionConfig
from .cli_goal import evaluate_and_store_goal
from .commands import parse_local_command
from .goal_loop import goal_turn_prompt
from .goal_state import GoalState, new_goal, read_session_goal, reset_restored_goal, write_goal
from .model_budget import BudgetedChatClient, ModelCostBudget, create_model_cost_budget
from .model_fallback import ModelFallbackState, create_fallback_chat_client
from .peer_runtime import create_peer_runtime
from .session_additional_directories import (
    merge_additional_directories,
    restore_session_additional_directories,
)
from .session_branching import create_session_branch
from .session_conversation import load_session_conversation
from .session_names import name_session, normalize_session_name
from .session_usage import summarize_run_usage
from .structured_output import StructuredOutputResult, generate_structured_output
from .types import ApprovalPolicy, ChatMessage
from .workspace_core import RunWorkspace, create_local_workspace
from .workspace_permissions import ProjectPermissions
from .dynamic_agent_profiles import DynamicAgentProfile
from .monitor_runtime import stop_session_monitors
from .deferred_tool_state import read_deferred_tool_state
from .session_lifecycle_hooks import run_session_end_hooks
from .agent_runtime_utils import append_session_event, format_exception
from .model_effort import ModelEffortSetting, configure_model_effort
from .background_agent_config import BackgroundAgentConfig


def run_one_shot_code(
    task: str,
    *,
    project_root: Path,
    execution_config: ExecutionConfig,
    provider_env: dict[str, str | None],
    approval_policy: ApprovalPolicy,
    agent: str | None = None,
    dynamic_agent_profiles: tuple[DynamicAgentProfile, ...] = (),
    session_name: str | None = None,
    trust_project_permissions: bool,
    permission_overrides: ProjectPermissions | None,
    resolved_mcp_config_paths: tuple[Path, ...],
    strict_mcp_config: bool,
    safe_mode: bool = False,
    setting_sources: tuple[str, ...] = ("user", "project", "local"),
    settings_override_json: str | None = None,
    invocation_plugin_dirs: tuple[Path, ...] = (),
    output_mode: CliOutputMode,
    output_json: bool,
    print_mode: bool,
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
    elapsed_ms: int,
    stream: JsonEventStream | None,
    input_prior_context: str | None,
    system_prompt: str | None,
    append_system_prompt: str | None,
    append_subagent_system_prompt: str | None = None,
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
    ephemeral_workspace: RunWorkspace | None = None,
    session_record_root: Path | None = None,
    create_chat_client_func: Callable[[dict[str, str | None]], object],
    run_agent_func: Callable[..., AgentResult],
    background_agent_config: BackgroundAgentConfig | None = None,
    get_resume_context_func: SessionContextGetter,
    get_compact_context_func: SessionContextGetter,
    generate_structured_output_func: Callable[..., StructuredOutputResult] = generate_structured_output,
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
    goal_state, steering_task = _resolve_one_shot_goal(task, prior_context, project_root)
    if ephemeral_workspace is not None and goal_state is not None:
        raise ValueError("--no-session-persistence cannot be used with a one-shot /goal task.")
    if goal_state is not None:
        task = goal_turn_prompt(goal_state, steering_task)
    model_budget: ModelCostBudget | None = None
    if max_budget_usd is not None:
        model_budget = create_model_cost_budget(max_budget_usd, provider_env)
    client = create_chat_client_func(provider_env)
    model_fallback: ModelFallbackState | None = None
    if fallback_model is not None:
        client, model_fallback = create_fallback_chat_client(client, fallback_model)
    if model_budget is not None:
        client = BudgetedChatClient(client, model_budget)
    client = configure_model_effort(
        client,  # type: ignore[arg-type]
        ModelEffortSetting(effort, locked=effort_locked),
    )
    resumed_workspace = (
        ephemeral_workspace
        or (
            create_local_workspace(
                project_root,
                prior_context.run_id,
                mcp_config_paths=resolved_mcp_config_paths,
                strict_mcp_config=strict_mcp_config,
                additional_roots=additional_directories,
                safe_mode=safe_mode,
                setting_sources=setting_sources,
                settings_override_json=settings_override_json,
                invocation_plugin_dirs=invocation_plugin_dirs,
            )
            if prior_context.source == "resume"
            and prior_context.run_id is not None
            and not fork_session
            else None
        )
    )
    stream_scope = build_one_shot_stream_scope(
        stream,
        project_root=project_root,
        mcp_config_paths=resolved_mcp_config_paths,
        strict_mcp_config=strict_mcp_config,
        additional_roots=additional_directories,
        safe_mode=safe_mode,
        setting_sources=setting_sources,
        settings_override_json=settings_override_json,
        invocation_plugin_dirs=invocation_plugin_dirs,
        force_workspace=fork_session or session_name is not None or ephemeral_workspace is not None,
        workspace=resumed_workspace,
        forward_subagent_text=forward_subagent_text,
    )
    if replay_user_messages:
        if stream is None or stream_scope.workspace is None:
            raise ValueError("User message replay requires a persistent stream-json coding session.")
        for message in input_user_messages or (task,):
            stream.user_message(stream_scope.workspace.session_dir, message)
    peer_runtime = create_peer_runtime(project_root, approval_policy)
    run_kwargs = build_one_shot_agent_kwargs(
        client=client,
        project_root=project_root,
        execution_config=execution_config,
        approval_policy=approval_policy,
        agent=agent,
        dynamic_agent_profiles=dynamic_agent_profiles,
        tool_names=tool_names,
        trust_project_permissions=trust_project_permissions,
        permission_overrides=permission_overrides,
        mcp_config_paths=resolved_mcp_config_paths,
        strict_mcp_config=strict_mcp_config,
        safe_mode=safe_mode,
        setting_sources=setting_sources,
        settings_override_json=settings_override_json,
        invocation_plugin_dirs=invocation_plugin_dirs,
        machine_output=output_mode.machine,
        stream_json=output_mode.stream_json,
        print_mode=print_mode,
        prior_context=merged_prior_context,
        system_prompt=system_prompt,
        append_system_prompt=append_system_prompt,
        append_subagent_system_prompt=append_subagent_system_prompt,
        additional_directories=additional_directories,
        autocompact_tokens=autocompact_tokens,
        task_metadata=task_metadata,
        setup_trigger=setup_trigger,
        workspace=stream_scope.workspace,
        peer_runtime=peer_runtime,
        model_stream_handler=(
            stream.model_stream_event
            if include_partial_messages and stream is not None
            else None
        ),
        background_agent_config=background_agent_config,
    )
    continuing_source_session = (
        ephemeral_workspace is None
        and resumed_workspace is not None
        and resumed_workspace.run_id == prior_context.run_id
    )
    if prior_context.run_id is not None and not continuing_source_session:
        run_kwargs["task_source_run_id"] = prior_context.run_id
    if prior_context.source == "resume" and prior_context.run_id is not None:
        restored_conversation = load_session_conversation(project_root, prior_context.run_id)
        prior_messages = list(restored_conversation.messages)
        if prior_messages and input_prior_context:
            prior_messages.append(
                ChatMessage(
                    role="user",
                    content=f"Additional continuation context:\n{input_prior_context}",
                )
            )
        if prior_messages:
            run_kwargs["prior_messages"] = prior_messages
        source_workspace = create_local_workspace(
            project_root,
            prior_context.run_id,
            safe_mode=safe_mode,
            setting_sources=setting_sources,
            settings_override_json=settings_override_json,
            invocation_plugin_dirs=invocation_plugin_dirs,
        )
        if continuing_source_session or ephemeral_workspace is not None:
            deferred_state = read_deferred_tool_state(source_workspace)
            if deferred_state is not None:
                run_kwargs["deferred_tool_state"] = deferred_state
    goal_turns = 0
    structured_output: StructuredOutputResult | None = None
    result: AgentResult | None = None
    session_end_ran = False
    recorded_session_tokens: dict[str, int] = {}

    def result_workspace() -> RunWorkspace:
        assert result is not None
        if ephemeral_workspace is not None and ephemeral_workspace.run_id == result.run_id:
            return replace(ephemeral_workspace, root=result.run_dir)
        return create_local_workspace(
            result.run_dir,
            result.run_id,
            additional_roots=additional_directories,
            safe_mode=safe_mode,
            setting_sources=setting_sources,
            settings_override_json=settings_override_json,
            invocation_plugin_dirs=invocation_plugin_dirs,
        )

    def end_session() -> None:
        nonlocal session_end_ran
        if result is None or session_end_ran:
            return
        current_workspace = result_workspace()
        session_end_ran = True
        try:
            run_session_end_hooks(
                current_workspace,
                "other",
                command_timeout_ms=execution_config.command_timeout_ms,
                approval_handler=run_kwargs.get("approval_handler"),
                approval_policy=result.approval_policy or approval_policy,
            )
        except Exception as error:
            append_session_event(
                current_workspace.session_dir,
                "session_end_hook_error",
                {"reason": "other", "message": format_exception(error)},
            )

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
                if result.stop_reason in {"tool_deferred", "tool_deferred_unavailable"}:
                    break
                workspace = create_local_workspace(project_root, result.run_id, safe_mode=safe_mode)
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
                    safe_mode=safe_mode,
                )
                run_kwargs.pop("setup_trigger", None)
                run_kwargs.pop("task_source_run_id", None)
            if structured_output_schema is not None and result.success and result.completion_ready:
                structured_output = generate_structured_output_func(
                    client,
                    result.conversation,
                    structured_output_schema,
                    session_dir=result_workspace().session_dir,
                    max_output_tokens=execution_config.max_output_tokens,
                    model_retries=execution_config.model_retries,
                    model_retry_delay_ms=execution_config.model_retry_delay_ms,
                    model_timeout_ms=execution_config.model_timeout_ms,
                    iteration=result.iterations,
                )
            end_session()
    finally:
        if result is not None:
            end_session()
            stop_session_monitors(project_root, result.run_id)
        if peer_runtime is not None:
            peer_runtime.close()
    assert result is not None
    result_payload = build_one_shot_code_payload(
        result,
        prior_context,
        machine_output=output_mode.machine,
        elapsed_ms=elapsed_ms,
        project_root=session_record_root or project_root,
        provider_env=provider_env,
    )
    apply_structured_output_result(result_payload, structured_output)
    apply_model_fallback_result(result_payload, model_fallback)
    apply_model_budget_result(result_payload, model_budget)
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
    if ephemeral_workspace is not None:
        result_payload["sessionPersistence"] = False
        result_payload["session_persistence"] = False
    emit_one_shot_code_payload(
        result,
        result_payload,
        stream=stream,
        output_json=output_json,
        print_mode=print_mode,
    )
    return one_shot_code_exit_code(result, structured_output, model_budget), prior_context


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
