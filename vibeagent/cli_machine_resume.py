from __future__ import annotations

import argparse
from pathlib import Path

from .cli_config import resolve_project_root
from .cli_context import normalize_resume_arg
from .session_machine_index import (
    backfill_project_session_index,
    is_machine_searchable_session_id,
    resolve_machine_session_root,
)


def prepare_machine_session_resume(args: argparse.Namespace) -> None:
    value = normalize_resume_arg(getattr(args, "resume", None))
    if value is None or not is_machine_searchable_session_id(value):
        return
    current_root = (resolve_project_root(getattr(args, "cwd", None)) or Path.cwd()).resolve()
    backfill_project_session_index(current_root)
    resolved_root = resolve_machine_session_root(current_root, value)
    if resolved_root is not None and resolved_root != current_root:
        args.cwd = str(resolved_root)


__all__ = ["prepare_machine_session_resume"]
