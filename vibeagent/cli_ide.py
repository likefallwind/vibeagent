from __future__ import annotations

import argparse
import os
from pathlib import Path

from .cli_config import resolve_project_root
from .ide_context import IDE_CONTEXT_FILE_ENV, IDE_CONTEXT_TOKEN_ENV
from .ide_discovery import discover_ide_connection


def prepare_ide_connection(args: argparse.Namespace) -> None:
    if not getattr(args, "ide", False):
        return
    root = resolve_project_root(args.cwd) or Path.cwd().resolve()
    connection = discover_ide_connection(root)
    os.environ[IDE_CONTEXT_FILE_ENV] = str(connection.context_file)
    os.environ[IDE_CONTEXT_TOKEN_ENV] = connection.token


__all__ = ["prepare_ide_connection"]
