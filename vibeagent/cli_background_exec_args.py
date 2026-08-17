from __future__ import annotations

import argparse

from .cli_local_flag_detection import has_local_flag


def add_background_exec_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--exec",
        dest="exec_command",
        metavar="COMMAND",
        help="Run a shell command as a managed background process (requires --background).",
    )


def validate_background_exec_arguments(args: argparse.Namespace) -> str | None:
    command = getattr(args, "exec_command", None)
    if command is None:
        return None
    if not args.background:
        return "--exec requires --background."
    if not command.strip():
        return "--exec command cannot be empty."
    if args.task:
        return "--exec cannot be combined with a coding task."
    if args.chat:
        return "--exec cannot be combined with --chat."
    if has_local_flag(args):
        return "--exec cannot be combined with local inspection or management commands."
    if (
        any(
            value is not None
            for value in (
                args.agent,
                args.agents,
                args.model,
                args.provider,
                args.model_name,
                args.base_url,
                args.resume,
                args.session_id,
                args.compact,
                args.worktree,
                args.name,
                args.effort,
                args.from_pr,
            )
        )
        or args.continue_latest
        or args.fork_session
    ):
        return "--exec cannot be combined with agent, session, model-effort, or naming options."
    return None


__all__ = ["add_background_exec_argument", "validate_background_exec_arguments"]
