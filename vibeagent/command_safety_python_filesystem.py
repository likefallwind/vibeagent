from __future__ import annotations

import ast

from .command_safety_python_introspection import python_dynamic_import_name


def python_call_deletes_broad_path(
    node: ast.Call,
    shutil_aliases: set[str],
    shutil_rmtree_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        if func.id not in shutil_rmtree_aliases:
            return False
    elif isinstance(func, ast.Attribute) and func.attr == "rmtree":
        if isinstance(func.value, ast.Name):
            if func.value.id not in shutil_aliases:
                return False
        elif not (
            isinstance(func.value, ast.Call)
            and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "shutil"
        ):
            return False
    else:
        return False
    target = python_call_string_argument(node, "path")
    return target is not None and is_dangerous_recursive_delete_target(target)


def python_call_string_argument(node: ast.Call, keyword_name: str) -> str | None:
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value
    for keyword in node.keywords:
        if keyword.arg == keyword_name and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            return keyword.value.value
    return None


def python_call_writes_raw_device(
    node: ast.Call,
    io_aliases: set[str],
    io_open_aliases: set[str],
    os_aliases: set[str],
    os_open_aliases: set[str],
    pathlib_aliases: set[str],
    pathlib_path_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    if python_open_call_writes_raw_device(node, io_aliases, io_open_aliases, builtins_aliases, importlib_aliases, import_module_aliases):
        return True
    if python_os_open_call_writes_raw_device(node, os_aliases, os_open_aliases, builtins_aliases, importlib_aliases, import_module_aliases):
        return True
    return python_pathlib_call_writes_raw_device(
        node,
        pathlib_aliases,
        pathlib_path_aliases,
        builtins_aliases,
        importlib_aliases,
        import_module_aliases,
    )


def python_open_call_writes_raw_device(
    node: ast.Call,
    io_aliases: set[str],
    io_open_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    func = node.func
    if not python_call_is_text_open(func, io_aliases, io_open_aliases, builtins_aliases, importlib_aliases, import_module_aliases):
        return False
    if not node.args:
        return False
    path_arg = node.args[0]
    if not isinstance(path_arg, ast.Constant) or not isinstance(path_arg.value, str):
        return False
    if not is_raw_device_write_target(path_arg.value):
        return False
    mode = "r"
    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
        mode = node.args[1].value
    for keyword in node.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            mode = keyword.value.value
            break
    return any(flag in mode for flag in ("w", "a", "+", "x"))


def python_call_is_text_open(
    func: ast.expr,
    io_aliases: set[str],
    io_open_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    if isinstance(func, ast.Name):
        return func.id == "open" or func.id in io_open_aliases
    if not isinstance(func, ast.Attribute) or func.attr != "open":
        return False
    if isinstance(func.value, ast.Name) and func.value.id in io_aliases:
        return True
    return isinstance(func.value, ast.Call) and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "io"


def python_os_open_call_writes_raw_device(
    node: ast.Call,
    os_aliases: set[str],
    os_open_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        if func.id not in os_open_aliases:
            return False
    elif isinstance(func, ast.Attribute) and func.attr == "open":
        if isinstance(func.value, ast.Name):
            if func.value.id not in os_aliases:
                return False
        elif not (
            isinstance(func.value, ast.Call)
            and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "os"
        ):
            return False
    else:
        return False
    if len(node.args) < 2:
        return False
    path_arg = node.args[0]
    if not isinstance(path_arg, ast.Constant) or not isinstance(path_arg.value, str):
        return False
    if not is_raw_device_write_target(path_arg.value):
        return False
    return python_os_open_flags_write(node.args[1])


def python_os_open_flags_write(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return (node.value & 0b11) in {1, 2}
    if isinstance(node, ast.Attribute) and node.attr in {"O_WRONLY", "O_RDWR"}:
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return python_os_open_flags_write(node.left) or python_os_open_flags_write(node.right)
    return False


def python_pathlib_call_writes_raw_device(
    node: ast.Call,
    pathlib_aliases: set[str],
    pathlib_path_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr not in {"open", "write_bytes", "write_text"}:
        return False
    path = python_pathlib_call_path(func.value, pathlib_aliases, pathlib_path_aliases, builtins_aliases, importlib_aliases, import_module_aliases)
    if path is None or not is_raw_device_write_target(path):
        return False
    if func.attr in {"write_bytes", "write_text"}:
        return True
    mode = "r"
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        mode = node.args[0].value
    for keyword in node.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            mode = keyword.value.value
            break
    return any(flag in mode for flag in ("w", "a", "+", "x"))


def python_pathlib_call_path(
    node: ast.AST,
    pathlib_aliases: set[str],
    pathlib_path_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> str | None:
    if not isinstance(node, ast.Call) or not node.args:
        return None
    path_arg = node.args[0]
    if not isinstance(path_arg, ast.Constant) or not isinstance(path_arg.value, str):
        return None
    func = node.func
    if isinstance(func, ast.Name) and func.id in pathlib_path_aliases:
        return path_arg.value
    if isinstance(func, ast.Attribute) and func.attr == "Path":
        if isinstance(func.value, ast.Name) and func.value.id in pathlib_aliases:
            return path_arg.value
        if isinstance(func.value, ast.Call) and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "pathlib":
            return path_arg.value
    return None


def is_dangerous_recursive_delete_target(path: str) -> bool:
    from .command_safety_filesystem import is_dangerous_recursive_delete_target as shell_is_dangerous_recursive_delete_target

    return shell_is_dangerous_recursive_delete_target(path)


def is_raw_device_write_target(path: str) -> bool:
    from .command_safety_filesystem import is_raw_device_write_target as shell_is_raw_device_write_target

    return shell_is_raw_device_write_target(path)
