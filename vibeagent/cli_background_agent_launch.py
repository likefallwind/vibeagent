from __future__ import annotations

import argparse
from pathlib import Path

from .background_agent_runtime import (
    background_agent_view_payload,
    launch_background_agent,
)
from .cli_context import is_resume_clear_arg, normalize_resume_arg
from .cli_config import resolve_project_root
from .cli_local_result import emit_local_result
from .commands import get_resume_context


def launch_background_agent_from_cli(
    argv: list[str],
    args: argparse.Namespace,
) -> int:
    invocation_root = Path.cwd()
    project_root = resolve_project_root(args.cwd) or invocation_root
    resume_reference = _resolve_background_resume_reference(args, project_root)
    view = launch_background_agent(
        project_root,
        invocation_root,
        argv,
        task_summary=" ".join(args.task),
        session_name=args.name,
        resume_reference=resume_reference,
    )
    record = view.record
    session_line = record.session_name or "."
    text = "\n".join(
        [
            f"Background agent started: {record.id}",
            f"  pid: {record.pid}",
            f"  session: {session_line}",
            f"  logs: vibeagent --background-agent-log {record.id}",
            f"  stop: vibeagent --stop-background-agent {record.id}",
            "  note: approvals that require terminal input are denied in background mode.",
        ]
    )
    return emit_local_result(
        args,
        text,
        {"backgroundAgent": background_agent_view_payload(view)},
    )


def _resolve_background_resume_reference(
    args: argparse.Namespace,
    project_root: Path,
) -> str | None:
    if getattr(args, "compact", None) is not None or getattr(args, "fork_session", False):
        return None
    resume = getattr(args, "resume", None)
    value = resume if resume is not None else getattr(args, "session_id", None)
    if value is None:
        return None
    normalized = normalize_resume_arg(value)
    if is_resume_clear_arg(normalized):
        return None
    run_id, context, message = get_resume_context(normalized, project_root)
    if context is None or run_id is None:
        raise ValueError(message or "Background resume could not resolve its source session.")
    return run_id


__all__ = ["launch_background_agent_from_cli"]
