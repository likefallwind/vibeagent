from __future__ import annotations

import ast

from .command_safety_python_introspection import python_static_getattr_target


def python_literal_eval_exec_script(
    node: ast.Call,
    builtins_aliases: set[str],
    eval_exec_aliases: set[str],
    compile_aliases: set[str],
    compiled_literal_scripts: dict[str, str],
) -> str | None:
    if not python_call_is_eval_or_exec(node.func, builtins_aliases, eval_exec_aliases):
        return None
    if not node.args:
        return None
    source = node.args[0]
    literal = python_literal_source_text(source)
    if literal is not None:
        return literal
    if isinstance(source, ast.Name):
        return compiled_literal_scripts.get(source.id)
    return python_literal_compile_script(source, builtins_aliases, compile_aliases)


def python_call_is_eval_or_exec(func: ast.expr, builtins_aliases: set[str], eval_exec_aliases: set[str]) -> bool:
    return python_expr_is_eval_or_exec_reference(func, builtins_aliases, eval_exec_aliases)


def python_expr_is_eval_or_exec_reference(node: ast.AST, builtins_aliases: set[str], eval_exec_aliases: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in eval_exec_aliases
    if isinstance(node, ast.Attribute) and node.attr in {"eval", "exec"}:
        return isinstance(node.value, ast.Name) and node.value.id in builtins_aliases
    getattr_target = python_static_getattr_target(node)
    if getattr_target is None:
        return False
    target, attr = getattr_target
    return attr in {"eval", "exec"} and isinstance(target, ast.Name) and target.id in builtins_aliases


def python_literal_compile_script(source: ast.AST, builtins_aliases: set[str], compile_aliases: set[str]) -> str | None:
    if not isinstance(source, ast.Call) or not python_call_is_compile(source.func, builtins_aliases, compile_aliases):
        return None
    if len(source.args) < 3:
        return None
    code = source.args[0]
    mode = source.args[2]
    literal = python_literal_source_text(code)
    if literal is None:
        return None
    if not isinstance(mode, ast.Constant) or mode.value not in {"eval", "exec", "single"}:
        return None
    return literal


def python_literal_source_text(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Constant):
        return None
    if isinstance(node.value, str):
        return node.value
    if isinstance(node.value, bytes):
        try:
            return node.value.decode("utf-8")
        except UnicodeDecodeError:
            return None
    return None


def python_call_is_compile(func: ast.expr, builtins_aliases: set[str], compile_aliases: set[str]) -> bool:
    return python_expr_is_compile_reference(func, builtins_aliases, compile_aliases)


def python_expr_is_compile_reference(node: ast.AST, builtins_aliases: set[str], compile_aliases: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in compile_aliases
    if isinstance(node, ast.Attribute) and node.attr == "compile":
        return isinstance(node.value, ast.Name) and node.value.id in builtins_aliases
    getattr_target = python_static_getattr_target(node)
    if getattr_target is None:
        return False
    target, attr = getattr_target
    return attr == "compile" and isinstance(target, ast.Name) and target.id in builtins_aliases
