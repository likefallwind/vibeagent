from __future__ import annotations

import ast
import re
from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_diff_utils import build_simple_diff, split_replacement_lines
from .workspace_file_read import format_line_excerpt, read_utf8_text_file
from .workspace_resolve import resolve_inside_run, resolve_mutation_path
from .workspace_search_files import list_search_files


def find_python_definitions(
    workspace: RunWorkspace,
    symbol: str,
    relative_path: str | None = None,
    max_matches: int = 50,
    max_lines: int = 120,
) -> tuple[list[dict[str, object]], int, list[str]]:
    symbol = symbol.strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$", symbol):
        raise ValueError("Python symbol must be a valid identifier or dotted identifier.")
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 200:
        raise ValueError("max_matches must be at most 200.")
    if max_lines < 1:
        raise ValueError("max_lines must be at least 1.")
    if max_lines > 1000:
        raise ValueError("max_lines must be at most 1000.")

    definitions: list[dict[str, object]] = []
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

        definitions.extend(collect_python_definition_matches(tree, symbol, relative, content, max_lines=max_lines))

    definitions.sort(key=lambda item: (str(item["path"]), int(item["line"]), str(item["qualified_name"])))
    return definitions[:max_matches], len(definitions), errors


def replace_python_definition(
    workspace: RunWorkspace,
    symbol: str,
    new_content: str,
    relative_path: str | None = None,
) -> tuple[Path, str, dict[str, object]]:
    target, after, diff, definition = preview_replace_python_definition(
        workspace,
        symbol,
        new_content,
        relative_path=relative_path,
    )
    target.write_text(after, encoding="utf-8")
    return target, diff, definition


def preview_replace_python_definition(
    workspace: RunWorkspace,
    symbol: str,
    new_content: str,
    relative_path: str | None = None,
) -> tuple[Path, str, str, dict[str, object]]:
    if not new_content.strip():
        raise ValueError("Replacement content must not be empty.")

    definitions, total, _ = find_python_definitions(
        workspace,
        symbol,
        relative_path=relative_path,
        max_matches=2,
        max_lines=1,
    )
    if total == 0:
        raise ValueError(f"Python definition not found: {symbol}")
    if total > 1:
        raise ValueError(f"Python definition is ambiguous: found {total} matches for {symbol}")

    definition = definitions[0]
    path = str(definition["path"])
    start_line = int(definition["line"])
    end_line = int(definition["end_line"])
    target = resolve_mutation_path(workspace.root, path)
    before = read_utf8_text_file(target, path)
    lines = before.splitlines(keepends=True)

    replacement = split_replacement_lines(new_content)
    after = "".join(lines[: start_line - 1] + replacement + lines[end_line:])
    if after == before:
        raise ValueError(f"Python definition replacement made no changes to {path}")

    try:
        ast.parse(after, filename=path)
    except SyntaxError as error:
        line = error.lineno or "unknown"
        raise ValueError(f"Replacement would create Python syntax error in {path} at line {line}: {error.msg}") from error

    return target, after, build_simple_diff(path, before, after), definition


def collect_python_definition_matches(
    tree: ast.AST,
    symbol: str,
    relative_path: str,
    content: str,
    max_lines: int,
) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    wanted_name = symbol.rsplit(".", 1)[-1]

    def visit_body(nodes: list[ast.stmt], parent: str | None = None) -> None:
        for node in nodes:
            kind: str | None = None
            if isinstance(node, ast.ClassDef):
                kind = "class"
            elif isinstance(node, ast.AsyncFunctionDef):
                kind = "async_function"
            elif isinstance(node, ast.FunctionDef):
                kind = "function"

            if kind is not None:
                qualified_name = node.name if parent is None else f"{parent}.{node.name}"
                if node.name == wanted_name and (symbol == wanted_name or symbol == qualified_name):
                    end_line = getattr(node, "end_lineno", None) or node.lineno
                    start_line = python_definition_start_line(node)
                    line_count = min(max_lines, end_line - start_line + 1)
                    matches.append(
                        {
                            "path": relative_path,
                            "name": node.name,
                            "qualified_name": qualified_name,
                            "kind": kind,
                            "line": start_line,
                            "end_line": end_line,
                            "parent": parent,
                            "content": format_line_excerpt(content, start_line, line_count),
                            "truncated": line_count < end_line - start_line + 1,
                            "message": f"Found {kind} {qualified_name}.",
                        }
                    )
                visit_body(node.body, qualified_name)
            else:
                child_body = getattr(node, "body", None)
                if isinstance(child_body, list):
                    visit_body(child_body, parent)

    visit_body(getattr(tree, "body", []))
    return matches


def python_definition_start_line(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    decorator_lines = [decorator.lineno for decorator in node.decorator_list if hasattr(decorator, "lineno")]
    return min([node.lineno, *decorator_lines])
