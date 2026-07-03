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
from .command_safety_python_eval import (
    python_call_is_compile,
    python_call_is_eval_or_exec,
    python_expr_is_compile_reference,
    python_expr_is_eval_or_exec_reference,
    python_literal_compile_script,
    python_literal_eval_exec_script,
    python_literal_source_text,
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
from .command_safety_python_shell import (
    python_asyncio_subprocess_command,
    python_call_shell_command,
    python_os_exec_spawn_command,
    python_os_exec_spawn_function_name,
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


def get_blocked_command_reason(command: str, _depth: int = 0) -> str | None:
    from .command_safety import get_blocked_command_reason as main_get_blocked_command_reason

    return main_get_blocked_command_reason(command, _depth=_depth)
