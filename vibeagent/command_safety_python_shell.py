from __future__ import annotations

import ast

from .command_safety_python_args import python_command_argument, python_executable_command_from_call
from .command_safety_python_introspection import python_dynamic_import_name, python_getattr_attribute


def python_call_shell_command(
    node: ast.Call,
    os_aliases: set[str],
    subprocess_aliases: set[str],
    asyncio_aliases: set[str],
    pty_aliases: set[str],
    os_launcher_aliases: set[str],
    subprocess_launcher_aliases: set[str],
    os_exec_spawn_aliases: set[str],
    asyncio_subprocess_aliases: set[str],
    pty_spawn_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
    *,
    os_exec_spawn_alias_functions: dict[str, str] | None = None,
    asyncio_subprocess_alias_functions: dict[str, str] | None = None,
) -> str | None:
    func = node.func
    if isinstance(func, ast.Call):
        os_attr = python_getattr_attribute(func, os_aliases, builtins_aliases, importlib_aliases, import_module_aliases)
        if os_attr in {"system", "popen"}:
            return python_command_argument(node)
        if os_attr and python_os_exec_spawn_function_name(os_attr):
            return python_os_exec_spawn_command(node, os_attr)
        subprocess_attr = python_getattr_attribute(func, subprocess_aliases, builtins_aliases, importlib_aliases, import_module_aliases)
        if subprocess_attr in {"run", "call", "Popen", "check_call", "check_output", "getoutput", "getstatusoutput"}:
            return python_command_argument(node)
        asyncio_attr = python_getattr_attribute(func, asyncio_aliases, builtins_aliases, importlib_aliases, import_module_aliases)
        if asyncio_attr in {"create_subprocess_exec", "create_subprocess_shell"}:
            return python_asyncio_subprocess_command(node, asyncio_attr)
        pty_attr = python_getattr_attribute(func, pty_aliases, builtins_aliases, importlib_aliases, import_module_aliases)
        if pty_attr == "spawn":
            return python_command_argument(node)
        return None
    if isinstance(func, ast.Name):
        if func.id in os_launcher_aliases or func.id in subprocess_launcher_aliases:
            return python_command_argument(node)
        if func.id in os_exec_spawn_aliases:
            function_name = os_exec_spawn_alias_functions.get(func.id, func.id) if os_exec_spawn_alias_functions else func.id
            return python_os_exec_spawn_command(node, function_name)
        if func.id in asyncio_subprocess_aliases:
            function_name = (
                asyncio_subprocess_alias_functions.get(func.id, func.id) if asyncio_subprocess_alias_functions else func.id
            )
            return python_asyncio_subprocess_command(node, function_name)
        if func.id in pty_spawn_aliases:
            return python_command_argument(node)
        return None
    if not isinstance(func, ast.Attribute):
        return None
    if isinstance(func.value, ast.Name):
        if func.value.id in os_aliases and func.attr in {"system", "popen"}:
            return python_command_argument(node)
        if func.value.id in os_aliases and python_os_exec_spawn_function_name(func.attr):
            return python_os_exec_spawn_command(node, func.attr)
        if func.value.id in subprocess_aliases and func.attr in {"run", "call", "Popen", "check_call", "check_output", "getoutput", "getstatusoutput"}:
            return python_command_argument(node)
        if func.value.id in asyncio_aliases and func.attr in {"create_subprocess_exec", "create_subprocess_shell"}:
            return python_asyncio_subprocess_command(node, func.attr)
        if func.value.id in pty_aliases and func.attr == "spawn":
            return python_command_argument(node)
    if (
        isinstance(func.value, ast.Call)
        and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) in os_aliases
        and func.attr in {"system", "popen"}
    ):
        return python_command_argument(node)
    if (
        isinstance(func.value, ast.Call)
        and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) in os_aliases
        and python_os_exec_spawn_function_name(func.attr)
    ):
        return python_os_exec_spawn_command(node, func.attr)
    if (
        isinstance(func.value, ast.Call)
        and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) in subprocess_aliases
        and func.attr in {"run", "call", "Popen", "check_call", "check_output", "getoutput", "getstatusoutput"}
    ):
        return python_command_argument(node)
    if (
        isinstance(func.value, ast.Call)
        and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) in asyncio_aliases
        and func.attr in {"create_subprocess_exec", "create_subprocess_shell"}
    ):
        return python_asyncio_subprocess_command(node, func.attr)
    if (
        isinstance(func.value, ast.Call)
        and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) in pty_aliases
        and func.attr == "spawn"
    ):
        return python_command_argument(node)
    return None


def python_asyncio_subprocess_command(node: ast.Call, name: str) -> str | None:
    if name == "create_subprocess_shell":
        return python_command_argument(node)
    if name == "create_subprocess_exec":
        return python_executable_command_from_call(
            node,
            path_index=0,
            argv_index=None,
            path_keyword_names=("program",),
        )
    return None


def python_os_exec_spawn_function_name(name: str) -> str | None:
    lowered = name.lower()
    if lowered in {
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "posix_spawn",
        "posix_spawnp",
    }:
        return lowered
    return None


def python_os_exec_spawn_command(node: ast.Call, name: str) -> str | None:
    function_name = python_os_exec_spawn_function_name(name)
    if function_name is None:
        return None
    path_index = 1 if function_name.startswith("spawn") and not function_name.startswith("posix_spawn") else 0
    argv_index: int | None = None
    if function_name.startswith(("execv", "spawnv")):
        argv_index = path_index + 1
    elif function_name.startswith("posix_spawn"):
        argv_index = 1
    return python_executable_command_from_call(node, path_index=path_index, argv_index=argv_index)
