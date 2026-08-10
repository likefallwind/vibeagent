from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from .cli_context import (
    build_context_limit_kwargs,
    is_resume_clear_arg,
    normalize_resume_arg,
)
from .commands import get_compact_context, get_resume_context


@dataclass(frozen=True)
class InteractiveStartupContext:
    run_id: str | None = None
    context: str | None = None
    message: str | None = None
    error: str | None = None
    agent: str | None = None


def resolve_interactive_startup_context(
    args: argparse.Namespace,
    project_root: Path,
    *,
    get_resume_context_func=get_resume_context,
    get_compact_context_func=get_compact_context,
) -> InteractiveStartupContext:
    selected_agent = getattr(args, "agent", None)
    session_resume = args.resume if args.resume is not None else args.session_id
    if session_resume is None and args.compact is None:
        return InteractiveStartupContext(agent=selected_agent)
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
            return InteractiveStartupContext(run_id=run_id, message=message, error=message, agent=selected_agent)
        return InteractiveStartupContext(run_id=run_id, context=context, message=message, agent=selected_agent)

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
        return InteractiveStartupContext(run_id=run_id, message=message, error=message, agent=selected_agent)
    return InteractiveStartupContext(run_id=run_id, context=context, message=message, agent=selected_agent)
