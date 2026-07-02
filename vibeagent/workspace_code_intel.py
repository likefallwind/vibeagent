from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_diff_utils import build_simple_diff, split_replacement_lines
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
from .workspace_project_info import list_files, list_search_files
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


def code_language_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".kt": "kotlin",
        ".c": "c",
        ".h": "c",
        ".cc": "cpp",
        ".cpp": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
    }.get(suffix, "text")


def supports_code_outline_path(path: str | Path) -> bool:
    return code_language_for_path(Path(path)) != "text"


def collect_generic_code_outline(content: str, language: str, max_symbols: int = 200) -> tuple[list[dict[str, object]], list[str]]:
    symbols: list[dict[str, object]] = []
    imports: list[str] = []
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith(("//", "#")):
            continue
        if is_generic_import_line(line, language):
            imports.append(f"{line_number}: {line}")
            continue
        for kind, name in generic_symbol_matches(line, language):
            symbols.append({"name": name, "kind": kind, "line": line_number, "end_line": None, "parent": None})
            if len(symbols) >= max_symbols:
                return symbols, imports
    return symbols, imports


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


def build_code_reference_pattern(symbol: str) -> re.Pattern[str]:
    escaped = re.escape(symbol)
    if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", symbol):
        return re.compile(rf"(?<![A-Za-z0-9_$]){escaped}(?![A-Za-z0-9_$])")
    return re.compile(escaped)


def collect_code_rename_replacements(
    content: str,
    pattern: re.Pattern[str],
    symbol: str,
    new_name: str,
    relative_path: str,
    language: str,
) -> list[dict[str, object]]:
    replacements: list[dict[str, object]] = []
    for line_number, line in enumerate(content.splitlines(keepends=True), start=1):
        for match in pattern.finditer(line):
            replacements.append(
                {
                    "path": relative_path,
                    "line": line_number,
                    "column": match.start(),
                    "end_column": match.end(),
                    "language": language,
                    "old": symbol,
                    "new": new_name,
                    "context": line.strip(),
                }
            )
    return replacements


def apply_code_rename_replacements(content: str, replacements: list[dict[str, object]]) -> str:
    lines = content.splitlines(keepends=True)
    by_line: dict[int, list[dict[str, object]]] = {}
    for replacement in replacements:
        by_line.setdefault(int(replacement["line"]), []).append(replacement)
    for line_number, line_replacements in by_line.items():
        line = lines[line_number - 1]
        for replacement in sorted(line_replacements, key=lambda item: int(item["column"]), reverse=True):
            column = int(replacement["column"])
            end_column = int(replacement["end_column"])
            line = f"{line[:column]}{replacement['new']}{line[end_column:]}"
        lines[line_number - 1] = line
    return "".join(lines)


def collect_code_imports(content: str, language: str, max_imports: int = 500) -> list[dict[str, object]]:
    imports: list[dict[str, object]] = []
    in_go_import_block = False
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith(("//", "#")) and not line.startswith("#include"):
            continue
        if language == "go":
            if line == "import (":
                in_go_import_block = True
                continue
            if in_go_import_block and line == ")":
                in_go_import_block = False
                continue
            parsed = parse_go_import_line(line, in_go_import_block)
        else:
            parsed = parse_code_import_line(line, language)
        if parsed is None:
            continue
        imports.append({"line": line_number, **parsed, "raw": line})
        if len(imports) >= max_imports:
            break
    return imports


def parse_code_import_line(line: str, language: str) -> dict[str, str] | None:
    if language in {"javascript", "typescript"}:
        side_effect = re.match(r"^import\s+['\"]([^'\"]+)['\"]", line)
        if side_effect:
            return {"kind": "import", "source": side_effect.group(1)}
        imported = re.match(r"^import\b.+?\bfrom\s+['\"]([^'\"]+)['\"]", line)
        if imported:
            return {"kind": "import", "source": imported.group(1)}
        exported = re.match(r"^export\b.+?\bfrom\s+['\"]([^'\"]+)['\"]", line)
        if exported:
            return {"kind": "export", "source": exported.group(1)}
    if language == "rust":
        match = re.match(r"^(?:pub\s+)?use\s+(.+?);?$", line)
        if match:
            return {"kind": "use", "source": match.group(1).rstrip(";")}
    if language in {"java", "kotlin"}:
        package = re.match(r"^package\s+([A-Za-z_][\w.]*)", line)
        if package:
            return {"kind": "package", "source": package.group(1)}
        imported = re.match(r"^import\s+(?:static\s+)?([A-Za-z_][\w.*]*)", line)
        if imported:
            return {"kind": "import", "source": imported.group(1)}
    if language in {"c", "cpp"}:
        include = re.match(r"^#include\s+([<\"].+[>\"])", line)
        if include:
            return {"kind": "include", "source": include.group(1)}
    return None


def parse_go_import_line(line: str, in_block: bool = False) -> dict[str, str] | None:
    if in_block:
        match = re.match(r"^(?:[._A-Za-z][\w.]*\s+)?\"([^\"]+)\"", line)
        if match:
            return {"kind": "import", "source": match.group(1)}
        return None
    imported = re.match(r"^import\s+(?:[._A-Za-z][\w.]*\s+)?\"([^\"]+)\"", line)
    if imported:
        return {"kind": "import", "source": imported.group(1)}
    return None


def is_generic_import_line(line: str, language: str) -> bool:
    if language in {"javascript", "typescript"}:
        return line.startswith("import ") or line.startswith("export ") and " from " in line
    if language == "go":
        return line.startswith("import ")
    if language == "rust":
        return line.startswith("use ")
    if language in {"java", "kotlin"}:
        return line.startswith("import ") or line.startswith("package ")
    if language in {"c", "cpp"}:
        return line.startswith("#include")
    return False


def generic_symbol_matches(line: str, language: str) -> list[tuple[str, str]]:
    matches: list[tuple[str, str]] = []
    if language in {"javascript", "typescript"}:
        patterns = [
            (r"^(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)", "class"),
            (r"^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", "function"),
            (r"^(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>", "function"),
            (r"^(?:export\s+)?(?:interface|type)\s+([A-Za-z_$][\w$]*)", "type"),
        ]
    elif language == "go":
        patterns = [
            (r"^func\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(", "function"),
            (r"^type\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:struct|interface)\b", "type"),
        ]
    elif language == "rust":
        patterns = [
            (r"^(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", "function"),
            (r"^(?:pub\s+)?(?:struct|enum|trait)\s+([A-Za-z_][A-Za-z0-9_]*)", "type"),
            (r"^impl(?:<[^>]+>)?\s+([A-Za-z_][A-Za-z0-9_]*)", "impl"),
        ]
    elif language in {"java", "kotlin"}:
        patterns = [
            (r"^(?:public|private|protected|internal|open|final|abstract|\s)*\s*(?:class|interface|enum)\s+([A-Za-z_][A-Za-z0-9_]*)", "type"),
            (r"^(?:public|private|protected|static|final|synchronized|abstract|\s)+[\w<>\[\], ?]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", "function"),
            (r"^fun\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", "function"),
        ]
    elif language in {"c", "cpp"}:
        patterns = [
            (r"^(?:class|struct|enum)\s+([A-Za-z_][A-Za-z0-9_]*)", "type"),
            (r"^[A-Za-z_][\w:<>\*&\s]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\s*(?:\{|$)", "function"),
        ]
    else:
        patterns = []

    for pattern, kind in patterns:
        match = re.match(pattern, line)
        if match:
            matches.append((kind, match.group(1)))
    return matches


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


