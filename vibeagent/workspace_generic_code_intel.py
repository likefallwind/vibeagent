from __future__ import annotations

from pathlib import Path

from .workspace_code_language import (
    apply_code_rename_replacements,
    build_code_reference_pattern,
    code_language_for_path,
    collect_code_rename_replacements,
)
from .workspace_core import RunWorkspace
from .workspace_diff_utils import build_simple_diff
from .workspace_file_read import read_utf8_text_file
from .workspace_generic_code_lookup import (
    find_code_definitions,
    find_code_references,
    inspect_code_dependencies,
    read_code_outline,
)
from .workspace_resolve import resolve_inside_run, resolve_mutation_path
from .workspace_search_files import list_search_files


def preview_code_rename(
    workspace: RunWorkspace,
    symbol: str,
    new_name: str,
    relative_path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 500,
) -> dict[str, object]:
    symbol = symbol.strip()
    new_name = new_name.strip()
    if not symbol:
        raise ValueError("Code rename symbol must not be empty.")
    if not new_name:
        raise ValueError("Code rename new_name must not be empty.")
    if "\n" in symbol or "\r" in symbol or "\n" in new_name or "\r" in new_name:
        raise ValueError("Code rename symbol and new_name must be single-line strings.")
    if symbol == new_name:
        raise ValueError("Code rename new_name must be different from symbol.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    if max_replacements < 1:
        raise ValueError("max_replacements must be at least 1.")
    if max_replacements > 2000:
        raise ValueError("max_replacements must be at most 2000.")

    files = [
        path
        for path in list_search_files(workspace, relative_path)
        if code_language_for_path(Path(path)) not in {"python", "text"}
    ]
    pattern = build_code_reference_pattern(symbol)
    preview_files: list[dict[str, object]] = []
    total_replacements = 0
    errors: list[str] = []
    remaining = max_replacements
    for relative in files[:max_files]:
        target = resolve_inside_run(workspace.root, relative)
        language = code_language_for_path(Path(relative))
        try:
            content = read_utf8_text_file(target, relative)
        except ValueError as error:
            errors.append(str(error))
            continue

        replacements = collect_code_rename_replacements(content, pattern, symbol, new_name, relative, language)
        if not replacements:
            continue
        total_replacements += len(replacements)
        shown_replacements = replacements[:remaining]
        remaining = max(0, remaining - len(shown_replacements))
        if not shown_replacements:
            continue
        updated = apply_code_rename_replacements(content, shown_replacements)
        preview_files.append(
            {
                "path": relative,
                "language": language,
                "replacements": shown_replacements,
                "diff": build_simple_diff(relative, content, updated),
                "truncated": len(shown_replacements) < len(replacements),
            }
        )

    return {
        "ok": True,
        "symbol": symbol,
        "new_name": new_name,
        "path": relative_path,
        "files": preview_files,
        "total_replacements": total_replacements,
        "total_files": len(files),
        "truncated": total_replacements > max_replacements,
        "errors": errors,
        "message": f"Found {total_replacements} code rename replacement(s) across {len(files)} file(s).",
    }


def apply_code_rename(
    workspace: RunWorkspace,
    symbol: str,
    new_name: str,
    relative_path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 2000,
) -> dict[str, object]:
    preview = preview_code_rename(
        workspace,
        symbol,
        new_name,
        relative_path=relative_path,
        max_files=max_files,
        max_replacements=max_replacements,
    )
    if preview["errors"]:
        raise ValueError(f"Code rename skipped {len(preview['errors'])} file(s); fix read errors first.")
    if int(preview["total_files"]) > max_files:
        raise ValueError(f"Code rename scope has {preview['total_files']} file(s); max_files is {max_files}.")
    if bool(preview["truncated"]):
        raise ValueError(f"Code rename has more than {max_replacements} replacement(s).")
    if int(preview["total_replacements"]) == 0:
        raise ValueError(f"Code rename found no replacements for {symbol}.")

    prepared: list[tuple[Path, str, str, str]] = []
    for file in list(preview["files"]):
        relative = str(file["path"])
        target = resolve_mutation_path(workspace.root, relative)
        before = read_utf8_text_file(target, relative)
        after = apply_code_rename_replacements(before, list(file["replacements"]))
        prepared.append((target, relative, before, after))

    for target, _, _, after in prepared:
        target.write_text(after, encoding="utf-8")

    return {
        **preview,
        "diff": "".join(build_simple_diff(relative, before, after) for _, relative, before, after in prepared),
    }
