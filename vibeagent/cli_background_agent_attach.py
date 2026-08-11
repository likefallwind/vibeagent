from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Callable

from .background_agent_attach import attach_background_agent
from .cli_args import parse_args
from .cli_config import resolve_project_root
from .background_agent_runtime import send_background_agent_message
from .interactive_background import InteractiveBackgroundRequest


def attach_background_agent_from_cli(
    args: argparse.Namespace,
    *,
    run_interactive_func: Callable[[argparse.Namespace], int],
) -> int:
    project_root = resolve_project_root(args.cwd) or Path.cwd()

    def report_wait() -> None:
        print(
            f"Waiting for background agent {args.attach_background_agent} "
            "to finish its active turn..."
        )

    background_request: InteractiveBackgroundRequest | None = None
    with attach_background_agent(
        project_root,
        args.attach_background_agent,
        on_wait=report_wait,
    ) as attachment:
        config = attachment.config
        attached_args = parse_args(config.base_argv)
        attached_args.attach_background_agent = None
        attached_args.task = []
        attached_args.background = False
        attached_args.print_mode = False
        attached_args.cwd = config.session_root.as_posix()
        attached_args.resume = config.resume_reference
        attached_args.resume_from_continue = False
        attached_args.continue_latest = False
        attached_args.session_id = None
        attached_args.compact = None
        attached_args.fork_session = False
        attached_args.name = None
        attached_args.worktree = None
        attached_args.no_auto_compact = False
        attached_args._attached_background_agent_id = config.agent_id
        print(
            f"Attached to background agent {config.agent_id} "
            f"in {config.session_root}."
        )
        previous_cwd = Path.cwd()
        os.chdir(attachment.invocation_root)
        try:
            try:
                return run_interactive_func(attached_args)
            except InteractiveBackgroundRequest as request:
                background_request = request
        finally:
            os.chdir(previous_cwd)
    if background_request is None:
        raise RuntimeError("Background attachment ended without an exit result.")
    _, disposition = send_background_agent_message(
        project_root,
        background_request.attached_agent_id or args.attach_background_agent,
        background_request.prompt,
    )
    print(
        f"Background agent {args.attach_background_agent} detached and {disposition}."
    )
    return 0


__all__ = ["attach_background_agent_from_cli"]
