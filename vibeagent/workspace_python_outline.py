from __future__ import annotations

import ast
from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_file_read import read_utf8_text_file
from .workspace_resolve import resolve_inside_run


def read_python_symbol_outline(workspace: RunWorkspace, relative_path: str, max_symbols: int = 200) -> dict[str, object]:
    target = resolve_inside_run(workspace, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    if target.suffix != ".py":
        raise ValueError(f"File is not a Python source file: {relative_path}")
    content = read_utf8_text_file(target, relative_path)
    try:
        tree = ast.parse(content, filename=relative_path)
    except SyntaxError as error:
        line = error.lineno or "unknown"
        raise ValueError(f"Python syntax error in {relative_path} at line {line}: {error.msg}") from error

    imports = collect_python_imports(tree)
    symbols = collect_python_symbols(tree, max_symbols=max_symbols)
    return {
        "path": relative_path,
        "ok": True,
        "symbols": symbols,
        "imports": imports,
        "message": f"Found {len(symbols)} symbol(s) and {len(imports)} import(s).",
    }


def collect_python_imports(tree: ast.AST, max_imports: int = 100) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = ", ".join(format_import_alias(alias) for alias in node.names)
            imports.append(f"{node.lineno}: import {names}")
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            names = ", ".join(format_import_alias(alias) for alias in node.names)
            imports.append(f"{node.lineno}: from {module} import {names}")
        if len(imports) >= max_imports:
            break
    return sorted(imports, key=import_line_number)


def format_import_alias(alias: ast.alias) -> str:
    return f"{alias.name} as {alias.asname}" if alias.asname else alias.name


def import_line_number(value: str) -> int:
    try:
        return int(value.split(":", 1)[0])
    except ValueError:
        return 0


def collect_python_symbols(tree: ast.AST, max_symbols: int = 200) -> list[dict[str, object]]:
    symbols: list[dict[str, object]] = []

    def visit_body(nodes: list[ast.stmt], parent: str | None = None) -> None:
        for node in nodes:
            if len(symbols) >= max_symbols:
                return
            kind: str | None = None
            if isinstance(node, ast.ClassDef):
                kind = "class"
            elif isinstance(node, ast.AsyncFunctionDef):
                kind = "async_function"
            elif isinstance(node, ast.FunctionDef):
                kind = "function"

            if kind is not None:
                symbols.append(
                    {
                        "name": node.name,
                        "kind": kind,
                        "line": node.lineno,
                        "end_line": getattr(node, "end_lineno", None),
                        "parent": parent,
                    }
                )
                visit_body(node.body, node.name if parent is None else f"{parent}.{node.name}")
            else:
                child_body = getattr(node, "body", None)
                if isinstance(child_body, list):
                    visit_body(child_body, parent)

    visit_body(getattr(tree, "body", []))
    return symbols
