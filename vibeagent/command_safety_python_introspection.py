from __future__ import annotations

import ast


def python_dynamic_import_name(
    node: ast.Call,
    builtins_aliases: set[str] | None = None,
    importlib_aliases: set[str] | None = None,
    import_module_aliases: set[str] | None = None,
) -> str | None:
    importer = node
    builtins_aliases = builtins_aliases or {"builtins", "__builtins__"}
    importlib_aliases = importlib_aliases or {"importlib"}
    import_module_aliases = import_module_aliases or set()
    module_name = python_first_string_argument(importer)
    if module_name is None:
        return None
    if isinstance(importer.func, ast.Name) and importer.func.id == "__import__":
        return module_name
    if (
        isinstance(importer.func, ast.Attribute)
        and importer.func.attr == "__import__"
        and isinstance(importer.func.value, ast.Name)
        and importer.func.value.id in builtins_aliases
    ):
        return module_name
    if isinstance(importer.func, ast.Name) and importer.func.id in import_module_aliases:
        return module_name
    if (
        isinstance(importer.func, ast.Attribute)
        and importer.func.attr == "import_module"
        and isinstance(importer.func.value, ast.Name)
        and importer.func.value.id in importlib_aliases
    ):
        return module_name
    if (
        isinstance(importer.func, ast.Attribute)
        and importer.func.attr == "import_module"
        and isinstance(importer.func.value, ast.Call)
        and python_dynamic_import_name(importer.func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "importlib"
    ):
        return module_name
    getattr_target = python_static_getattr_target(importer.func)
    if getattr_target is None:
        return None
    target, attr = getattr_target
    if attr == "__import__" and isinstance(target, ast.Name) and target.id in builtins_aliases:
        return module_name
    if attr == "import_module" and isinstance(target, ast.Call):
        target_name = python_dynamic_import_name(target, builtins_aliases, importlib_aliases, import_module_aliases)
        if target_name == "importlib":
            return module_name
    return None


def python_first_string_argument(node: ast.Call) -> str | None:
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value
    return None


def python_static_getattr_target(node: ast.AST) -> tuple[ast.AST, str] | None:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "getattr" or len(node.args) < 2:
        return None
    attr = node.args[1]
    if not isinstance(attr, ast.Constant) or not isinstance(attr.value, str):
        return None
    return node.args[0], attr.value


def python_getattr_attribute(
    node: ast.Call,
    module_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> str | None:
    getattr_target = python_static_getattr_target(node)
    if getattr_target is None:
        return None
    target, attr_value = getattr_target
    if isinstance(target, ast.Name):
        target_name = target.id
    elif isinstance(target, ast.Call):
        target_name = python_dynamic_import_name(target, builtins_aliases, importlib_aliases, import_module_aliases)
    else:
        return None
    if target_name not in module_aliases:
        return None
    return attr_value
