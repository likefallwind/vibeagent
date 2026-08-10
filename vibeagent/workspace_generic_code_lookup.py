from __future__ import annotations

from pathlib import Path

from .workspace_code_language import (
    build_code_reference_pattern,
    code_language_for_path,
    collect_code_imports,
    collect_generic_code_outline,
    supports_code_outline_path,
)
from .workspace_core import RunWorkspace
from .workspace_file_read import read_utf8_text_file
from .workspace_python_intel import read_python_symbol_outline
from .workspace_resolve import resolve_inside_run
from .workspace_search_files import list_search_files


def read_code_outline(workspace: RunWorkspace, relative_path: str, max_symbols: int = 200) -> dict[str, object]:
    if max_symbols < 1:
        raise ValueError("max_symbols must be at least 1.")
    if max_symbols > 1000:
        raise ValueError("max_symbols must be at most 1000.")

    target = resolve_inside_run(workspace, relative_path)
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
        target = resolve_inside_run(workspace, relative)
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
        target = resolve_inside_run(workspace, relative)
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
            target = resolve_inside_run(workspace, relative)
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
