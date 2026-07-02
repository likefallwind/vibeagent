from __future__ import annotations

import ast
from pathlib import Path
import re
import shlex


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

    builtins_aliases = {"builtins", "__builtins__"}
    eval_exec_aliases = {"eval", "exec"}
    compile_aliases = {"compile"}
    compiled_literal_scripts: dict[str, str] = {}
    webbrowser_aliases = {"webbrowser"}
    webbrowser_open_aliases: set[str] = set()
    webbrowser_get_aliases: set[str] = set()
    io_aliases = {"io"}
    io_open_aliases: set[str] = set()
    importlib_aliases = {"importlib"}
    import_module_aliases: set[str] = set()
    os_aliases = {"os"}
    os_open_aliases: set[str] = set()
    os_startfile_aliases: set[str] = set()
    os_exec_spawn_aliases: set[str] = set()
    asyncio_aliases = {"asyncio"}
    asyncio_subprocess_aliases: set[str] = set()
    pathlib_aliases = {"pathlib"}
    pathlib_path_aliases: set[str] = set()
    pty_aliases = {"pty"}
    pty_spawn_aliases: set[str] = set()
    shutil_aliases = {"shutil"}
    shutil_rmtree_aliases: set[str] = set()
    subprocess_aliases = {"subprocess"}
    os_launcher_aliases: set[str] = set()
    subprocess_launcher_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                asname = alias.asname or name.split(".", 1)[0]
                if name == "builtins":
                    builtins_aliases.add(asname)
                elif name == "webbrowser":
                    webbrowser_aliases.add(asname)
                elif name == "io":
                    io_aliases.add(asname)
                elif name == "importlib":
                    importlib_aliases.add(asname)
                elif name == "os":
                    os_aliases.add(asname)
                elif name == "asyncio":
                    asyncio_aliases.add(asname)
                elif name == "pathlib":
                    pathlib_aliases.add(asname)
                elif name == "pty":
                    pty_aliases.add(asname)
                elif name == "shutil":
                    shutil_aliases.add(asname)
                elif name == "subprocess":
                    subprocess_aliases.add(asname)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "webbrowser":
                for alias in node.names:
                    if alias.name.startswith("open"):
                        webbrowser_open_aliases.add(alias.asname or alias.name)
                    elif alias.name == "get":
                        webbrowser_get_aliases.add(alias.asname or alias.name)
            elif node.module == "os":
                for alias in node.names:
                    if alias.name == "open":
                        os_open_aliases.add(alias.asname or alias.name)
                    elif alias.name in {"system", "popen"}:
                        os_launcher_aliases.add(alias.asname or alias.name)
                    elif alias.name == "startfile":
                        os_startfile_aliases.add(alias.asname or alias.name)
                    elif python_os_exec_spawn_function_name(alias.name):
                        os_exec_spawn_aliases.add(alias.asname or alias.name)
            elif node.module == "asyncio":
                for alias in node.names:
                    if alias.name in {"create_subprocess_exec", "create_subprocess_shell"}:
                        asyncio_subprocess_aliases.add(alias.asname or alias.name)
            elif node.module == "io":
                for alias in node.names:
                    if alias.name == "open":
                        io_open_aliases.add(alias.asname or alias.name)
            elif node.module == "importlib":
                for alias in node.names:
                    if alias.name == "import_module":
                        import_module_aliases.add(alias.asname or alias.name)
            elif node.module == "pathlib":
                for alias in node.names:
                    if alias.name == "Path":
                        pathlib_path_aliases.add(alias.asname or alias.name)
            elif node.module == "pty":
                for alias in node.names:
                    if alias.name == "spawn":
                        pty_spawn_aliases.add(alias.asname or alias.name)
            elif node.module == "shutil":
                for alias in node.names:
                    if alias.name == "rmtree":
                        shutil_rmtree_aliases.add(alias.asname or alias.name)
            elif node.module == "subprocess":
                for alias in node.names:
                    if alias.name in {"run", "call", "Popen", "check_call", "check_output", "getoutput", "getstatusoutput"}:
                        subprocess_launcher_aliases.add(alias.asname or alias.name)
            elif node.module == "builtins":
                for alias in node.names:
                    if alias.name in {"eval", "exec"}:
                        eval_exec_aliases.add(alias.asname or alias.name)
                    elif alias.name == "compile":
                        compile_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.Assign):
            if python_expr_is_eval_or_exec_reference(node.value, builtins_aliases, eval_exec_aliases):
                eval_exec_aliases.update(target.id for target in node.targets if isinstance(target, ast.Name))
            elif python_expr_is_compile_reference(node.value, builtins_aliases, compile_aliases):
                compile_aliases.update(target.id for target in node.targets if isinstance(target, ast.Name))
            else:
                compiled_script = python_literal_compile_script(node.value, builtins_aliases, compile_aliases)
                if compiled_script is not None:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            compiled_literal_scripts[target.id] = compiled_script

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        nested_python = python_literal_eval_exec_script(
            node,
            builtins_aliases,
            eval_exec_aliases,
            compile_aliases,
            compiled_literal_scripts,
        )
        if nested_python is not None:
            nested_python_blocked = python_script_blocked_command_reason(nested_python, depth + 1)
            if nested_python_blocked:
                return nested_python_blocked
        if python_call_writes_raw_device(
            node,
            io_aliases,
            io_open_aliases,
            os_aliases,
            os_open_aliases,
            pathlib_aliases,
            pathlib_path_aliases,
            builtins_aliases,
            importlib_aliases,
            import_module_aliases,
        ):
            return RAW_DEVICE_WRITE_BLOCK_REASON
        if python_call_deletes_broad_path(
            node,
            shutil_aliases,
            shutil_rmtree_aliases,
            builtins_aliases,
            importlib_aliases,
            import_module_aliases,
        ):
            return RECURSIVE_DELETE_BLOCK_REASON
        if python_call_is_webbrowser_open(
            node,
            webbrowser_aliases,
            webbrowser_open_aliases,
            webbrowser_get_aliases,
            builtins_aliases,
            importlib_aliases,
            import_module_aliases,
        ):
            return "GUI application launch commands are not allowed in project mode"
        if python_call_is_os_startfile(
            node,
            os_aliases,
            os_startfile_aliases,
            builtins_aliases,
            importlib_aliases,
            import_module_aliases,
        ):
            return "GUI application launch commands are not allowed in project mode"
        nested_command = python_call_shell_command(
            node,
            os_aliases,
            subprocess_aliases,
            asyncio_aliases,
            pty_aliases,
            os_launcher_aliases,
            subprocess_launcher_aliases,
            os_exec_spawn_aliases,
            asyncio_subprocess_aliases,
            pty_spawn_aliases,
            builtins_aliases,
            importlib_aliases,
            import_module_aliases,
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
    if (
        isinstance(importer.func, ast.Name)
        and importer.func.id == "__import__"
    ):
        return module_name
    if (
        isinstance(importer.func, ast.Attribute)
        and importer.func.attr == "__import__"
        and isinstance(importer.func.value, ast.Name)
        and importer.func.value.id in builtins_aliases
    ):
        return module_name
    if (
        isinstance(importer.func, ast.Name)
        and importer.func.id in import_module_aliases
    ):
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
            return python_os_exec_spawn_command(node, func.id)
        if func.id in asyncio_subprocess_aliases:
            return python_asyncio_subprocess_command(node, func.id)
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
        for keyword in node.keywords:
            if keyword.arg in keyword_names:
                command_arg = keyword.value
                break
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


def get_blocked_command_reason(command: str, _depth: int = 0) -> str | None:
    from .command_safety import get_blocked_command_reason as main_get_blocked_command_reason

    return main_get_blocked_command_reason(command, _depth=_depth)


def is_dangerous_recursive_delete_target(path: str) -> bool:
    from .command_safety_shell import is_dangerous_recursive_delete_target as main_is_dangerous_recursive_delete_target

    return main_is_dangerous_recursive_delete_target(path)


def is_raw_device_write_target(path: str) -> bool:
    from .command_safety_shell import is_raw_device_write_target as main_is_raw_device_write_target

    return main_is_raw_device_write_target(path)
