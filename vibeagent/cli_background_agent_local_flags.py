from __future__ import annotations

import argparse
from pathlib import Path
import shlex
from typing import Any

from .background_agent_runtime import (
    background_agent_view_payload,
    list_background_agents,
    read_background_agent_logs,
    remove_background_agent,
    stop_background_agent,
)


def run_background_agent_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    _command_namespace: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or Path.cwd()
    if args.background_agents:
        views = list_background_agents(root)
        return _format_background_agents(views), {
            "backgroundAgents": [background_agent_view_payload(view) for view in views]
        }
    if args.background_agent_log is not None:
        view, stdout, stderr = read_background_agent_logs(
            root,
            args.background_agent_log,
            max_chars=args.background_agent_log_max_chars,
        )
        if view is None:
            return _not_found(args.background_agent_log)
        return _format_background_agent_log(view, stdout, stderr), {
            "backgroundAgent": {
                **background_agent_view_payload(view),
                "stdout": stdout,
                "stderr": stderr,
            }
        }
    if args.stop_background_agent is not None:
        view = stop_background_agent(root, args.stop_background_agent)
        if view is None:
            return _not_found(args.stop_background_agent)
        text = (
            f"Background agent {view.record.id}:\n"
            f"  status: {view.status}\n"
            f"  exitCode: {view.exit_code if view.exit_code is not None else '.'}"
        )
        return text, {"backgroundAgent": background_agent_view_payload(view)}
    if args.remove_background_agent is not None:
        removed, message = remove_background_agent(root, args.remove_background_agent)
        return (
            f"Background agent removal:\n  ok: {'yes' if removed else 'no'}\n  message: {message}",
            {"backgroundAgentRemoval": {"ok": removed, "message": message}},
        )
    return None


def run_interactive_background_agent_command(command: Any) -> str | None:
    root = Path.cwd()
    if command.type == "background_agents":
        return _format_background_agents(list_background_agents(root))
    if command.type == "background_agent_log":
        usage = "Usage: /background-agent-log <id> [max-chars]"
        parts, error = _parse_argument(command.argument, usage, maximum=2)
        if error:
            return error
        max_chars = 20_000
        if len(parts) == 2:
            try:
                max_chars = int(parts[1])
            except ValueError:
                return usage
            if not 1_000 <= max_chars <= 100_000:
                return "Background agent log max-chars must be between 1000 and 100000."
        view, stdout, stderr = read_background_agent_logs(root, parts[0], max_chars=max_chars)
        return _not_found(parts[0])[0] if view is None else _format_background_agent_log(view, stdout, stderr)
    if command.type == "stop_background_agent":
        parts, error = _parse_argument(
            command.argument,
            "Usage: /stop-background-agent <id>",
        )
        if error:
            return error
        view = stop_background_agent(root, parts[0])
        if view is None:
            return _not_found(parts[0])[0]
        return (
            f"Background agent {view.record.id}:\n"
            f"  status: {view.status}\n"
            f"  exitCode: {view.exit_code if view.exit_code is not None else '.'}"
        )
    if command.type == "remove_background_agent":
        parts, error = _parse_argument(
            command.argument,
            "Usage: /remove-background-agent <id>",
        )
        if error:
            return error
        removed, message = remove_background_agent(root, parts[0])
        return f"Background agent removal:\n  ok: {'yes' if removed else 'no'}\n  message: {message}"
    return None


def _format_background_agents(views) -> str:
    lines = ["Background agents:", f"  count: {len(views)}"]
    for view in views:
        record = view.record
        lines.append(
            f"  - {record.id}: status={view.status}; pid={record.pid}; "
            f"session={record.session_name or '.'}; task={record.task_summary or '.'}"
        )
    return "\n".join(lines)


def _format_background_agent_log(view, stdout: str, stderr: str) -> str:
    record = view.record
    return "\n".join(
        [
            f"Background agent {record.id}:",
            f"  status: {view.status}",
            f"  exitCode: {view.exit_code if view.exit_code is not None else '.'}",
            f"  session: {record.session_name or '.'}",
            "  stdout:",
            stdout.rstrip() or "    (empty)",
            "  stderr:",
            stderr.rstrip() or "    (empty)",
        ]
    )


def _not_found(agent_id: str) -> tuple[str, dict[str, object]]:
    text = f"Background agent not found: {agent_id}"
    return text, {"backgroundAgent": {"ok": False, "id": agent_id, "message": text}}


def _parse_argument(
    argument: str | None,
    usage: str,
    *,
    maximum: int = 1,
) -> tuple[list[str], str | None]:
    if not argument:
        return [], usage
    try:
        parts = shlex.split(argument)
    except ValueError:
        return [], usage
    if not 1 <= len(parts) <= maximum:
        return [], usage
    return parts, None


__all__ = [
    "run_background_agent_local_flag",
    "run_interactive_background_agent_command",
]
