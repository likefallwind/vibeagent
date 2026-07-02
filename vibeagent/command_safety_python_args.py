from __future__ import annotations

import ast
import shlex


def python_executable_command_from_args(args: list[ast.expr], path_index: int, argv_index: int | None) -> str | None:
    return python_executable_command_from_values(
        args=args,
        path_expr=args[path_index] if len(args) > path_index else None,
        argv_expr=args[argv_index] if argv_index is not None and len(args) > argv_index else None,
        path_index=path_index,
        argv_index=argv_index,
    )


def python_executable_command_from_call(
    node: ast.Call,
    path_index: int,
    argv_index: int | None,
    path_keyword_names: tuple[str, ...] = ("path", "file"),
    argv_keyword_names: tuple[str, ...] = ("args", "argv"),
) -> str | None:
    path_expr = node.args[path_index] if len(node.args) > path_index else python_keyword_value(node, path_keyword_names)
    argv_expr = None
    if argv_index is not None:
        argv_expr = node.args[argv_index] if len(node.args) > argv_index else python_keyword_value(node, argv_keyword_names)
    return python_executable_command_from_values(
        args=node.args,
        path_expr=path_expr,
        argv_expr=argv_expr,
        path_index=path_index,
        argv_index=argv_index,
    )


def python_executable_command_from_values(
    args: list[ast.expr],
    path_expr: ast.expr | None,
    argv_expr: ast.expr | None,
    path_index: int,
    argv_index: int | None,
) -> str | None:
    if path_expr is None:
        return None
    path = python_string_constant(path_expr)
    if path is None:
        return None
    parts = [path]
    if argv_index is not None:
        if argv_expr is None:
            return shlex.join(parts)
        argv = python_string_sequence(argv_expr)
        if argv:
            parts.extend(argv)
        return shlex.join(parts)
    for arg in args[path_index + 1 :]:
        value = python_string_constant(arg)
        if value is None:
            break
        parts.append(value)
    return shlex.join(parts)


def python_keyword_value(node: ast.Call, names: tuple[str, ...]) -> ast.expr | None:
    for keyword in node.keywords:
        if keyword.arg in names:
            return keyword.value
    return None


def python_string_constant(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def python_string_sequence(node: ast.expr) -> list[str] | None:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    values: list[str] = []
    for item in node.elts:
        value = python_string_constant(item)
        if value is None:
            return None
        values.append(value)
    return values


def python_command_argument(node: ast.Call, keyword_names: tuple[str, ...] = ("args", "command", "cmd")) -> str | None:
    command_arg = node.args[0] if node.args else None
    if command_arg is None:
        command_arg = python_keyword_value(node, keyword_names)
    if command_arg is None:
        return None
    if isinstance(command_arg, ast.Constant) and isinstance(command_arg.value, str):
        return command_arg.value
    if isinstance(command_arg, (ast.List, ast.Tuple)):
        parts: list[str] = []
        for item in command_arg.elts:
            if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
                return None
            parts.append(item.value)
        return shlex.join(parts)
    return None
