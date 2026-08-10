from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from pathlib import Path

from .cli_context import (
    build_context_limit_kwargs,
    is_resume_clear_arg,
    normalize_resume_arg,
)
from .commands import get_compact_context, get_resume_context
from .cli_system_prompt_files import resolve_system_prompt_inputs
from .cli_additional_directories import resolve_additional_directories
from .session_additional_directories import (
    merge_additional_directories,
    restore_session_additional_directories,
)
from .session_branching import create_session_branch
from .workspace_core import RunWorkspace


@dataclass(frozen=True)
class InteractiveStartupContext:
    run_id: str | None = None
    context: str | None = None
    message: str | None = None
    error: str | None = None
    agent: str | None = None
    system_prompt: str | None = None
    append_system_prompt: str | None = None
    additional_directories: tuple[Path, ...] = ()
    pending_workspace: RunWorkspace | None = None
    branch_source_run_id: str | None = None


def resolve_interactive_startup_context(
    args: argparse.Namespace,
    project_root: Path,
    *,
    get_resume_context_func=get_resume_context,
    get_compact_context_func=get_compact_context,
) -> InteractiveStartupContext:
    selected_agent = getattr(args, "agent", None)
    additional_directories = resolve_additional_directories(args.add_dir, invocation_root=Path.cwd())
    system_prompt, append_system_prompt = resolve_system_prompt_inputs(
        system_prompt=args.system_prompt,
        system_prompt_file=args.system_prompt_file,
        append_system_prompt=args.append_system_prompt,
        append_system_prompt_file=args.append_system_prompt_file,
        invocation_root=Path.cwd(),
    )
    prompt_kwargs = {
        "agent": selected_agent,
        "system_prompt": system_prompt,
        "append_system_prompt": append_system_prompt,
        "additional_directories": additional_directories,
    }
    session_resume = args.resume if args.resume is not None else args.session_id
    if session_resume is None and args.compact is None:
        return InteractiveStartupContext(**prompt_kwargs)
    if session_resume is not None:
        resume_kwargs = build_context_limit_kwargs(
            max_failures=args.resume_max_failures,
            max_files=args.resume_max_files,
            max_commands=args.resume_max_commands,
            max_checks=args.resume_max_checks,
            max_output_chars=args.resume_max_output_chars,
            max_text=args.resume_max_text,
        )
        normalized_resume = normalize_resume_arg(session_resume)
        run_id, context, message = get_resume_context_func(normalized_resume, project_root, **resume_kwargs)
        if context is None and not is_resume_clear_arg(normalized_resume):
            return InteractiveStartupContext(run_id=run_id, message=message, error=message, **prompt_kwargs)
        context = _with_restored_directories(
            InteractiveStartupContext(run_id=run_id, context=context, message=message, **prompt_kwargs),
            project_root,
        )
        return _with_forked_session(context, project_root) if getattr(args, "fork_session", False) else context

    compact_kwargs = build_context_limit_kwargs(
        max_failures=args.compact_max_failures,
        max_files=args.compact_max_files,
        max_commands=args.compact_max_commands,
        max_checks=args.compact_max_checks,
        max_output_chars=args.compact_max_output_chars,
        max_text=args.compact_max_text,
    )
    run_id, context, message = get_compact_context_func(normalize_resume_arg(args.compact), project_root, **compact_kwargs)
    if context is None:
        return InteractiveStartupContext(run_id=run_id, message=message, error=message, **prompt_kwargs)
    context = _with_restored_directories(
        InteractiveStartupContext(run_id=run_id, context=context, message=message, **prompt_kwargs),
        project_root,
    )
    return _with_forked_session(context, project_root) if getattr(args, "fork_session", False) else context


def _with_restored_directories(
    context: InteractiveStartupContext,
    project_root: Path,
) -> InteractiveStartupContext:
    restored = restore_session_additional_directories(project_root, context.run_id)
    try:
        directories = merge_additional_directories(
            project_root,
            context.additional_directories,
            restored.directories,
        )
    except (OSError, ValueError) as error:
        return replace(context, error=str(error))
    message_parts = [part for part in (context.message, restored.message) if part]
    return replace(
        context,
        message="\n".join(message_parts) or None,
        additional_directories=directories,
    )


def _with_forked_session(
    context: InteractiveStartupContext,
    project_root: Path,
) -> InteractiveStartupContext:
    if context.error is not None:
        return context
    if context.run_id is None or context.context is None:
        return replace(context, error="--fork-session requires a resolved source session.")
    try:
        branch = create_session_branch(
            project_root,
            context.run_id,
            additional_directories=context.additional_directories,
        )
    except (OSError, ValueError) as error:
        return replace(context, error=str(error))
    message_parts = [part for part in (context.message, branch.text) if part]
    return replace(
        context,
        run_id=branch.workspace.run_id,
        message="\n".join(message_parts),
        pending_workspace=branch.workspace,
        branch_source_run_id=branch.source_run_id,
    )
