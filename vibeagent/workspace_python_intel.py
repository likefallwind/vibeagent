from __future__ import annotations

import ast
import re
from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_diff_utils import build_simple_diff, split_replacement_lines
from .workspace_file_read import format_line_excerpt, read_utf8_text_file
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
from .workspace_project_info import list_files, list_search_files
from .workspace_resolve import resolve_inside_run, resolve_mutation_path


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

def collect_python_call_graph_edges(
    tree: ast.AST,
    relative_path: str,
    lines: list[str],
) -> list[dict[str, object]]:
    edges: list[dict[str, object]] = []
    scope_stack: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            scope_stack.append(node.name if not scope_stack else f"{scope_stack[-1]}.{node.name}")
            self.generic_visit(node)
            scope_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.visit_function_scope(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.visit_function_scope(node)

        def visit_function_scope(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            scope_stack.append(node.name if not scope_stack else f"{scope_stack[-1]}.{node.name}")
            self.generic_visit(node)
            scope_stack.pop()

        def visit_Call(self, node: ast.Call) -> None:
            callee = python_call_name(node.func)
            if callee:
                line = getattr(node, "lineno", 0)
                column = getattr(node, "col_offset", 0)
                edges.append(
                    {
                        "path": relative_path,
                        "line": int(line),
                        "column": int(column),
                        "callee": callee,
                        "caller": scope_stack[-1] if scope_stack else None,
                        "context": lines[line - 1].strip() if 1 <= line <= len(lines) else "",
                    }
                )
            self.generic_visit(node)

    Visitor().visit(tree)
    return edges

def collect_python_call_matches(
    tree: ast.AST,
    symbol: str,
    relative_path: str,
    lines: list[str],
) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []
    wanted_tail = symbol.rsplit(".", 1)[-1]
    scope_stack: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            scope_stack.append(node.name if not scope_stack else f"{scope_stack[-1]}.{node.name}")
            self.generic_visit(node)
            scope_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.visit_function_scope(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.visit_function_scope(node)

        def visit_function_scope(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            scope_stack.append(node.name if not scope_stack else f"{scope_stack[-1]}.{node.name}")
            self.generic_visit(node)
            scope_stack.pop()

        def visit_Call(self, node: ast.Call) -> None:
            callee = python_call_name(node.func)
            if call_matches_symbol(callee, symbol, wanted_tail):
                line = getattr(node, "lineno", 0)
                column = getattr(node, "col_offset", 0)
                calls.append(
                    {
                        "path": relative_path,
                        "line": int(line),
                        "column": int(column),
                        "callee": callee,
                        "caller": scope_stack[-1] if scope_stack else None,
                        "context": lines[line - 1].strip() if 1 <= line <= len(lines) else "",
                    }
                )
            self.generic_visit(node)

    Visitor().visit(tree)
    return calls

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

def collect_python_rename_replacements(
    tree: ast.AST,
    symbol: str,
    new_name: str,
    relative_path: str,
    lines: list[str],
) -> list[dict[str, object]]:
    replacements: list[dict[str, object]] = []
    seen: set[tuple[int, int, int]] = set()

    def add_replacement(line: int, column: int, end_column: int, kind: str) -> None:
        if line < 1 or line > len(lines) or column < 0 or end_column <= column:
            return
        text = lines[line - 1]
        if text[column:end_column] != symbol:
            return
        key = (line, column, end_column)
        if key in seen:
            return
        seen.add(key)
        replacements.append(
            {
                "path": relative_path,
                "line": line,
                "column": column,
                "end_column": end_column,
                "kind": kind,
                "old": symbol,
                "new": new_name,
                "context": text.strip(),
            }
        )

    class Visitor(ast.NodeVisitor):
        def visit_Name(self, node: ast.Name) -> None:
            if node.id == symbol:
                add_replacement(node.lineno, node.col_offset, getattr(node, "end_col_offset", node.col_offset + len(symbol)), "name")

        def visit_Attribute(self, node: ast.Attribute) -> None:
            if node.attr == symbol:
                end_column = getattr(node, "end_col_offset", node.col_offset)
                add_replacement(node.lineno, end_column - len(symbol), end_column, "attribute")
            self.generic_visit(node)

        def visit_arg(self, node: ast.arg) -> None:
            if node.arg == symbol:
                add_replacement(node.lineno, node.col_offset, node.col_offset + len(symbol), "argument")

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.visit_function(node, "function")

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.visit_function(node, "async_function")

        def visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str) -> None:
            if node.name == symbol:
                column = find_identifier_column(lines[node.lineno - 1], symbol, node.col_offset)
                add_replacement(node.lineno, column, column + len(symbol), kind)
            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            if node.name == symbol:
                column = find_identifier_column(lines[node.lineno - 1], symbol, node.col_offset)
                add_replacement(node.lineno, column, column + len(symbol), "class")
            self.generic_visit(node)

    Visitor().visit(tree)
    replacements.sort(key=lambda item: (str(item["path"]), int(item["line"]), int(item["column"])))
    return replacements

def find_identifier_column(line: str, symbol: str, start: int) -> int:
    column = line.find(symbol, max(0, start))
    return column if column >= 0 else start

def apply_python_rename_replacements(content: str, replacements: list[dict[str, object]]) -> str:
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

def python_call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = python_call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return python_call_name(node.func)
    if isinstance(node, ast.Subscript):
        return python_call_name(node.value)
    return ""

def call_matches_symbol(callee: str, symbol: str, wanted_tail: str) -> bool:
    if not callee:
        return False
    if "." in symbol:
        return callee == symbol or callee.endswith(f".{symbol}")
    return callee == symbol or callee.rsplit(".", 1)[-1] == wanted_tail

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

def collect_python_references(
    tree: ast.AST,
    symbol: str,
    relative_path: str,
    lines: list[str],
) -> list[dict[str, object]]:
    references: list[dict[str, object]] = []
    seen: set[tuple[int, int, str]] = set()

    def add(node: ast.AST, kind: str, column: int | None = None) -> None:
        line = getattr(node, "lineno", None)
        if not isinstance(line, int):
            return
        col = column if column is not None else getattr(node, "col_offset", 0)
        key = (line, int(col), kind)
        if key in seen:
            return
        seen.add(key)
        context = lines[line - 1].strip() if 1 <= line <= len(lines) else ""
        references.append(
            {
                "path": relative_path,
                "line": line,
                "column": int(col),
                "kind": kind,
                "context": context,
            }
        )

    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
            add(node, "definition")
        elif isinstance(node, ast.Name) and node.id == symbol:
            add(node, "reference")
        elif isinstance(node, ast.Attribute) and node.attr == symbol:
            attr_column = getattr(node, "end_col_offset", None)
            if isinstance(attr_column, int):
                attr_column -= len(symbol)
            add(node, "reference", column=attr_column)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname == symbol or alias.name.split(".", 1)[0] == symbol:
                    add(node, "import")
                    break
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_name = alias.asname or alias.name
                if imported_name == symbol:
                    add(node, "import")
                    break

    return references
