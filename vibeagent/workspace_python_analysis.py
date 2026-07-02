from __future__ import annotations

import ast
from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_file_read import read_utf8_text_file
from .workspace_project_info import list_files, list_search_files
from .workspace_resolve import resolve_inside_run


def check_python_syntax(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_files: int = 200,
) -> tuple[list[dict[str, object]], int]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")

    files = [path for path in list_search_files(workspace, relative_path) if path.endswith(".py")]
    results: list[dict[str, object]] = []
    for relative in files[:max_files]:
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
            ast.parse(content, filename=relative)
            results.append(
                {
                    "path": relative,
                    "ok": True,
                    "line": None,
                    "column": None,
                    "message": "Syntax OK.",
                }
            )
        except SyntaxError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "line": error.lineno,
                    "column": error.offset,
                    "message": f"Python syntax error: {error.msg}",
                }
            )
        except ValueError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "line": None,
                    "column": None,
                    "message": str(error),
                }
            )
    return results, len(files)


def check_python_file_paths(
    workspace: RunWorkspace,
    relative_paths: list[str],
    max_files: int = 200,
) -> tuple[list[dict[str, object]], int]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")

    files: list[str] = []
    seen: set[str] = set()
    for relative in relative_paths:
        if relative in seen or not relative.endswith(".py"):
            continue
        try:
            target = resolve_inside_run(workspace.root, relative)
        except ValueError:
            continue
        if not target.is_file():
            continue
        seen.add(relative)
        files.append(relative)

    results: list[dict[str, object]] = []
    for relative in files[:max_files]:
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
            ast.parse(content, filename=relative)
            results.append(
                {
                    "path": relative,
                    "ok": True,
                    "line": None,
                    "column": None,
                    "message": "Syntax OK.",
                }
            )
        except SyntaxError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "line": error.lineno,
                    "column": error.offset,
                    "message": f"Python syntax error: {error.msg}",
                }
            )
        except ValueError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "line": None,
                    "column": None,
                    "message": str(error),
                }
            )
    return results, len(files)


def inspect_python_dependencies(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_files: int = 100,
    max_imports: int = 500,
) -> tuple[list[dict[str, object]], int]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    if max_imports < 1:
        raise ValueError("max_imports must be at least 1.")
    if max_imports > 2000:
        raise ValueError("max_imports must be at most 2000.")

    all_python_files = [path for path in list_files(workspace.root) if path.endswith(".py")]
    local_modules = build_python_module_index(all_python_files)
    files = [path for path in list_search_files(workspace, relative_path) if path.endswith(".py")]
    results: list[dict[str, object]] = []
    remaining_imports = max_imports
    for relative in files[:max_files]:
        if remaining_imports <= 0:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "module": module_name_for_python_path(relative),
                    "imports": [],
                    "local_modules": [],
                    "external_modules": [],
                    "message": "Import result limit reached.",
                }
            )
            continue
        target = resolve_inside_run(workspace.root, relative)
        try:
            content = read_utf8_text_file(target, relative)
            tree = ast.parse(content, filename=relative)
        except SyntaxError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "module": module_name_for_python_path(relative),
                    "imports": [],
                    "local_modules": [],
                    "external_modules": [],
                    "message": f"Python syntax error: {error.msg}",
                }
            )
            continue
        except ValueError as error:
            results.append(
                {
                    "path": relative,
                    "ok": False,
                    "module": module_name_for_python_path(relative),
                    "imports": [],
                    "local_modules": [],
                    "external_modules": [],
                    "message": str(error),
                }
            )
            continue

        imports = collect_python_dependency_imports(
            tree,
            current_module=module_name_for_python_path(relative),
            local_modules=local_modules,
            max_imports=remaining_imports,
        )
        remaining_imports -= len(imports)
        local_targets = sorted({str(item["target"]) for item in imports if item["local"]})
        external_targets = sorted({str(item["target"]) for item in imports if not item["local"]})
        results.append(
            {
                "path": relative,
                "ok": True,
                "module": module_name_for_python_path(relative),
                "imports": imports,
                "local_modules": local_targets,
                "external_modules": external_targets,
                "message": f"Found {len(imports)} import(s).",
            }
        )
    return results, len(files)


def build_python_module_index(files: list[str]) -> set[str]:
    modules: set[str] = set()
    for relative in files:
        module = module_name_for_python_path(relative)
        if module:
            modules.add(module)
            parts = module.split(".")
            for index in range(1, len(parts)):
                modules.add(".".join(parts[:index]))
    return modules


def module_name_for_python_path(relative_path: str) -> str:
    path = Path(relative_path)
    if path.suffix != ".py":
        return ""
    parts = list(path.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def collect_python_dependency_imports(
    tree: ast.AST,
    current_module: str,
    local_modules: set[str],
    max_imports: int,
) -> list[dict[str, object]]:
    imports: list[dict[str, object]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = alias.name
                imports.append(
                    {
                        "line": node.lineno,
                        "kind": "import",
                        "module": alias.name,
                        "name": None,
                        "alias": alias.asname,
                        "target": target,
                        "local": is_local_python_module(target, local_modules),
                    }
                )
                if len(imports) >= max_imports:
                    return sorted(imports, key=python_import_sort_key)
        elif isinstance(node, ast.ImportFrom):
            module = resolve_import_from_module(current_module, node.level, node.module)
            for alias in node.names:
                target = resolve_import_target(module, alias.name, local_modules)
                imports.append(
                    {
                        "line": node.lineno,
                        "kind": "from_import",
                        "module": module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "target": target,
                        "local": is_local_python_module(target, local_modules),
                    }
                )
                if len(imports) >= max_imports:
                    return sorted(imports, key=python_import_sort_key)
    return sorted(imports, key=python_import_sort_key)


def resolve_import_from_module(current_module: str, level: int, module: str | None) -> str:
    if level <= 0:
        return module or ""
    package_parts = current_module.split(".")[:-1]
    keep = max(0, len(package_parts) - level + 1)
    base = ".".join(package_parts[:keep])
    if module:
        return f"{base}.{module}" if base else module
    return base


def resolve_import_target(module: str, name: str, local_modules: set[str]) -> str:
    candidate = f"{module}.{name}" if module else name
    if candidate in local_modules:
        return candidate
    if module in local_modules:
        return module
    return module or name


def is_local_python_module(module: str, local_modules: set[str]) -> bool:
    return bool(module) and (module in local_modules or any(module.startswith(f"{local}.") for local in local_modules))


def python_import_sort_key(item: dict[str, object]) -> tuple[int, str, str]:
    return (int(item["line"]), str(item["module"]), str(item["name"] or ""))
