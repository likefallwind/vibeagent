from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, replace
from pathlib import Path

from .cli_context import (
    build_context_limit_kwargs,
    is_resume_clear_arg,
    normalize_resume_arg,
)
from .cli_additional_directories import resolve_additional_directories
from .cli_config import model_override_from_args
from .cli_system_prompt_files import resolve_system_prompt_inputs
from .commands import get_compact_context, get_resume_context
from .context_compaction import resolve_autocompact_tokens
from .dynamic_agent_profiles import DynamicAgentProfile, parse_dynamic_agent_profiles
from .model_effort import resolve_model_effort_setting
from .invocation_settings import parse_invocation_settings, parse_setting_sources
from .session_additional_directories import (
    merge_additional_directories,
    restore_session_additional_directories,
)
from .session_branching import create_session_branch
from .session_names import name_session, normalize_session_name
from .session_conversation import load_session_conversation
from .types import ApprovalPolicy, ChatMessage
from .workspace_core import RunWorkspace, create_local_workspace, create_run_workspace


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
    conversation: tuple[ChatMessage, ...] = ()
    dynamic_agent_profiles: tuple[DynamicAgentProfile, ...] = ()
    effort: str | None = None
    effort_locked: bool = False
    autocompact_tokens: int | None = None
    attached_background_agent_id: str | None = None
    model: str | None = None
    approval: ApprovalPolicy = "ask"
    safe_mode: bool = False
    setting_sources: tuple[str, ...] = ("user", "project", "local")
    settings_override_json: str | None = None


def resolve_interactive_startup_context(
    args: argparse.Namespace,
    project_root: Path,
    *,
    get_resume_context_func=get_resume_context,
    get_compact_context_func=get_compact_context,
) -> InteractiveStartupContext:
    selected_agent = getattr(args, "agent", None)
    effort = resolve_model_effort_setting(getattr(args, "effort", None), os.environ)
    dynamic_agent_profiles = parse_dynamic_agent_profiles(getattr(args, "agents", None))
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
        "dynamic_agent_profiles": dynamic_agent_profiles,
        "effort": effort.level,
        "effort_locked": effort.locked,
        "autocompact_tokens": resolve_autocompact_tokens(getattr(args, "autocompact", None)),
        "attached_background_agent_id": getattr(args, "_attached_background_agent_id", None),
        "model": model_override_from_args(args),
        "approval": getattr(args, "approval", "ask"),
        "safe_mode": getattr(args, "safe_mode", False),
        "setting_sources": parse_setting_sources(getattr(args, "setting_sources", None)),
        "settings_override_json": parse_invocation_settings(
            getattr(args, "settings", None),
            invocation_root=Path.cwd(),
        ),
    }
    session_resume = args.resume if args.resume is not None else args.session_id
    if session_resume is None and args.compact is None:
        return _with_requested_name(InteractiveStartupContext(**prompt_kwargs), args, project_root)
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
        context = _with_restored_conversation(context, project_root)
        context = _with_resumed_workspace(context, project_root)
        context = _with_forked_session(context, project_root) if getattr(args, "fork_session", False) else context
        return _with_requested_name(context, args, project_root)

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
    context = _with_forked_session(context, project_root) if getattr(args, "fork_session", False) else context
    return _with_requested_name(context, args, project_root)


def _with_restored_conversation(
    context: InteractiveStartupContext,
    project_root: Path,
) -> InteractiveStartupContext:
    if context.error is not None or context.run_id is None:
        return context
    loaded = load_session_conversation(project_root, context.run_id)
    message_parts = [part for part in (context.message, loaded.warning) if part]
    return replace(
        context,
        conversation=loaded.messages,
        message="\n".join(message_parts) or None,
    )


def _with_resumed_workspace(
    context: InteractiveStartupContext,
    project_root: Path,
) -> InteractiveStartupContext:
    if context.error is not None or context.run_id is None:
        return context
    return replace(
        context,
        pending_workspace=create_local_workspace(
            project_root,
            context.run_id,
            additional_roots=context.additional_directories,
            safe_mode=context.safe_mode,
            setting_sources=context.setting_sources,
            settings_override_json=context.settings_override_json,
        ),
    )


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
        pending_workspace=replace(
            branch.workspace,
            safe_mode=context.safe_mode,
            setting_sources=context.setting_sources,
            settings_override_json=context.settings_override_json,
        ),
        branch_source_run_id=branch.source_run_id,
    )


def _with_requested_name(
    context: InteractiveStartupContext,
    args: argparse.Namespace,
    project_root: Path,
) -> InteractiveStartupContext:
    requested = getattr(args, "name", None)
    if requested is None or context.error is not None:
        return context
    try:
        normalized = normalize_session_name(requested)
        workspace = context.pending_workspace
        run_id = workspace.run_id if workspace is not None else None
        if run_id is None:
            workspace = create_run_workspace(
                project_root,
                additional_roots=context.additional_directories,
                safe_mode=context.safe_mode,
                setting_sources=context.setting_sources,
                settings_override_json=context.settings_override_json,
            )
            run_id = workspace.run_id
        name_session(project_root, run_id, normalized)
    except (OSError, ValueError) as error:
        return replace(context, error=str(error))
    message = "\n".join(part for part in (context.message, f"Session named: {normalized} ({run_id})") if part)
    active_run_id = context.run_id if context.run_id is not None else run_id
    return replace(context, run_id=active_run_id, message=message, pending_workspace=workspace)
