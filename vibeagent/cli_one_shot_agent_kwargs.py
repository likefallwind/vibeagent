from __future__ import annotations

from pathlib import Path

from .cli_output import build_approval_handler, prompt_user_input
from .config import ExecutionConfig
from .project_trust import is_project_permissions_trusted
from .types import AgentLogger, ApprovalHandler, ApprovalPolicy
from .workspace_core import RunWorkspace
from .workspace_permissions import ProjectPermissions
from .peer_runtime import PeerSessionRuntime
from .dynamic_agent_profiles import DynamicAgentProfile
from .model_streaming import AgentModelStreamHandler
from .background_agent_approval import background_agent_approval_handler
from .background_agent_config import BackgroundAgentConfig
from .background_agent_input import BackgroundUserInputPrompt
from .permission_prompt_mcp import (
    PermissionPromptTool,
    build_mcp_permission_prompt_handler,
)


def build_one_shot_agent_kwargs(
    *,
    client: object,
    project_root: Path,
    execution_config: ExecutionConfig,
    approval_policy: ApprovalPolicy,
    agent: str | None = None,
    tool_names: frozenset[str] | None = None,
    trust_project_permissions: bool,
    permission_overrides: ProjectPermissions | None,
    mcp_config_paths: tuple[Path, ...],
    strict_mcp_config: bool,
    safe_mode: bool = False,
    bare_mode: bool = False,
    brief: bool = False,
    disable_slash_commands: bool = False,
    setting_sources: tuple[str, ...] = ("user", "project", "local"),
    settings_override_json: str | None = None,
    invocation_plugin_dirs: tuple[Path, ...] = (),
    machine_output: bool,
    stream_json: bool,
    print_mode: bool = False,
    setup_trigger: str | None = None,
    prior_context: str | None,
    system_prompt: str | None,
    append_system_prompt: str | None,
    append_subagent_system_prompt: str | None = None,
    additional_directories: tuple[Path, ...] = (),
    dynamic_agent_profiles: tuple[DynamicAgentProfile, ...] = (),
    autocompact_tokens: int | None = None,
    task_metadata: dict[str, object] | None,
    workspace: RunWorkspace | None = None,
    peer_runtime: PeerSessionRuntime | None = None,
    model_stream_handler: AgentModelStreamHandler | None = None,
    background_agent_config: BackgroundAgentConfig | None = None,
    permission_prompt_tool: PermissionPromptTool | None = None,
    logger: AgentLogger | None = None,
) -> dict[str, object]:
    approval_handler = _build_one_shot_approval_handler(
        approval_policy=approval_policy,
        workspace=workspace,
        permission_prompt_tool=permission_prompt_tool,
        background_agent_config=background_agent_config,
        command_timeout_ms=execution_config.command_timeout_ms,
        stream_json=stream_json,
    )
    kwargs: dict[str, object] = {
        "client": client,
        "base_dir": project_root,
        "max_iterations": execution_config.max_iterations,
        "command_timeout_ms": execution_config.command_timeout_ms,
        "max_output_tokens": execution_config.max_output_tokens,
        "model_retries": execution_config.model_retries,
        "model_retry_delay_ms": execution_config.model_retry_delay_ms,
        "model_timeout_ms": execution_config.model_timeout_ms,
        "approval_handler": approval_handler,
        "approval_policy": approval_policy,
        "agent": agent,
        "tool_names": tool_names,
        "trust_project_permissions": trust_project_permissions or is_project_permissions_trusted(project_root),
        "permission_overrides": permission_overrides,
        "mcp_config_paths": mcp_config_paths,
        "strict_mcp_config": strict_mcp_config,
        "safe_mode": safe_mode,
        "bare_mode": bare_mode,
        "brief": brief,
        "disable_slash_commands": disable_slash_commands,
        "setting_sources": setting_sources,
        "settings_override_json": settings_override_json,
        "invocation_plugin_dirs": invocation_plugin_dirs,
        "user_input_handler": (
            BackgroundUserInputPrompt(background_agent_config)
            if background_agent_config is not None
            else (None if machine_output else prompt_user_input)
        ),
        "prior_context": prior_context,
        "system_prompt": system_prompt,
        "append_system_prompt": append_system_prompt,
        "append_subagent_system_prompt": append_subagent_system_prompt,
        "task_metadata": task_metadata,
        "dynamic_agent_profiles": dynamic_agent_profiles,
        "autocompact_tokens": autocompact_tokens,
        "defer_tool_calls": print_mode,
        "close_async_hooks_on_finish": print_mode,
    }
    if setup_trigger is not None:
        kwargs["setup_trigger"] = setup_trigger
    if additional_directories:
        kwargs["additional_directories"] = additional_directories
    if workspace is not None:
        kwargs["workspace"] = workspace
    if peer_runtime is not None:
        kwargs["peer_runtime"] = peer_runtime
    if model_stream_handler is not None:
        kwargs["model_stream_handler"] = model_stream_handler
    if logger is not None:
        kwargs["logger"] = logger
    return kwargs


def _build_one_shot_approval_handler(
    *,
    approval_policy: ApprovalPolicy,
    workspace: RunWorkspace | None,
    permission_prompt_tool: PermissionPromptTool | None,
    background_agent_config: BackgroundAgentConfig | None,
    command_timeout_ms: int,
    stream_json: bool,
) -> ApprovalHandler | None:
    if permission_prompt_tool is not None:
        if workspace is None:
            raise ValueError("Permission prompt MCP delegation requires a session workspace.")
        return build_mcp_permission_prompt_handler(
            workspace,
            permission_prompt_tool,
            timeout_ms=command_timeout_ms,
        )
    background_approval = background_agent_approval_handler(
        background_agent_config,
        approval_policy,
    )
    if background_approval is not None:
        return background_approval
    if stream_json and approval_policy == "ask":
        return None
    return build_approval_handler(approval_policy)
