from __future__ import annotations

import ast


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


def find_identifier_column(line: str, symbol: str, start: int) -> int:
    column = line.find(symbol, max(0, start))
    return column if column >= 0 else start


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


__all__ = [
    "apply_python_rename_replacements",
    "call_matches_symbol",
    "collect_python_call_graph_edges",
    "collect_python_call_matches",
    "collect_python_references",
    "collect_python_rename_replacements",
    "find_identifier_column",
    "python_call_name",
]
