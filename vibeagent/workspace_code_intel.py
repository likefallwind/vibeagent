from __future__ import annotations

import json
import tomllib
from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_diff_utils import build_simple_diff, split_replacement_lines
from .workspace_code_language import (
    apply_code_rename_replacements,
    build_code_reference_pattern,
    code_language_for_path,
    collect_code_imports,
    collect_code_rename_replacements,
    collect_generic_code_outline,
    generic_symbol_matches,
    is_generic_import_line,
    parse_code_import_line,
    parse_go_import_line,
    supports_code_outline_path,
)
from .workspace_python_intel import (
    read_python_symbol_outline,
    check_python_syntax,
    check_python_file_paths,
    inspect_python_dependencies,
    build_python_module_index,
    module_name_for_python_path,
    collect_python_dependency_imports,
    resolve_import_from_module,
    resolve_import_target,
    is_local_python_module,
    python_import_sort_key,
    find_python_definitions,
    replace_python_definition,
    preview_replace_python_definition,
    collect_python_definition_matches,
    python_definition_start_line,
    find_python_calls,
    inspect_python_call_graph,
    collect_python_call_graph_edges,
    collect_python_call_matches,
    preview_python_rename,
    apply_python_rename,
    collect_python_rename_replacements,
    find_identifier_column,
    apply_python_rename_replacements,
    python_call_name,
    call_matches_symbol,
    find_python_references,
    collect_python_references,
    collect_python_imports,
    format_import_alias,
    import_line_number,
    collect_python_symbols,
)
from .workspace_file_read import format_line_excerpt, read_utf8_text_file
from .workspace_search_files import list_files, list_search_files
from .workspace_resolve import resolve_inside_run, resolve_mutation_path


def read_code_outline(workspace: RunWorkspace, relative_path: str, max_symbols: int = 200) -> dict[str, object]:
    if max_symbols < 1:
        raise ValueError("max_symbols must be at least 1.")
    if max_symbols > 1000:
        raise ValueError("max_symbols must be at most 1000.")

    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    suffix = target.suffix.lower()
    if suffix == ".py":
        outline = read_python_symbol_outline(workspace, relative_path, max_symbols=max_symbols)
        return {
            **outline,
            "language": "python",
        }

    content = read_utf8_text_file(target, relative_path)
    language = code_language_for_path(target)
    symbols, imports = collect_generic_code_outline(content, language, max_symbols=max_symbols)
    return {
        "path": relative_path,
        "ok": True,
        "language": language,
        "symbols": symbols,
        "imports": imports,
        "message": f"Found {len(symbols)} symbol(s) and {len(imports)} import(s).",
    }


def inspect_code_dependencies(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_files: int = 100,
    max_imports: int = 500,
) -> tuple[list[dict[str, object]], int]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    if max_imports < 1:
        raise ValueError("max_imports must be at least 1.")
    if max_imports > 2000:
        raise ValueError("max_imports must be at most 2000.")

    files = [
        path
        for path in list_search_files(workspace, relative_path)
        if supports_code_outline_path(path) and code_language_for_path(Path(path)) != "python"
    ]
    results: list[dict[str, object]] = []
    remaining_imports = max_imports
    for relative in files[:max_files]:
        target = resolve_inside_run(workspace.root, relative)
        language = code_language_for_path(target)
        if remaining_imports <= 0:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "language": language,
                    "imports": [],
                    "dependencies": [],
                    "message": "Import result limit reached.",
                }
            )
            continue
        try:
            content = read_utf8_text_file(target, relative)
            imports = collect_code_imports(content, language, max_imports=remaining_imports)
            remaining_imports -= len(imports)
            dependencies = sorted({str(item["source"]) for item in imports if str(item["source"])})
            results.append(
                {
                    "path": relative,
                    "ok": True,
                    "language": language,
                    "imports": imports,
                    "dependencies": dependencies,
                    "message": f"Found {len(imports)} import(s) and {len(dependencies)} dependency source(s).",
                }
            )
        except ValueError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "language": language,
                    "imports": [],
                    "dependencies": [],
                    "message": str(error),
                }
            )
    return results, len(files)


def find_code_references(
    workspace: RunWorkspace,
    symbol: str,
    relative_path: str | None = None,
    max_matches: int = 200,
) -> tuple[list[dict[str, object]], int]:
    symbol = symbol.strip()
    if not symbol:
        raise ValueError("Code reference symbol must not be empty.")
    if "\n" in symbol or "\r" in symbol:
        raise ValueError("Code reference symbol must be a single-line string.")
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 500:
        raise ValueError("max_matches must be at most 500.")

    pattern = build_code_reference_pattern(symbol)
    matches: list[dict[str, object]] = []
    total = 0
    for relative in list_search_files(workspace, relative_path):
        language = code_language_for_path(Path(relative))
        if language == "python" or language == "text":
            continue
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
        except ValueError:
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            for match in pattern.finditer(line):
                total += 1
                if len(matches) < max_matches:
                    matches.append(
                        {
                            "path": relative,
                            "language": language,
                            "line": line_number,
                            "column": match.start() + 1,
                            "symbol": symbol,
                            "context": line.strip(),
                        }
                    )
    return matches, total


def find_code_definitions(
    workspace: RunWorkspace,
    symbol: str,
    relative_path: str | None = None,
    max_matches: int = 50,
    max_lines: int = 80,
) -> tuple[list[dict[str, object]], int, list[str]]:
    symbol = symbol.strip()
    if not symbol:
        raise ValueError("Code definition symbol must not be empty.")
    if "\n" in symbol or "\r" in symbol:
        raise ValueError("Code definition symbol must be a single-line string.")
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 200:
        raise ValueError("max_matches must be at most 200.")
    if max_lines < 1:
        raise ValueError("max_lines must be at least 1.")
    if max_lines > 500:
        raise ValueError("max_lines must be at most 500.")

    definitions: list[dict[str, object]] = []
    total = 0
    errors: list[str] = []
    for relative in list_search_files(workspace, relative_path):
        language = code_language_for_path(Path(relative))
        if language == "python" or language == "text":
            continue
        try:
            outline = read_code_outline(workspace, relative, max_symbols=1000)
            symbols = list(outline["symbols"])
            target = resolve_inside_run(workspace.root, relative)
            content = read_utf8_text_file(target, relative)
        except ValueError as error:
            errors.append(str(error))
            continue
        lines = content.splitlines()
        for item in symbols:
            if str(item.get("name")) != symbol:
                continue
            total += 1
            if len(definitions) >= max_matches:
                continue
            line = int(item["line"])
            excerpt_lines = lines[line - 1 : line - 1 + max_lines]
            end_line = line + len(excerpt_lines) - 1
            definitions.append(
                {
                    "path": relative,
                    "language": language,
                    "name": symbol,
                    "kind": str(item["kind"]),
                    "line": line,
                    "end_line": end_line,
                    "content": "\n".join(excerpt_lines),
                    "truncated": len(lines) > end_line,
                    "message": f"Found {symbol} definition at line {line}.",
                }
            )
    return definitions, total, errors


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
        target = resolve_inside_run(workspace.root, relative)
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
            target = resolve_inside_run(workspace.root, relative)
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
