from __future__ import annotations

import argparse
from pathlib import Path

from .cli_config import resolve_project_root
from .session_pull_requests import resolve_session_from_pull_request


def prepare_pull_request_resume(args: argparse.Namespace) -> None:
    selector = getattr(args, "from_pr", None)
    if selector is None:
        return
    if args.resume is not None or args.session_id is not None or args.compact is not None or args.continue_latest:
        raise ValueError("--from-pr cannot be combined with --resume, --session-id, --compact, or --continue.")
    root = resolve_project_root(args.cwd) or Path.cwd().resolve()
    args.resume = resolve_session_from_pull_request(root, selector)


__all__ = ["prepare_pull_request_resume"]
