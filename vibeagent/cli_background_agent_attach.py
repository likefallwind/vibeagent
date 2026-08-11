from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Callable

from .background_agent_attach import attach_background_agent
from .cli_args import parse_args
from .cli_config import resolve_project_root


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
        print(
            f"Attached to background agent {config.agent_id} "
            f"in {config.session_root}."
        )
        previous_cwd = Path.cwd()
        os.chdir(attachment.invocation_root)
        try:
            return run_interactive_func(attached_args)
        finally:
            os.chdir(previous_cwd)


__all__ = ["attach_background_agent_from_cli"]
