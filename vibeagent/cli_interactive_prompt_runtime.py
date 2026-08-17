from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cli_output import format_error
from .cli_interactive_session_management import interactive_session_prompt
from .config import resolve_execution_config
from .types import ApprovalHandler, ApprovalPolicy
from .workspace_core import RunWorkspace


@dataclass(frozen=True)
class InteractivePromptRequest:
    project_root: Path
    resume_run_id: str | None
    pending_workspace: RunWorkspace | None
    additional_directories: tuple[Path, ...]
    safe_mode: bool
    approval_handler: ApprovalHandler | None
    approval_policy: ApprovalPolicy


@dataclass(frozen=True)
class InteractivePromptServices:
    idle_notification_factory: Callable[[], Any]
    create_file_changed_runtime: Callable[..., Any]
    create_config_change_runtime: Callable[..., Any]
    completion_scope: Callable[..., Any]
    input_with_idle_callback: Callable[..., str]


def read_interactive_prompt(
    request: InteractivePromptRequest,
    services: InteractivePromptServices,
    *,
    run_idle_tasks: Callable[[Any, Any | None, Any | None], None],
) -> str:
    idle_notification = services.idle_notification_factory()
    file_changed_runtime = None
    config_change_runtime = None
    if request.resume_run_id is not None and not request.safe_mode:
        try:
            command_timeout_ms = resolve_execution_config(
                request.project_root
            ).command_timeout_ms
            file_changed_runtime = services.create_file_changed_runtime(
                request.project_root,
                request.resume_run_id,
                request.pending_workspace,
                request.additional_directories,
                command_timeout_ms=command_timeout_ms,
                approval_handler=request.approval_handler,
                approval_policy=request.approval_policy,
            )
            config_change_runtime = services.create_config_change_runtime(
                request.project_root,
                request.resume_run_id,
                request.pending_workspace,
                request.additional_directories,
                command_timeout_ms=command_timeout_ms,
                approval_handler=request.approval_handler,
                approval_policy=request.approval_policy,
            )
        except Exception as error:
            print(f"Runtime change hook warning: {format_error(error)}")
    with services.completion_scope(
        request.project_root,
        request.additional_directories,
    ):
        return services.input_with_idle_callback(
            interactive_session_prompt(
                request.project_root,
                request.resume_run_id,
                request.pending_workspace,
            ),
            lambda: run_idle_tasks(
                idle_notification,
                file_changed_runtime,
                config_change_runtime,
            ),
            input_func=input,
        ).strip()


__all__ = [
    "InteractivePromptRequest",
    "InteractivePromptServices",
    "read_interactive_prompt",
]
