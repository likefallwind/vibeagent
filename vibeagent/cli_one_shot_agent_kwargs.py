from __future__ import annotations

from pathlib import Path
from typing import Any

from .cli_output import build_approval_handler, prompt_user_input
from .project_trust import is_project_permissions_trusted
from .types import ApprovalPolicy


def build_one_shot_agent_kwargs(
    *,
    client: object,
    project_root: Path,
    execution_config: object,
    approval_policy: ApprovalPolicy,
    trust_project_permissions: bool,
    permission_overrides: object,
    mcp_config_paths: list[Path] | tuple[Path, ...],
    strict_mcp_config: bool,
    machine_output: bool,
    stream_json: bool,
    prior_context: str | None,
    system_prompt: str | None,
    append_system_prompt: str | None,
    task_metadata: dict[str, object] | None,
    workspace: object | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
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
        "mcp_config_paths": mcp_config_paths,
        "strict_mcp_config": strict_mcp_config,
        "user_input_handler": None if machine_output else prompt_user_input,
        "prior_context": prior_context,
        "system_prompt": system_prompt,
        "append_system_prompt": append_system_prompt,
        "task_metadata": task_metadata,
    }
    if workspace is not None:
        kwargs["workspace"] = workspace
    return kwargs
