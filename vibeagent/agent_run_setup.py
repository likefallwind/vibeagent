from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from .dynamic_agent_profiles import DynamicAgentProfile
from .agent_profile_permissions import apply_agent_permission_mode, permission_mode_forces_plan

from .agent_runtime_utils import append_session_event, compact_session_context
from .agent_conversation import continue_conversation
from .agent_tool_registry import (
    activate_agent_tool_names,
    activate_tools_for_run,
    initialize_agent_tools,
)
from .main_agent_profile import (
    MainAgentProfile,
    apply_tool_ceiling,
    append_main_profile_prompt,
    load_main_agent_profile,
)
from .main_agent_settings import resolve_main_agent_selection
from .prompt_file_mentions import (
    PromptFileContext,
    load_prompt_file_context,
    prompt_file_context_metadata,
)
from .permission_tool_visibility import globally_denied_tool_names
from .powershell_runtime import powershell_tool_availability
from .prompts import build_messages
from .redaction import redact_jsonable_payload
from .session_tasks import inherit_task_store
from .session_environment import (
    ensure_session_environment_file,
    inherit_session_environment,
)
from .session_working_directory import inherit_session_cwd
from .scheduled_task_store import inherit_schedule_store, schedule_store_path
from .types import ApprovalPolicy, ChatMessage
from .workspace_core import RunWorkspace, create_run_workspace, normalize_additional_roots
from .workspace_hooks import ProjectHooks, merge_project_hooks, read_project_hooks
from .workspace_permissions import (
    ProjectPermissions,
    format_permissions_for_prompt,
    merge_project_permissions,
    read_project_permissions,
    resolve_permission_additional_directories,
)
from .workspace_sandbox import SandboxConfig, read_workspace_sandbox
from .workspace_memory import AutoMemorySnapshot, read_auto_memory


@dataclass(frozen=True)
class AgentRunSetup:
    workspace: RunWorkspace
    messages: list[ChatMessage]
    active_tool_names: set[str]
    project_hooks: ProjectHooks
    project_permissions: ProjectPermissions
    sandbox_config: SandboxConfig
    main_profile: MainAgentProfile
    append_system_prompt: str | None
    tool_ceiling_names: frozenset[str] | None
    task: str
    task_metadata: dict[str, object] | None
    approval_policy: ApprovalPolicy
    approval_policy_locked: bool = False


def prepare_agent_run(
    task: str,
    *,
    base_dir: str | Path | None,
    workspace: RunWorkspace | None,
    prior_context: str | None,
    prior_messages: list[ChatMessage] | None = None,
    approval_policy: ApprovalPolicy,
    task_metadata: dict[str, object] | None,
    task_source_run_id: str | None = None,
    trust_project_permissions: bool,
    permission_overrides: ProjectPermissions | None,
    mcp_config_paths: tuple[Path, ...],
    strict_mcp_config: bool,
    safe_mode: bool = False,
    bare_mode: bool = False,
    setting_sources: tuple[str, ...] = ("user", "project", "local"),
    settings_override_json: str | None = None,
    invocation_plugin_dirs: tuple[Path, ...] = (),
    system_prompt: str | None,
    append_system_prompt: str | None,
    append_subagent_system_prompt: str | None = None,
    agent: str | None = None,
    tool_names: frozenset[str] | None = None,
    additional_directories: tuple[Path, ...] = (),
    dynamic_agent_profiles: tuple[DynamicAgentProfile, ...] = (),
    autocompact_tokens: int | None = None,
) -> AgentRunSetup:
    current_workspace = _prepare_workspace(
        base_dir,
        workspace,
        mcp_config_paths,
        strict_mcp_config,
        safe_mode,
        bare_mode,
        setting_sources,
        settings_override_json,
        invocation_plugin_dirs,
        trust_project_permissions,
        additional_directories,
        dynamic_agent_profiles,
        autocompact_tokens,
        append_subagent_system_prompt,
    )
    main_selection = resolve_main_agent_selection(current_workspace, agent)
    main_profile = load_main_agent_profile(
        current_workspace,
        main_selection.name,
        source=main_selection.source,
    )
    current_workspace = main_profile.workspace or current_workspace
    effective_append_system_prompt = append_main_profile_prompt(
        append_system_prompt, main_profile
    )
    project_permissions = _prepare_project_permissions(
        current_workspace,
        permission_overrides,
    )
    if project_permissions.error is None and project_permissions.additional_directories:
        try:
            configured_roots = resolve_permission_additional_directories(
                current_workspace,
                project_permissions,
            )
        except ValueError as error:
            project_permissions = replace(project_permissions, error=str(error))
        else:
            current_workspace = replace(
                current_workspace,
                additional_roots=normalize_additional_roots(
                    current_workspace.root,
                    configured_roots,
                ),
            )
    settings_approval_policy = approval_policy
    if approval_policy == "ask" and project_permissions.default_mode is not None:
        settings_approval_policy, project_permissions = apply_agent_permission_mode(
            approval_policy,
            project_permissions,
            project_permissions.default_mode,
        )
    approval_policy_locked = permission_mode_forces_plan(
        settings_approval_policy,
        project_permissions,
        main_profile.permission_mode,
    )
    effective_approval_policy, project_permissions = apply_agent_permission_mode(
        settings_approval_policy,
        project_permissions,
        main_profile.permission_mode,
    )
    permission_denied_tool_names = globally_denied_tool_names(project_permissions)
    main_profile = apply_tool_ceiling(
        main_profile,
        tool_names,
        permission_denied_tool_names,
    )
    environment_inherited, environment_restore_error = inherit_session_environment(
        current_workspace,
        task_source_run_id,
    )
    ensure_session_environment_file(current_workspace)
    powershell_availability = powershell_tool_availability(current_workspace)
    if not powershell_availability.enabled:
        main_profile = replace(
            main_profile,
            disallowed_tool_names=(
                main_profile.disallowed_tool_names | frozenset({"PowerShell", "powershell"})
            ),
        )
    tasks_inherited, task_restore_error = inherit_task_store(current_workspace, task_source_run_id)
    cwd_inherited, cwd_restore_error = inherit_session_cwd(
        current_workspace,
        task_source_run_id,
    )
    schedules_inherited, schedule_restore_error = inherit_schedule_store(current_workspace, task_source_run_id)
    auto_memory = read_auto_memory(current_workspace)
    effective_task = _main_profile_task(task, main_profile, prior_messages)
    prompt_file_context = load_prompt_file_context(effective_task, current_workspace)
    messages = build_messages(
        effective_task,
        current_workspace,
        prior_context=None if prior_messages else prior_context,
        approval_policy=effective_approval_policy,
        permission_summary=format_permissions_for_prompt(project_permissions),
        system_prompt=system_prompt,
        append_system_prompt=effective_append_system_prompt,
        auto_memory=auto_memory,
        prompt_file_context=prompt_file_context,
    )
    if prior_messages:
        messages = continue_conversation(prior_messages, messages)
    if current_workspace.safe_mode:
        append_session_event(
            current_workspace.session_dir,
            "safe_mode",
            {
                "enabled": True,
                "disabled": [
                    "agents", "auto_memory", "commands", "hooks", "instructions",
                    "lsp", "mcp", "plugins", "skills", "status_line", "workflows",
                ],
            },
        )
    elif current_workspace.bare_mode:
        append_session_event(
            current_workspace.session_dir,
            "bare_mode",
            {
                "enabled": True,
                "auto_discovery_disabled": [
                    "agents",
                    "commands",
                    "hooks",
                    "instructions",
                    "mcp",
                    "memory",
                    "plugins",
                    "skills",
                ],
                "explicit_sources_retained": [
                    "agents",
                    "mcp_config",
                    "plugins",
                    "settings",
                    "system_prompt",
                ],
            },
        )
    if (
        current_workspace.setting_sources != ("user", "project", "local")
        or current_workspace.settings_override_json is not None
    ):
        append_session_event(
            current_workspace.session_dir,
            "invocation_settings_loaded",
            {
                "sources": list(current_workspace.setting_sources),
                "override": current_workspace.settings_override_json is not None,
            },
        )
    if current_workspace.invocation_plugin_dirs:
        append_session_event(
            current_workspace.session_dir,
            "invocation_plugins_loaded",
            {"count": len(current_workspace.invocation_plugin_dirs)},
        )
    _append_task_event(
        current_workspace,
        effective_task,
        effective_approval_policy,
        prior_context,
        task_metadata,
    )
    if current_workspace.dynamic_agent_profiles:
        append_session_event(
            current_workspace.session_dir,
            "dynamic_agents_loaded",
            {
                "count": len(current_workspace.dynamic_agent_profiles),
                "names": [profile.name for profile in current_workspace.dynamic_agent_profiles],
            },
        )
    if prior_messages:
        append_session_event(
            current_workspace.session_dir,
            "conversation_continued",
            {"messages": len(prior_messages)},
        )
    _append_prompt_files_event(current_workspace, prompt_file_context)
    _append_task_restore_event(current_workspace, task_source_run_id, tasks_inherited, task_restore_error)
    append_session_event(
        current_workspace.session_dir,
        "session_environment_ready",
        {
            "source_run_id": task_source_run_id,
            "inherited": environment_inherited,
            "error": environment_restore_error,
        },
    )
    if task_source_run_id is not None:
        append_session_event(
            current_workspace.session_dir,
            "shell_cwd_restored",
            {
                "source_run_id": task_source_run_id,
                "restored": cwd_inherited,
                "error": cwd_restore_error,
            },
        )
    _append_schedule_restore_event(
        current_workspace,
        task_source_run_id,
        schedules_inherited,
        schedule_restore_error,
    )
    _append_memory_event(current_workspace, auto_memory)
    project_hooks = merge_project_hooks(
        read_project_hooks(current_workspace),
        main_profile.hooks,
    )
    _append_hooks_event(current_workspace, project_hooks)
    _append_permissions_event(current_workspace, project_permissions)
    sandbox_config = read_workspace_sandbox(current_workspace)
    _append_sandbox_event(current_workspace, sandbox_config)
    active_tool_names = initialize_agent_tools(
        current_workspace,
        effective_approval_policy,
        excluded_names=main_profile.disallowed_tool_names,
        allowed_names=main_profile.allowed_tool_names,
    )
    if powershell_availability.enabled:
        activate_agent_tool_names(
            active_tool_names,
            ["PowerShell"],
            effective_approval_policy,
            main_profile.disallowed_tool_names,
            main_profile.allowed_tool_names,
        )
    append_session_event(
        current_workspace.session_dir,
        "powershell_tool",
        {
            "enabled": powershell_availability.enabled,
            "executable": powershell_availability.executable,
            "message": powershell_availability.message,
        },
    )
    if approval_policy_locked:
        active_tool_names.discard("ExitPlanMode")
    _append_main_profile_event(current_workspace, main_profile)
    if tool_names is not None or permission_denied_tool_names:
        append_session_event(
            current_workspace.session_dir,
            "tool_restrictions_loaded",
            {
                "tools": sorted(tool_names) if tool_names is not None else None,
                "total": len(tool_names) if tool_names is not None else None,
                "disallowed_tools": sorted(permission_denied_tool_names),
            },
        )
    schedule_path = schedule_store_path(current_workspace)
    if schedule_path.exists() or schedule_path.is_symlink():
        activate_tools_for_run(
            current_workspace,
            active_tool_names,
            ["CronList", "CronDelete"],
            0,
            source="scheduled_task_store",
            approval_policy=effective_approval_policy,
            excluded_names=main_profile.disallowed_tool_names,
            allowed_names=main_profile.allowed_tool_names,
        )
    return AgentRunSetup(
        workspace=current_workspace,
        messages=messages,
        active_tool_names=active_tool_names,
        project_hooks=project_hooks,
        project_permissions=project_permissions,
        sandbox_config=sandbox_config,
        main_profile=main_profile,
        append_system_prompt=effective_append_system_prompt,
        tool_ceiling_names=tool_names,
        task=effective_task,
        task_metadata=task_metadata,
        approval_policy=effective_approval_policy,
        approval_policy_locked=approval_policy_locked,
    )


def _main_profile_task(
    task: str,
    profile: MainAgentProfile,
    prior_messages: list[ChatMessage] | None,
) -> str:
    if prior_messages or not profile.initial_prompt:
        return task
    return f"{profile.initial_prompt}\n\n{task}" if task.strip() else profile.initial_prompt


def _prepare_workspace(
    base_dir: str | Path | None,
    workspace: RunWorkspace | None,
    mcp_config_paths: tuple[Path, ...],
    strict_mcp_config: bool,
    safe_mode: bool,
    bare_mode: bool,
    setting_sources: tuple[str, ...],
    settings_override_json: str | None,
    invocation_plugin_dirs: tuple[Path, ...],
    trust_project_permissions: bool,
    additional_directories: tuple[Path, ...],
    dynamic_agent_profiles: tuple[DynamicAgentProfile, ...],
    autocompact_tokens: int | None,
    append_subagent_system_prompt: str | None,
) -> RunWorkspace:
    current_workspace = workspace or create_run_workspace(
        base_dir,
        mcp_config_paths=mcp_config_paths,
        strict_mcp_config=strict_mcp_config,
        additional_roots=additional_directories,
        safe_mode=safe_mode,
        bare_mode=bare_mode,
        setting_sources=setting_sources,
        settings_override_json=settings_override_json,
        invocation_plugin_dirs=invocation_plugin_dirs,
    )
    if workspace is not None and additional_directories:
        merged_roots = normalize_additional_roots(
            current_workspace.root,
            (*current_workspace.additional_roots, *additional_directories),
        )
        current_workspace = replace(current_workspace, additional_roots=merged_roots)
    if workspace is not None and mcp_config_paths and not workspace.mcp_config_paths:
        absolute_mcp_paths = tuple(path if path.is_absolute() else current_workspace.root / path for path in mcp_config_paths)
        current_workspace = replace(current_workspace, mcp_config_paths=absolute_mcp_paths)
    if workspace is not None and strict_mcp_config != current_workspace.strict_mcp_config:
        current_workspace = replace(current_workspace, strict_mcp_config=strict_mcp_config)
    if workspace is not None and safe_mode != current_workspace.safe_mode:
        current_workspace = replace(current_workspace, safe_mode=safe_mode)
    if workspace is not None and bare_mode != current_workspace.bare_mode:
        current_workspace = replace(current_workspace, bare_mode=bare_mode)
    if workspace is not None and setting_sources != current_workspace.setting_sources:
        current_workspace = replace(current_workspace, setting_sources=setting_sources)
    if workspace is not None and settings_override_json != current_workspace.settings_override_json:
        current_workspace = replace(current_workspace, settings_override_json=settings_override_json)
    if workspace is not None and invocation_plugin_dirs != current_workspace.invocation_plugin_dirs:
        current_workspace = replace(current_workspace, invocation_plugin_dirs=invocation_plugin_dirs)
    if safe_mode:
        current_workspace = replace(
            current_workspace,
            mcp_config_paths=(),
            strict_mcp_config=False,
            dynamic_agent_profiles=(),
            profile_mcp_server_configs=(),
        )
    if trust_project_permissions and not current_workspace.project_config_trusted:
        current_workspace = replace(current_workspace, project_config_trusted=True)
    if (
        not safe_mode
        and dynamic_agent_profiles
        and dynamic_agent_profiles != current_workspace.dynamic_agent_profiles
    ):
        current_workspace = replace(
            current_workspace,
            dynamic_agent_profiles=dynamic_agent_profiles,
        )
    if autocompact_tokens is not None and autocompact_tokens != current_workspace.autocompact_tokens:
        current_workspace = replace(current_workspace, autocompact_tokens=autocompact_tokens)
    if (
        append_subagent_system_prompt is not None
        and append_subagent_system_prompt != current_workspace.append_subagent_system_prompt
    ):
        current_workspace = replace(
            current_workspace,
            append_subagent_system_prompt=append_subagent_system_prompt,
        )
    return current_workspace


def _prepare_project_permissions(
    workspace: RunWorkspace,
    permission_overrides: ProjectPermissions | None,
) -> ProjectPermissions:
    project_permissions = read_project_permissions(workspace)
    project_permissions = merge_project_permissions(project_permissions, permission_overrides)
    if workspace.project_config_trusted:
        project_permissions = replace(project_permissions, allow_rules_trusted=True)
    return project_permissions


def _append_task_event(
    workspace: RunWorkspace,
    task: str,
    approval_policy: ApprovalPolicy,
    prior_context: str | None,
    task_metadata: dict[str, object] | None,
) -> None:
    task_event: dict[str, object] = {
        "task": task,
        "approval_policy": approval_policy,
        "prior_context": compact_session_context(prior_context) if prior_context else None,
        "additional_directories": [str(root) for root in workspace.additional_roots],
        "subagent_system_prompt_appended": bool(workspace.append_subagent_system_prompt),
    }
    if workspace.autocompact_tokens is not None:
        task_event["autocompact_tokens"] = workspace.autocompact_tokens
    if task_metadata:
        task_event["metadata"] = redact_jsonable_payload(task_metadata)
    append_session_event(workspace.session_dir, "task", task_event)


def _append_task_restore_event(
    workspace: RunWorkspace,
    source_run_id: str | None,
    inherited: bool,
    error: str | None,
) -> None:
    if source_run_id is None:
        return
    append_session_event(
        workspace.session_dir,
        "tasks_restored",
        {
            "source_run_id": source_run_id,
            "inherited": inherited,
            "error": error,
        },
    )


def _append_prompt_files_event(workspace: RunWorkspace, context: PromptFileContext) -> None:
    metadata = prompt_file_context_metadata(context)
    if int(metadata["count"]) == 0:
        return
    append_session_event(workspace.session_dir, "prompt_files_loaded", metadata)


def _append_memory_event(workspace: RunWorkspace, memory: AutoMemorySnapshot) -> None:
    append_session_event(
        workspace.session_dir,
        "auto_memory_loaded",
        {
            "enabled": memory.enabled,
            "bytes": len(memory.content.encode("utf-8")),
            "truncated": memory.truncated,
            "error": memory.error,
        },
    )


def _append_schedule_restore_event(
    workspace: RunWorkspace,
    source_run_id: str | None,
    inherited: int,
    error: str | None,
) -> None:
    if source_run_id is None:
        return
    append_session_event(
        workspace.session_dir,
        "scheduled_tasks_restored",
        {
            "source_run_id": source_run_id,
            "inherited": inherited,
            "error": error,
        },
    )


def _append_hooks_event(workspace: RunWorkspace, project_hooks: ProjectHooks) -> None:
    if not project_hooks.enabled:
        return
    append_session_event(
        workspace.session_dir,
        "hooks_loaded",
        {
            "sources": list(project_hooks.sources),
            "count": len(project_hooks.hooks),
            "error": project_hooks.error,
        },
    )


def _append_permissions_event(workspace: RunWorkspace, project_permissions: ProjectPermissions) -> None:
    if not project_permissions.enabled:
        return
    append_session_event(
        workspace.session_dir,
        "permissions_loaded",
        {
            "sources": list(project_permissions.sources),
            "count": len(project_permissions.rules),
            "error": project_permissions.error,
            "allow_rules_trusted": project_permissions.allow_rules_trusted,
            "trusted_allow_sources": list(project_permissions.trusted_allow_sources),
            "default_mode": project_permissions.default_mode,
            "default_mode_source": project_permissions.default_mode_source,
            "additional_directories": list(project_permissions.additional_directories),
        },
    )


def _append_sandbox_event(workspace: RunWorkspace, sandbox_config: SandboxConfig) -> None:
    if not (sandbox_config.enabled or sandbox_config.sources or sandbox_config.error is not None):
        return
    append_session_event(
        workspace.session_dir,
        "sandbox_loaded",
        {
            "enabled": sandbox_config.enabled,
            "active": sandbox_config.active,
            "available": sandbox_config.available,
            "network_disabled": sandbox_config.network_disabled,
            "network_available": sandbox_config.network_available,
            "fail_if_unavailable": sandbox_config.fail_if_unavailable,
            "auto_allow_bash_if_sandboxed": sandbox_config.auto_allow_bash_if_sandboxed,
            "sources": list(sandbox_config.sources),
            "error": sandbox_config.error,
        },
    )


def _append_main_profile_event(
    workspace: RunWorkspace, profile: MainAgentProfile
) -> None:
    if not profile.enabled:
        return
    append_session_event(
        workspace.session_dir,
        "main_agent_profile_loaded",
        {
            "name": profile.name,
            "source": profile.source,
            "mode": profile.mode,
            "model": profile.model,
            "effort": profile.effort,
            "max_turns": profile.max_turns,
            "skills": list(profile.skills),
            "memory_scope": profile.memory_scope,
            "permission_mode": profile.permission_mode,
            "has_initial_prompt": profile.initial_prompt is not None,
            "color": profile.color,
            "allowed_tools": (
                sorted(profile.allowed_tool_names)
                if profile.allowed_tool_names is not None
                else None
            ),
            "disallowed_tools": sorted(profile.disallowed_tool_names),
        },
    )
