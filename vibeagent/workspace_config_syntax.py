from __future__ import annotations

import json
import tomllib
from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_file_read import read_utf8_text_file
from .workspace_resolve import resolve_inside_run
from .workspace_search_files import list_search_files


def check_config_syntax(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_files: int = 200,
) -> tuple[list[dict[str, object]], int]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")

    files = [path for path in list_search_files(workspace, relative_path) if config_format_for_path(path) is not None]
    results: list[dict[str, object]] = []
    for relative in files[:max_files]:
        target = resolve_inside_run(workspace, relative)
        config_format = config_format_for_path(relative) or "unknown"
        try:
            content = read_utf8_text_file(target, relative)
            if config_format == "json":
                json.loads(content)
            elif config_format == "toml":
                tomllib.loads(content)
            results.append(
                {
                    "path": relative,
                    "ok": True,
                    "format": config_format,
                    "line": None,
                    "column": None,
                    "message": "Syntax OK.",
                }
            )
        except json.JSONDecodeError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "format": config_format,
                    "line": error.lineno,
                    "column": error.colno,
                    "message": f"JSON syntax error: {error.msg}",
                }
            )
        except tomllib.TOMLDecodeError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "format": config_format,
                    "line": None,
                    "column": None,
                    "message": f"TOML syntax error: {error}",
                }
            )
        except ValueError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "format": config_format,
                    "line": None,
                    "column": None,
                    "message": str(error),
                }
            )
    return results, len(files)


def config_format_for_path(path: str | Path) -> str | None:
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix == ".toml":
        return "toml"
    return None


def check_config_file_paths(
    workspace: RunWorkspace,
    relative_paths: list[str],
    max_files: int = 200,
) -> tuple[list[dict[str, object]], int]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")

    files: list[str] = []
    seen: set[str] = set()
    for relative in relative_paths:
        if relative in seen or config_format_for_path(relative) is None:
            continue
        try:
            target = resolve_inside_run(workspace, relative)
        except ValueError:
            continue
        if not target.is_file():
            continue
        seen.add(relative)
        files.append(relative)

    results: list[dict[str, object]] = []
    for relative in files[:max_files]:
        scoped_results, _total = check_config_syntax(workspace, relative, max_files=1)
        results.extend(scoped_results)
    return results, len(files)
