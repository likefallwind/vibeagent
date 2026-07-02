from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class PythonImportAliases:
    builtins_aliases: set[str] = field(default_factory=lambda: {"builtins", "__builtins__"})
    eval_exec_aliases: set[str] = field(default_factory=lambda: {"eval", "exec"})
    compile_aliases: set[str] = field(default_factory=lambda: {"compile"})
    webbrowser_aliases: set[str] = field(default_factory=lambda: {"webbrowser"})
    webbrowser_open_aliases: set[str] = field(default_factory=set)
    webbrowser_get_aliases: set[str] = field(default_factory=set)
    io_aliases: set[str] = field(default_factory=lambda: {"io"})
    io_open_aliases: set[str] = field(default_factory=set)
    importlib_aliases: set[str] = field(default_factory=lambda: {"importlib"})
    import_module_aliases: set[str] = field(default_factory=set)
    os_aliases: set[str] = field(default_factory=lambda: {"os"})
    os_open_aliases: set[str] = field(default_factory=set)
    os_startfile_aliases: set[str] = field(default_factory=set)
    os_exec_spawn_aliases: set[str] = field(default_factory=set)
    os_exec_spawn_alias_functions: dict[str, str] = field(default_factory=dict)
    asyncio_aliases: set[str] = field(default_factory=lambda: {"asyncio"})
    asyncio_subprocess_aliases: set[str] = field(default_factory=set)
    asyncio_subprocess_alias_functions: dict[str, str] = field(default_factory=dict)
    pathlib_aliases: set[str] = field(default_factory=lambda: {"pathlib"})
    pathlib_path_aliases: set[str] = field(default_factory=set)
    pty_aliases: set[str] = field(default_factory=lambda: {"pty"})
    pty_spawn_aliases: set[str] = field(default_factory=set)
    shutil_aliases: set[str] = field(default_factory=lambda: {"shutil"})
    shutil_rmtree_aliases: set[str] = field(default_factory=set)
    subprocess_aliases: set[str] = field(default_factory=lambda: {"subprocess"})
    os_launcher_aliases: set[str] = field(default_factory=set)
    subprocess_launcher_aliases: set[str] = field(default_factory=set)


def collect_python_import_aliases(
    tree: ast.AST,
    os_exec_spawn_function_name: Callable[[str], str | None],
) -> PythonImportAliases:
    aliases = PythonImportAliases()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            add_import_aliases(node, aliases)
        elif isinstance(node, ast.ImportFrom):
            add_import_from_aliases(node, aliases, os_exec_spawn_function_name)
    return aliases


def add_python_assignment_aliases(
    node: ast.Assign,
    aliases: PythonImportAliases,
    os_exec_spawn_function_name: Callable[[str], str | None],
) -> None:
    targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
    if not targets:
        return
    source = python_assignment_alias_source(node.value, aliases, os_exec_spawn_function_name)
    if source is None:
        return
    for target in targets:
        add_python_function_alias(target, source, aliases)


def python_assignment_alias_source(
    node: ast.AST,
    aliases: PythonImportAliases,
    os_exec_spawn_function_name: Callable[[str], str | None],
) -> tuple[str, str | None] | None:
    if isinstance(node, ast.Name):
        return python_name_alias_source(node.id, aliases)
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return python_attribute_alias_source(node.value.id, node.attr, aliases, os_exec_spawn_function_name)
    getattr_source = python_getattr_alias_source(node, aliases, os_exec_spawn_function_name)
    if getattr_source is not None:
        return getattr_source
    return None


def python_getattr_alias_source(
    node: ast.AST,
    aliases: PythonImportAliases,
    os_exec_spawn_function_name: Callable[[str], str | None],
) -> tuple[str, str | None] | None:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "getattr" or len(node.args) < 2:
        return None
    attr = node.args[1]
    if not isinstance(attr, ast.Constant) or not isinstance(attr.value, str):
        return None
    module_name = python_getattr_target_module_name(node.args[0], aliases)
    if module_name is None:
        return None
    return python_attribute_alias_source(module_name, attr.value, aliases, os_exec_spawn_function_name)


def python_getattr_target_module_name(node: ast.AST, aliases: PythonImportAliases) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        return python_dynamic_import_alias_name(node, aliases)
    return None


def python_dynamic_import_alias_name(node: ast.Call, aliases: PythonImportAliases) -> str | None:
    module_name = python_first_string_argument(node)
    if module_name is None:
        return None
    func = node.func
    if isinstance(func, ast.Name) and func.id == "__import__":
        return module_name
    if isinstance(func, ast.Name) and func.id in aliases.import_module_aliases:
        return module_name
    if isinstance(func, ast.Attribute) and func.attr == "__import__" and isinstance(func.value, ast.Name) and func.value.id in aliases.builtins_aliases:
        return module_name
    if isinstance(func, ast.Attribute) and func.attr == "import_module" and isinstance(func.value, ast.Name) and func.value.id in aliases.importlib_aliases:
        return module_name
    return None


def python_first_string_argument(node: ast.Call) -> str | None:
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value
    return None


def python_name_alias_source(name: str, aliases: PythonImportAliases) -> tuple[str, str | None] | None:
    if name in aliases.webbrowser_open_aliases:
        return ("webbrowser_open", None)
    if name in aliases.webbrowser_get_aliases:
        return ("webbrowser_get", None)
    if name in aliases.io_open_aliases:
        return ("io_open", None)
    if name in aliases.import_module_aliases:
        return ("import_module", None)
    if name in aliases.os_open_aliases:
        return ("os_open", None)
    if name in aliases.os_startfile_aliases:
        return ("os_startfile", None)
    if name in aliases.os_exec_spawn_aliases:
        return ("os_exec_spawn", aliases.os_exec_spawn_alias_functions.get(name, name))
    if name in aliases.asyncio_subprocess_aliases:
        return ("asyncio_subprocess", aliases.asyncio_subprocess_alias_functions.get(name, name))
    if name in aliases.pathlib_path_aliases:
        return ("pathlib_path", None)
    if name in aliases.pty_spawn_aliases:
        return ("pty_spawn", None)
    if name in aliases.shutil_rmtree_aliases:
        return ("shutil_rmtree", None)
    if name in aliases.os_launcher_aliases:
        return ("os_launcher", None)
    if name in aliases.subprocess_launcher_aliases:
        return ("subprocess_launcher", None)
    return None


def python_attribute_alias_source(
    module_name: str,
    attr: str,
    aliases: PythonImportAliases,
    os_exec_spawn_function_name: Callable[[str], str | None],
) -> tuple[str, str | None] | None:
    if module_name in aliases.webbrowser_aliases and attr.startswith("open"):
        return ("webbrowser_open", None)
    if module_name in aliases.webbrowser_aliases and attr == "get":
        return ("webbrowser_get", None)
    if module_name in aliases.io_aliases and attr == "open":
        return ("io_open", None)
    if module_name in aliases.importlib_aliases and attr == "import_module":
        return ("import_module", None)
    if module_name in aliases.os_aliases and attr == "open":
        return ("os_open", None)
    if module_name in aliases.os_aliases and attr in {"system", "popen"}:
        return ("os_launcher", None)
    if module_name in aliases.os_aliases and attr == "startfile":
        return ("os_startfile", None)
    if module_name in aliases.os_aliases and os_exec_spawn_function_name(attr):
        return ("os_exec_spawn", attr)
    if module_name in aliases.asyncio_aliases and attr in {"create_subprocess_exec", "create_subprocess_shell"}:
        return ("asyncio_subprocess", attr)
    if module_name in aliases.pathlib_aliases and attr == "Path":
        return ("pathlib_path", None)
    if module_name in aliases.pty_aliases and attr == "spawn":
        return ("pty_spawn", None)
    if module_name in aliases.shutil_aliases and attr == "rmtree":
        return ("shutil_rmtree", None)
    if module_name in aliases.subprocess_aliases and attr in {"run", "call", "Popen", "check_call", "check_output", "getoutput", "getstatusoutput"}:
        return ("subprocess_launcher", None)
    return None


def add_python_function_alias(alias: str, source: tuple[str, str | None], aliases: PythonImportAliases) -> None:
    kind, function_name = source
    if kind == "webbrowser_open":
        aliases.webbrowser_open_aliases.add(alias)
    elif kind == "webbrowser_get":
        aliases.webbrowser_get_aliases.add(alias)
    elif kind == "io_open":
        aliases.io_open_aliases.add(alias)
    elif kind == "import_module":
        aliases.import_module_aliases.add(alias)
    elif kind == "os_open":
        aliases.os_open_aliases.add(alias)
    elif kind == "os_launcher":
        aliases.os_launcher_aliases.add(alias)
    elif kind == "os_startfile":
        aliases.os_startfile_aliases.add(alias)
    elif kind == "os_exec_spawn":
        aliases.os_exec_spawn_aliases.add(alias)
        if function_name is not None:
            aliases.os_exec_spawn_alias_functions[alias] = function_name
    elif kind == "asyncio_subprocess":
        aliases.asyncio_subprocess_aliases.add(alias)
        if function_name is not None:
            aliases.asyncio_subprocess_alias_functions[alias] = function_name
    elif kind == "pathlib_path":
        aliases.pathlib_path_aliases.add(alias)
    elif kind == "pty_spawn":
        aliases.pty_spawn_aliases.add(alias)
    elif kind == "shutil_rmtree":
        aliases.shutil_rmtree_aliases.add(alias)
    elif kind == "subprocess_launcher":
        aliases.subprocess_launcher_aliases.add(alias)


def add_import_aliases(node: ast.Import, aliases: PythonImportAliases) -> None:
    for alias in node.names:
        name = alias.name
        asname = alias.asname or name.split(".", 1)[0]
        if name == "builtins":
            aliases.builtins_aliases.add(asname)
        elif name == "webbrowser":
            aliases.webbrowser_aliases.add(asname)
        elif name == "io":
            aliases.io_aliases.add(asname)
        elif name == "importlib":
            aliases.importlib_aliases.add(asname)
        elif name == "os":
            aliases.os_aliases.add(asname)
        elif name == "asyncio":
            aliases.asyncio_aliases.add(asname)
        elif name == "pathlib":
            aliases.pathlib_aliases.add(asname)
        elif name == "pty":
            aliases.pty_aliases.add(asname)
        elif name == "shutil":
            aliases.shutil_aliases.add(asname)
        elif name == "subprocess":
            aliases.subprocess_aliases.add(asname)


def add_import_from_aliases(
    node: ast.ImportFrom,
    aliases: PythonImportAliases,
    os_exec_spawn_function_name: Callable[[str], str | None],
) -> None:
    if node.module == "webbrowser":
        for alias in node.names:
            if alias.name.startswith("open"):
                aliases.webbrowser_open_aliases.add(alias.asname or alias.name)
            elif alias.name == "get":
                aliases.webbrowser_get_aliases.add(alias.asname or alias.name)
    elif node.module == "os":
        for alias in node.names:
            if alias.name == "open":
                aliases.os_open_aliases.add(alias.asname or alias.name)
            elif alias.name in {"system", "popen"}:
                aliases.os_launcher_aliases.add(alias.asname or alias.name)
            elif alias.name == "startfile":
                aliases.os_startfile_aliases.add(alias.asname or alias.name)
            elif os_exec_spawn_function_name(alias.name):
                alias_name = alias.asname or alias.name
                aliases.os_exec_spawn_aliases.add(alias_name)
                aliases.os_exec_spawn_alias_functions[alias_name] = alias.name
    elif node.module == "asyncio":
        for alias in node.names:
            if alias.name in {"create_subprocess_exec", "create_subprocess_shell"}:
                alias_name = alias.asname or alias.name
                aliases.asyncio_subprocess_aliases.add(alias_name)
                aliases.asyncio_subprocess_alias_functions[alias_name] = alias.name
    elif node.module == "io":
        for alias in node.names:
            if alias.name == "open":
                aliases.io_open_aliases.add(alias.asname or alias.name)
    elif node.module == "importlib":
        for alias in node.names:
            if alias.name == "import_module":
                aliases.import_module_aliases.add(alias.asname or alias.name)
    elif node.module == "pathlib":
        for alias in node.names:
            if alias.name == "Path":
                aliases.pathlib_path_aliases.add(alias.asname or alias.name)
    elif node.module == "pty":
        for alias in node.names:
            if alias.name == "spawn":
                aliases.pty_spawn_aliases.add(alias.asname or alias.name)
    elif node.module == "shutil":
        for alias in node.names:
            if alias.name == "rmtree":
                aliases.shutil_rmtree_aliases.add(alias.asname or alias.name)
    elif node.module == "subprocess":
        for alias in node.names:
            if alias.name in {"run", "call", "Popen", "check_call", "check_output", "getoutput", "getstatusoutput"}:
                aliases.subprocess_launcher_aliases.add(alias.asname or alias.name)
    elif node.module == "builtins":
        for alias in node.names:
            if alias.name in {"eval", "exec"}:
                aliases.eval_exec_aliases.add(alias.asname or alias.name)
            elif alias.name == "compile":
                aliases.compile_aliases.add(alias.asname or alias.name)
