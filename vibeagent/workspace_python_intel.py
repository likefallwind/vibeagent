from __future__ import annotations

import ast
import re
from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_diff_utils import build_simple_diff
from .workspace_file_read import read_utf8_text_file
from .workspace_python_outline import (
    collect_python_imports,
    collect_python_symbols,
    format_import_alias,
    import_line_number,
    read_python_symbol_outline,
)
from .workspace_python_analysis import (
    build_python_module_index,
    check_python_file_paths,
    check_python_syntax,
    collect_python_dependency_imports,
    inspect_python_dependencies,
    is_local_python_module,
    module_name_for_python_path,
    python_import_sort_key,
    resolve_import_from_module,
    resolve_import_target,
)
from .workspace_search_files import list_files, list_search_files
from .workspace_python_symbols import (
    apply_python_rename_replacements,
    call_matches_symbol,
    collect_python_call_graph_edges,
    collect_python_call_matches,
    collect_python_references,
    collect_python_rename_replacements,
    find_identifier_column,
    python_call_name,
)
from .workspace_python_definitions import (
    collect_python_definition_matches,
    find_python_definitions,
    preview_replace_python_definition,
    python_definition_start_line,
    replace_python_definition,
)
from .workspace_resolve import resolve_inside_run, resolve_mutation_path


def find_python_calls(
    workspace: RunWorkspace,
    symbol: str,
    relative_path: str | None = None,
    max_matches: int = 200,
) -> tuple[list[dict[str, object]], int, list[str]]:
    symbol = symbol.strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$", symbol):
        raise ValueError("Python symbol must be a valid identifier or dotted identifier.")
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 500:
        raise ValueError("max_matches must be at most 500.")

    calls: list[dict[str, object]] = []
    errors: list[str] = []
    for relative in list_search_files(workspace, relative_path):
        if Path(relative).suffix != ".py":
            continue
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
            tree = ast.parse(content, filename=relative)
        except ValueError as error:
            errors.append(str(error))
            continue
        except SyntaxError as error:
            line = error.lineno or "unknown"
            errors.append(f"Python syntax error in {relative} at line {line}: {error.msg}")
            continue

        calls.extend(collect_python_call_matches(tree, symbol, relative, content.splitlines()))

    calls.sort(key=lambda item: (str(item["path"]), int(item["line"]), int(item["column"]), str(item["callee"])))
    return calls[:max_matches], len(calls), errors

def inspect_python_call_graph(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_files: int = 100,
    max_edges: int = 500,
) -> tuple[list[dict[str, object]], int, int, list[str]]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    if max_edges < 1:
        raise ValueError("max_edges must be at least 1.")
    if max_edges > 2000:
        raise ValueError("max_edges must be at most 2000.")

    files = [path for path in list_search_files(workspace, relative_path) if path.endswith(".py")]
    edges: list[dict[str, object]] = []
    errors: list[str] = []
    for relative in files[:max_files]:
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
            tree = ast.parse(content, filename=relative)
        except ValueError as error:
            errors.append(str(error))
            continue
        except SyntaxError as error:
            line = error.lineno or "unknown"
            errors.append(f"Python syntax error in {relative} at line {line}: {error.msg}")
            continue

        edges.extend(collect_python_call_graph_edges(tree, relative, content.splitlines()))

    edges.sort(key=lambda item: (str(item["path"]), int(item["line"]), int(item["column"]), str(item["callee"])))
    return edges[:max_edges], len(edges), len(files), errors

def preview_python_rename(
    workspace: RunWorkspace,
    symbol: str,
    new_name: str,
    relative_path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 500,
) -> dict[str, object]:
    symbol = symbol.strip()
    new_name = new_name.strip()
    identifier_pattern = r"^[A-Za-z_][A-Za-z0-9_]*$"
    if not re.match(identifier_pattern, symbol):
        raise ValueError("Python rename symbol must be a simple identifier.")
    if not re.match(identifier_pattern, new_name):
        raise ValueError("Python rename new_name must be a simple identifier.")
    if symbol == new_name:
        raise ValueError("Python rename new_name must be different from symbol.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    if max_replacements < 1:
        raise ValueError("max_replacements must be at least 1.")
    if max_replacements > 2000:
        raise ValueError("max_replacements must be at most 2000.")

    files = [path for path in list_search_files(workspace, relative_path) if path.endswith(".py")]
    preview_files: list[dict[str, object]] = []
    total_replacements = 0
    errors: list[str] = []
    remaining = max_replacements
    for relative in files[:max_files]:
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
            tree = ast.parse(content, filename=relative)
        except ValueError as error:
            errors.append(str(error))
            continue
        except SyntaxError as error:
            line = error.lineno or "unknown"
            errors.append(f"Python syntax error in {relative} at line {line}: {error.msg}")
            continue

        lines = content.splitlines(keepends=True)
        replacements = collect_python_rename_replacements(tree, symbol, new_name, relative, lines)
        if not replacements:
            continue
        total_replacements += len(replacements)
        shown_replacements = replacements[:remaining]
        remaining = max(0, remaining - len(shown_replacements))
        if not shown_replacements:
            continue
        updated = apply_python_rename_replacements(content, shown_replacements)
        preview_files.append(
            {
                "path": relative,
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
        "message": f"Found {total_replacements} Python rename replacement(s) across {len(files)} file(s).",
    }

def apply_python_rename(
    workspace: RunWorkspace,
    symbol: str,
    new_name: str,
    relative_path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 2000,
) -> dict[str, object]:
    preview = preview_python_rename(
        workspace,
        symbol,
        new_name,
        relative_path=relative_path,
        max_files=max_files,
        max_replacements=max_replacements,
    )
    if preview["errors"]:
        raise ValueError(f"Python rename skipped {len(preview['errors'])} file(s); fix syntax/read errors first.")
    if int(preview["total_files"]) > max_files:
        raise ValueError(f"Python rename scope has {preview['total_files']} file(s); max_files is {max_files}.")
    if bool(preview["truncated"]):
        raise ValueError(f"Python rename has more than {max_replacements} replacement(s).")
    if int(preview["total_replacements"]) == 0:
        raise ValueError(f"Python rename found no replacements for {symbol}.")

    prepared: list[tuple[Path, str, str, str]] = []
    for file in list(preview["files"]):
        relative = str(file["path"])
        target = resolve_mutation_path(workspace.root, relative)
        before = read_utf8_text_file(target, relative)
        after = apply_python_rename_replacements(before, list(file["replacements"]))
        try:
            ast.parse(after, filename=relative)
        except SyntaxError as error:
            line = error.lineno or "unknown"
            raise ValueError(f"Python rename would create syntax error in {relative} at line {line}: {error.msg}") from error
        prepared.append((target, relative, before, after))

    for target, _, _, after in prepared:
        target.write_text(after, encoding="utf-8")

    return {
        **preview,
        "diff": "".join(build_simple_diff(relative, before, after) for _, relative, before, after in prepared),
    }

def find_python_references(
    workspace: RunWorkspace,
    symbol: str,
    relative_path: str | None = None,
    max_matches: int = 200,
) -> tuple[list[dict[str, object]], int, list[str]]:
    symbol = symbol.strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", symbol):
        raise ValueError("Python symbol must be a valid identifier.")
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 500:
        raise ValueError("max_matches must be at most 500.")

    references: list[dict[str, object]] = []
    errors: list[str] = []
    for relative in list_search_files(workspace, relative_path):
        if Path(relative).suffix != ".py":
            continue
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
            tree = ast.parse(content, filename=relative)
        except ValueError as error:
            errors.append(str(error))
            continue
        except SyntaxError as error:
            line = error.lineno or "unknown"
            errors.append(f"Python syntax error in {relative} at line {line}: {error.msg}")
            continue

        lines = content.splitlines()
        references.extend(collect_python_references(tree, symbol, relative, lines))

    references.sort(key=lambda item: (str(item["path"]), int(item["line"]), int(item["column"]), str(item["kind"])))
    return references[:max_matches], len(references), errors
