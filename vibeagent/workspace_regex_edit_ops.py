from __future__ import annotations

import re
from pathlib import Path

from .workspace_code_intel import build_simple_diff
from .workspace_core import RunWorkspace
from .workspace_file_read import read_utf8_text_file
from .workspace_resolve import resolve_mutation_path


def regex_replace_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    pattern: str,
    replacement: str,
    count: int = 0,
    case_sensitive: bool = True,
    multiline: bool = False,
    max_replacements: int = 100,
) -> tuple[Path, int, str]:
    target, after, replacements, diff = build_regex_replacement(
        workspace,
        relative_path,
        pattern,
        replacement,
        count=count,
        case_sensitive=case_sensitive,
        multiline=multiline,
        max_replacements=max_replacements,
    )
    target.write_text(after, encoding="utf-8")
    return target, replacements, diff


def preview_regex_replace_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    pattern: str,
    replacement: str,
    count: int = 0,
    case_sensitive: bool = True,
    multiline: bool = False,
    max_replacements: int = 100,
) -> tuple[Path, int, str]:
    target, _after, replacements, diff = build_regex_replacement(
        workspace,
        relative_path,
        pattern,
        replacement,
        count=count,
        case_sensitive=case_sensitive,
        multiline=multiline,
        max_replacements=max_replacements,
    )
    return target, replacements, diff


def build_regex_replacement(
    workspace: RunWorkspace,
    relative_path: str,
    pattern: str,
    replacement: str,
    count: int = 0,
    case_sensitive: bool = True,
    multiline: bool = False,
    max_replacements: int = 100,
) -> tuple[Path, str, int, str]:
    if pattern == "":
        raise ValueError("pattern must not be empty.")
    if count < 0:
        raise ValueError("count must be non-negative.")
    if max_replacements < 1:
        raise ValueError("max_replacements must be at least 1.")

    target = resolve_mutation_path(workspace, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    before = read_utf8_text_file(target, relative_path)
    flags = 0
    if not case_sensitive:
        flags |= re.IGNORECASE
    if multiline:
        flags |= re.MULTILINE
    try:
        compiled = re.compile(pattern, flags)
    except re.error as error:
        raise ValueError(f"Invalid regex pattern: {error}") from error

    matches = list(compiled.finditer(before))
    if not matches:
        raise ValueError(f"Pattern was not found in {relative_path}")
    replacements_to_apply = len(matches) if count == 0 else min(count, len(matches))
    if replacements_to_apply > max_replacements:
        raise ValueError(f"Regex replacement would change {replacements_to_apply} matches, above max_replacements {max_replacements}.")
    try:
        after, replacements = compiled.subn(replacement, before, count=count)
    except re.error as error:
        raise ValueError(f"Invalid regex replacement: {error}") from error
    if replacements > max_replacements:
        raise ValueError(f"Regex replacement changed {replacements} matches, above max_replacements {max_replacements}.")
    if after == before:
        raise ValueError(f"Regex replacement made no changes to {relative_path}")
    return target, after, replacements, build_simple_diff(relative_path, before, after)
