from __future__ import annotations

import ast
from pathlib import Path
import re
import shlex

from .command_safety_python_aliases import add_python_assignment_aliases, collect_python_import_aliases
from .command_safety_python_args import (
    python_command_argument,
    python_executable_command_from_args,
    python_executable_command_from_call,
    python_string_constant,
    python_string_sequence,
)
from .command_safety_python_filesystem import (
    python_call_deletes_broad_path,
    python_call_is_text_open,
    python_call_string_argument,
    python_call_writes_raw_device,
    python_open_call_writes_raw_device,
    python_os_open_call_writes_raw_device,
    python_os_open_flags_write,
    python_pathlib_call_path,
    python_pathlib_call_writes_raw_device,
)
from .command_safety_python_gui import (
    python_call_is_os_startfile,
    python_call_is_webbrowser_get,
    python_call_is_webbrowser_open,
)
from .command_safety_python_introspection import (
    python_dynamic_import_name,
    python_first_string_argument,
    python_getattr_attribute,
    python_static_getattr_target,
)


RAW_DEVICE_WRITE_BLOCK_REASON = "raw device writes are not allowed in project mode"
RECURSIVE_DELETE_BLOCK_REASON = "recursive forced deletion of broad paths is not allowed in project mode"


def python_one_liner_blocked_command_reason(command: str, depth: int) -> str | None:
    if depth >= 3:
        return None
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    while parts:
        executable = Path(parts[0]).name.lower()
        if executable in {"nohup", "setsid"}:
            parts = parts[1:]
            continue
        if executable == "env":
            parts = parts[1:]
            while parts and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", parts[0]):
                parts = parts[1:]
            continue
        break
    if len(parts) < 2 or not re.fullmatch(r"python(?:3(?:\.\d+)?)?", Path(parts[0]).name.lower()):
        return None
    script: str | None = None
    for index, token in enumerate(parts[1:], start=1):
        if token == "-c":
            if index + 1 < len(parts):
                script = parts[index + 1]
            break
        if token.startswith("-c") and len(token) > 2:
            script = token[2:]
            break
    if not script:
        return None
    return python_script_blocked_command_reason(script, depth)


def python_script_blocked_command_reason(script: str, depth: int) -> str | None:
    if depth >= 3:
        return None
    try:
        tree = ast.parse(script)
    except SyntaxError:
        return None

    aliases = collect_python_import_aliases(tree, python_os_exec_spawn_function_name)
    compiled_literal_scripts: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            add_python_assignment_aliases(node, aliases, python_os_exec_spawn_function_name)
            if python_expr_is_eval_or_exec_reference(node.value, aliases.builtins_aliases, aliases.eval_exec_aliases):
                aliases.eval_exec_aliases.update(target.id for target in node.targets if isinstance(target, ast.Name))
            elif python_expr_is_compile_reference(node.value, aliases.builtins_aliases, aliases.compile_aliases):
                aliases.compile_aliases.update(target.id for target in node.targets if isinstance(target, ast.Name))
            else:
                compiled_script = python_literal_compile_script(node.value, aliases.builtins_aliases, aliases.compile_aliases)
                if compiled_script is not None:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            compiled_literal_scripts[target.id] = compiled_script

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        nested_python = python_literal_eval_exec_script(
            node,
            aliases.builtins_aliases,
            aliases.eval_exec_aliases,
            aliases.compile_aliases,
            compiled_literal_scripts,
        )
        if nested_python is not None:
            nested_python_blocked = python_script_blocked_command_reason(nested_python, depth + 1)
            if nested_python_blocked:
                return nested_python_blocked
        if python_call_writes_raw_device(
            node,
            aliases.io_aliases,
            aliases.io_open_aliases,
            aliases.os_aliases,
            aliases.os_open_aliases,
            aliases.pathlib_aliases,
            aliases.pathlib_path_aliases,
            aliases.builtins_aliases,
            aliases.importlib_aliases,
            aliases.import_module_aliases,
        ):
            return RAW_DEVICE_WRITE_BLOCK_REASON
        if python_call_deletes_broad_path(
            node,
            aliases.shutil_aliases,
            aliases.shutil_rmtree_aliases,
            aliases.builtins_aliases,
            aliases.importlib_aliases,
            aliases.import_module_aliases,
        ):
            return RECURSIVE_DELETE_BLOCK_REASON
        if python_call_is_webbrowser_open(
            node,
            aliases.webbrowser_aliases,
            aliases.webbrowser_open_aliases,
            aliases.webbrowser_get_aliases,
            aliases.builtins_aliases,
            aliases.importlib_aliases,
            aliases.import_module_aliases,
        ):
            return "GUI application launch commands are not allowed in project mode"
        if python_call_is_os_startfile(
            node,
            aliases.os_aliases,
            aliases.os_startfile_aliases,
            aliases.builtins_aliases,
            aliases.importlib_aliases,
            aliases.import_module_aliases,
        ):
            return "GUI application launch commands are not allowed in project mode"
        nested_command = python_call_shell_command(
            node,
            aliases.os_aliases,
            aliases.subprocess_aliases,
            aliases.asyncio_aliases,
            aliases.pty_aliases,
            aliases.os_launcher_aliases,
            aliases.subprocess_launcher_aliases,
            aliases.os_exec_spawn_aliases,
            aliases.asyncio_subprocess_aliases,
            aliases.pty_spawn_aliases,
            aliases.builtins_aliases,
            aliases.importlib_aliases,
            aliases.import_module_aliases,
            os_exec_spawn_alias_functions=aliases.os_exec_spawn_alias_functions,
            asyncio_subprocess_alias_functions=aliases.asyncio_subprocess_alias_functions,
        )
        if nested_command:
            nested_blocked = get_blocked_command_reason(nested_command, _depth=depth + 1)
            if nested_blocked:
                return nested_blocked
    return None


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


def get_blocked_command_reason(command: str, _depth: int = 0) -> str | None:
    from .command_safety import get_blocked_command_reason as main_get_blocked_command_reason

    return main_get_blocked_command_reason(command, _depth=_depth)
