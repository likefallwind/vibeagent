from __future__ import annotations

import argparse
from pathlib import Path

from .background_agent_runtime import (
    background_agent_view_payload,
    launch_background_agent,
)
from .cli_config import resolve_project_root
from .cli_local_result import emit_local_result


def launch_background_agent_from_cli(
    argv: list[str],
    args: argparse.Namespace,
) -> int:
    invocation_root = Path.cwd()
    project_root = resolve_project_root(args.cwd) or invocation_root
    view = launch_background_agent(
        project_root,
        invocation_root,
        argv,
        task_summary=" ".join(args.task),
        session_name=args.name,
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


__all__ = ["launch_background_agent_from_cli"]
