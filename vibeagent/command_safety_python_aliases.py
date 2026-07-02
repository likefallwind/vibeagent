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
