from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .cli_background_agent_local_flags import run_interactive_background_agent_command
from .cli_code_intel_local_flags import run_interactive_code_intel_command
from .cli_command_local_flags import run_interactive_command_execution
from .cli_edit_local_flags import run_interactive_edit_command
from .cli_git_local_flags import run_interactive_git_command
from .cli_interactive_read_commands import run_interactive_read_command
from .cli_json_local_flags import run_interactive_json_command
from .cli_patch_local_flags import run_interactive_patch_command
from .cli_project_local_flags import (
    run_interactive_project_command,
    run_interactive_project_state_command,
)
from .cli_review_local_flags import run_interactive_review_command
from .cli_runtime_local_flags import run_interactive_runtime_command
from .cli_text_edit_local_flags import run_interactive_text_edit_command
from .command_types import LocalCommand
from .types import ApprovalPolicy


@dataclass(frozen=True)
class InteractiveLocalCommandContext:
    project_root: Path
    mode: Literal["code", "chat"]
    approval_policy: ApprovalPolicy
    resume_run_id: str | None
    resume_context: str | None
    chat_turns: int
    effort: str
    autocompact: str
    system_prompt_set: bool
    append_system_prompt_set: bool
    permission_mode: str
    safe_mode: bool


def dispatch_interactive_local_command(
    command: LocalCommand,
    command_namespace: dict[str, Any],
    context: InteractiveLocalCommandContext,
    *,
    project_command_namespace: dict[str, Any] | None = None,
) -> str | None:
    text = run_interactive_project_command(
        command,
        (
            project_command_namespace
            if project_command_namespace is not None
            else command_namespace
        ),
        context.approval_policy,
        context.project_root,
        safe_mode=context.safe_mode,
    )
    if text is not None:
        return text

    for handler in (
        run_interactive_background_agent_command,
        lambda value: run_interactive_command_execution(value, command_namespace),
        lambda value: run_interactive_read_command(value, command_namespace),
        lambda value: run_interactive_code_intel_command(value, command_namespace),
        lambda value: run_interactive_json_command(value, command_namespace),
        lambda value: run_interactive_text_edit_command(value, command_namespace),
        lambda value: run_interactive_edit_command(value, command_namespace),
        lambda value: run_interactive_patch_command(value, command_namespace),
        lambda value: run_interactive_git_command(value, command_namespace),
        lambda value: run_interactive_runtime_command(value, command_namespace),
    ):
        text = handler(command)
        if text is not None:
            return text

    text = run_interactive_project_state_command(
        command,
        command_namespace,
        mode=context.mode,
        approval_policy=context.approval_policy,
        resume_run_id=context.resume_run_id,
        resume_context=context.resume_context,
        chat_turns=context.chat_turns,
        effort=context.effort,
        autocompact=context.autocompact,
        system_prompt_set=context.system_prompt_set,
        append_system_prompt_set=context.append_system_prompt_set,
        permission_mode=context.permission_mode,
    )
    if text is not None:
        return text
    return run_interactive_review_command(command, command_namespace)


__all__ = [
    "InteractiveLocalCommandContext",
    "dispatch_interactive_local_command",
]
