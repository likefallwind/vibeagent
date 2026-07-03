from __future__ import annotations

import ast

from .command_safety_python_introspection import python_dynamic_import_name, python_getattr_attribute


def python_call_is_webbrowser_open(
    node: ast.Call,
    module_aliases: set[str],
    function_aliases: set[str],
    get_function_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    func = node.func
    if isinstance(func, ast.Name) and func.id in function_aliases:
        return True
    if isinstance(func, ast.Call):
        attr = python_getattr_attribute(func, module_aliases, builtins_aliases, importlib_aliases, import_module_aliases)
        return attr is not None and attr.startswith("open")
    if not isinstance(func, ast.Attribute) or not func.attr.startswith("open"):
        return False
    if isinstance(func.value, ast.Name) and func.value.id in module_aliases:
        return True
    if not isinstance(func.value, ast.Call):
        return False
    if python_call_is_webbrowser_get(func.value, module_aliases, get_function_aliases, builtins_aliases, importlib_aliases, import_module_aliases):
        return True
    return python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "webbrowser"


def python_call_is_webbrowser_get(
    node: ast.Call,
    module_aliases: set[str],
    function_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    func = node.func
    if isinstance(func, ast.Name) and func.id in function_aliases:
        return True
    if isinstance(func, ast.Call):
        return python_getattr_attribute(func, module_aliases, builtins_aliases, importlib_aliases, import_module_aliases) == "get"
    if isinstance(func, ast.Attribute) and func.attr == "get":
        if isinstance(func.value, ast.Name) and func.value.id in module_aliases:
            return True
        if isinstance(func.value, ast.Call) and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "webbrowser":
            return True
    return False


def python_call_is_os_startfile(
    node: ast.Call,
    module_aliases: set[str],
    function_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    func = node.func
    if isinstance(func, ast.Name) and func.id in function_aliases:
        return True
    if isinstance(func, ast.Call):
        return python_getattr_attribute(func, module_aliases, builtins_aliases, importlib_aliases, import_module_aliases) == "startfile"
    if not isinstance(func, ast.Attribute) or func.attr != "startfile":
        return False
    if isinstance(func.value, ast.Name) and func.value.id in module_aliases:
        return True
    if isinstance(func.value, ast.Call) and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "os":
        return True
    return False
