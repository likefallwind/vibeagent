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
from .invocation_plugins import resolve_invocation_plugin_dirs


def launch_background_agent_from_cli(
    argv: list[str],
    args: argparse.Namespace,
) -> int:
    invocation_root = Path.cwd()
    project_root = resolve_project_root(args.cwd) or invocation_root
    resume_reference = _resolve_background_resume_reference(args, project_root)
    launch_argv = _with_resolved_invocation_plugins(argv, args, invocation_root)
    view = launch_background_agent(
        project_root,
        invocation_root,
        launch_argv,
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
            "  input: open `vibeagent agents` to handle approvals and questions.",
        ]
    )
    return emit_local_result(
        args,
        text,
        {"backgroundAgent": background_agent_view_payload(view)},
    )


def _with_resolved_invocation_plugins(
    argv: list[str],
    args: argparse.Namespace,
    invocation_root: Path,
) -> list[str]:
    plugin_dirs = getattr(args, "plugin_dir", None)
    plugin_urls = getattr(args, "plugin_url", None)
    if not plugin_dirs and not plugin_urls:
        return argv
    resolved = resolve_invocation_plugin_dirs(
        plugin_dirs,
        invocation_root=invocation_root,
        plugin_urls=plugin_urls,
    )
    rewritten: list[str] = []
    index = 0
    options = True
    while index < len(argv):
        item = argv[index]
        if options and item == "--":
            options = False
            rewritten.append(item)
            index += 1
            continue
        if options and item in {"--plugin-dir", "--plugin-url"}:
            index += 2
            continue
        if options and (
            item.startswith("--plugin-dir=") or item.startswith("--plugin-url=")
        ):
            index += 1
            continue
        rewritten.append(item)
        index += 1
    insertion = rewritten.index("--") if "--" in rewritten else len(rewritten)
    replacement = [item for root in resolved for item in ("--plugin-dir", root.as_posix())]
    rewritten[insertion:insertion] = replacement
    return rewritten


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
