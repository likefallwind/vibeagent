from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from .agent_runtime_utils import append_session_event, compact_session_context
from .agent_tool_registry import initialize_agent_tools
from .prompts import build_messages
from .redaction import redact_jsonable_payload
from .session_tasks import inherit_task_store
from .types import ApprovalPolicy, ChatMessage
from .workspace_core import RunWorkspace, create_run_workspace
from .workspace_hooks import ProjectHooks, read_project_hooks
from .workspace_permissions import (
    ProjectPermissions,
    format_permissions_for_prompt,
    merge_project_permissions,
    read_project_permissions,
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


def prepare_agent_run(
    task: str,
    *,
    base_dir: str | Path | None,
    workspace: RunWorkspace | None,
    prior_context: str | None,
    approval_policy: ApprovalPolicy,
    task_metadata: dict[str, object] | None,
    task_source_run_id: str | None = None,
    trust_project_permissions: bool,
    permission_overrides: ProjectPermissions | None,
    mcp_config_paths: tuple[Path, ...],
    strict_mcp_config: bool,
    system_prompt: str | None,
    append_system_prompt: str | None,
) -> AgentRunSetup:
    current_workspace = _prepare_workspace(
        base_dir,
        workspace,
        mcp_config_paths,
        strict_mcp_config,
        trust_project_permissions,
    )
    project_permissions = _prepare_project_permissions(
        current_workspace,
        permission_overrides,
    )
    tasks_inherited, task_restore_error = inherit_task_store(current_workspace, task_source_run_id)
    auto_memory = read_auto_memory(current_workspace)
    messages = build_messages(
        task,
        current_workspace,
        prior_context=prior_context,
        approval_policy=approval_policy,
        permission_summary=format_permissions_for_prompt(project_permissions),
        system_prompt=system_prompt,
        append_system_prompt=append_system_prompt,
        auto_memory=auto_memory,
    )
    _append_task_event(current_workspace, task, approval_policy, prior_context, task_metadata)
    _append_task_restore_event(current_workspace, task_source_run_id, tasks_inherited, task_restore_error)
    _append_memory_event(current_workspace, auto_memory)
    project_hooks = read_project_hooks(current_workspace)
    _append_hooks_event(current_workspace, project_hooks)
    _append_permissions_event(current_workspace, project_permissions)
    sandbox_config = read_workspace_sandbox(current_workspace)
    _append_sandbox_event(current_workspace, sandbox_config)
    active_tool_names = initialize_agent_tools(current_workspace, approval_policy)
    return AgentRunSetup(
        workspace=current_workspace,
        messages=messages,
        active_tool_names=active_tool_names,
        project_hooks=project_hooks,
        project_permissions=project_permissions,
        sandbox_config=sandbox_config,
    )


def _prepare_workspace(
    base_dir: str | Path | None,
    workspace: RunWorkspace | None,
    mcp_config_paths: tuple[Path, ...],
    strict_mcp_config: bool,
    trust_project_permissions: bool,
) -> RunWorkspace:
    current_workspace = workspace or create_run_workspace(
        base_dir,
        mcp_config_paths=mcp_config_paths,
        strict_mcp_config=strict_mcp_config,
    )
    if workspace is not None and mcp_config_paths and not workspace.mcp_config_paths:
        absolute_mcp_paths = tuple(path if path.is_absolute() else current_workspace.root / path for path in mcp_config_paths)
        current_workspace = replace(workspace, mcp_config_paths=absolute_mcp_paths)
    if workspace is not None and strict_mcp_config != current_workspace.strict_mcp_config:
        current_workspace = replace(current_workspace, strict_mcp_config=strict_mcp_config)
    if trust_project_permissions and not current_workspace.project_config_trusted:
        current_workspace = replace(current_workspace, project_config_trusted=True)
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
    }
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
