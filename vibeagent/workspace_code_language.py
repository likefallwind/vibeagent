from __future__ import annotations

import re
from pathlib import Path


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


__all__ = [
    "apply_code_rename_replacements",
    "build_code_reference_pattern",
    "code_language_for_path",
    "collect_code_imports",
    "collect_code_rename_replacements",
    "collect_generic_code_outline",
    "generic_symbol_matches",
    "is_generic_import_line",
    "parse_code_import_line",
    "parse_go_import_line",
    "supports_code_outline_path",
]
