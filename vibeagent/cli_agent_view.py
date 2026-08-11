from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from .agent_view import run_agent_view
from .cli_background_agent_attach import attach_background_agent_from_cli
from .cli_config import resolve_project_root


def run_agent_view_from_cli(
    args: argparse.Namespace,
    *,
    run_interactive_func: Callable[[argparse.Namespace], int],
) -> int:
    project_root = resolve_project_root(args.cwd) or Path.cwd()
    outcome = run_agent_view(project_root)
    if outcome.attach_id is None:
        return 0
    attached_args = argparse.Namespace(**vars(args))
    attached_args.agent_view = False
    attached_args.attach_background_agent = outcome.attach_id
    return attach_background_agent_from_cli(
        attached_args,
        run_interactive_func=run_interactive_func,
    )


__all__ = ["run_agent_view_from_cli"]
