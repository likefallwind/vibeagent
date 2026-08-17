from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from .cli_interactive_project_runtime import InteractiveProjectRuntime
from .config import resolve_execution_config
from .dynamic_agent_profiles import DynamicAgentProfile
from .dynamic_workflow_agent import (
    background_workflow_approval_handler,
    execute_workflow_agent_request,
)
from .dynamic_workflow_runtime import DynamicWorkflowManager
from .types import ApprovalHandler, ApprovalPolicy, ChatClient
from .workspace_core import RunWorkspace, create_local_workspace, create_run_workspace
from .workspace_hooks import read_project_hooks
from .workspace_permissions import read_project_permissions


@dataclass(frozen=True)
class InteractiveWorkflowRequest:
    project_root: Path
    project_runtime: InteractiveProjectRuntime
    pending_workspace: RunWorkspace | None
    resume_run_id: str | None
    additional_directories: tuple[Path, ...]
    dynamic_agent_profiles: tuple[DynamicAgentProfile, ...]
    approval_policy: ApprovalPolicy
    approval_handler: ApprovalHandler | None
    safe_mode: bool
    bare_mode: bool
    setting_sources: tuple[str, ...]
    settings_override_json: str | None
    invocation_plugin_dirs: tuple[Path, ...]


def get_or_create_interactive_workflow_manager(
    request: InteractiveWorkflowRequest,
    *,
    ensure_client: Callable[[], ChatClient],
) -> DynamicWorkflowManager:
    if request.project_runtime.workflow is not None:
        return request.project_runtime.workflow
    workspace = request.pending_workspace or _workflow_workspace(request)
    if request.dynamic_agent_profiles:
        workspace = replace(
            workspace,
            dynamic_agent_profiles=request.dynamic_agent_profiles,
        )
    hooks = read_project_hooks(workspace)
    permissions = read_project_permissions(workspace)
    if workspace.project_config_trusted and permissions.enabled:
        permissions = replace(permissions, allow_rules_trusted=True)

    def execute_agent(agent_request, cancel_requested):
        return execute_workflow_agent_request(
            workspace,
            agent_request,
            ensure_client(),
            execution_config=resolve_execution_config(request.project_root),
            approval_handler=background_workflow_approval_handler(
                request.approval_policy,
                request.approval_handler,
            ),
            approval_policy=request.approval_policy,
            hooks=hooks,
            permissions=permissions,
            cancel_requested=cancel_requested,
        )

    return request.project_runtime.set_workflow(
        DynamicWorkflowManager(workspace, execute_agent)
    )


def _workflow_workspace(request: InteractiveWorkflowRequest) -> RunWorkspace:
    if request.resume_run_id is not None:
        return create_local_workspace(
            request.project_root,
            request.resume_run_id,
            additional_roots=request.additional_directories,
            safe_mode=request.safe_mode,
            bare_mode=request.bare_mode,
            setting_sources=request.setting_sources,
            settings_override_json=request.settings_override_json,
            invocation_plugin_dirs=request.invocation_plugin_dirs,
        )
    return create_run_workspace(
        request.project_root,
        additional_roots=request.additional_directories,
        safe_mode=request.safe_mode,
        bare_mode=request.bare_mode,
        setting_sources=request.setting_sources,
        settings_override_json=request.settings_override_json,
        invocation_plugin_dirs=request.invocation_plugin_dirs,
    )


__all__ = [
    "InteractiveWorkflowRequest",
    "get_or_create_interactive_workflow_manager",
]
