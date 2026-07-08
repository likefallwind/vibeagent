from __future__ import annotations

from pathlib import Path

from .project_command_utils import (
    commands_attr as _commands_attr,
    execute_action as _execute_action,
    field_value as _field_value,
    plain_data as _plain_data,
)
from .types import RepoMapAction
from .workspace_core import RunWorkspace


def get_repo_map_report(
    project_root: str | Path = ".",
    path: str | None = None,
    max_depth: int = 3,
    max_files: int = 80,
    max_symbols: int = 120,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-repo-map", session_dir=root / ".vibeagent" / "sessions" / "local-repo-map")
    observation = _execute_action(
        workspace,
        RepoMapAction(
            type="repo_map",
            path=path,
            max_depth=max_depth,
            max_files=max_files,
            max_symbols=max_symbols,
        ),
    )
    if observation.kind != "repo_map":
        return {
            "projectRoot": str(root),
            "path": path or ".",
            "ok": False,
            "tree": {"shown": 0, "total": 0, "entries": []},
            "files": {"shown": 0, "total": 0, "paths": []},
            "symbols": {"pythonFiles": [], "codeFiles": []},
            "truncated": False,
            "maxDepth": max_depth,
            "maxFiles": max_files,
            "maxSymbols": max_symbols,
            "message": f"Unexpected observation: {observation.kind}",
        }

    return {
        "projectRoot": str(root),
        "path": observation.path,
        "ok": observation.ok,
        "tree": {"shown": len(observation.tree), "total": observation.total_tree_entries, "entries": list(observation.tree)},
        "files": {"shown": len(observation.files), "total": observation.total_files, "paths": list(observation.files)},
        "symbols": {
            "pythonFiles": [_plain_data(item) for item in observation.python_files],
            "codeFiles": [_plain_data(item) for item in observation.code_files],
        },
        "truncated": observation.truncated,
        "maxDepth": max_depth,
        "maxFiles": max_files,
        "maxSymbols": max_symbols,
        "message": observation.message,
    }


def format_repo_map_report_text(report: dict[str, object]) -> str:
    tree = report.get("tree") if isinstance(report.get("tree"), dict) else {}
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    symbols = report.get("symbols") if isinstance(report.get("symbols"), dict) else {}
    tree_entries = tree.get("entries") if isinstance(tree.get("entries"), list) else []
    file_paths = files.get("paths") if isinstance(files.get("paths"), list) else []
    python_files = symbols.get("pythonFiles") if isinstance(symbols.get("pythonFiles"), list) else []
    code_files = symbols.get("codeFiles") if isinstance(symbols.get("codeFiles"), list) else []

    lines = [
        "Repo map:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  path: {report.get('path') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  files: {files.get('shown', 0)}/{files.get('total', 0)}",
        f"  treeEntries: {tree.get('shown', 0)}/{tree.get('total', 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
    ]
    if tree_entries:
        lines.append("  tree:")
        lines.extend(f"    - {entry}" for entry in tree_entries)
    else:
        lines.append("  tree: none")
    if file_paths:
        lines.append("  files:")
        lines.extend(f"    - {file}" for file in file_paths)
    else:
        lines.append("  files: none")
    symbol_lines = format_repo_map_symbols(python_files, code_files)
    if symbol_lines:
        lines.append("  symbols:")
        lines.extend(symbol_lines)
    else:
        lines.append("  symbols: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def format_repo_map_symbols(python_files: list[object], code_files: list[object], max_per_file: int = 12) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for file in python_files:
        path = str(_field_value(file, "path", "") or "")
        if not path or path in seen:
            continue
        seen.add(path)
        lines.extend(format_symbol_file(path, "python", _field_value(file, "imports", []), _field_value(file, "symbols", []), max_per_file=max_per_file))
    for file in code_files:
        path = str(_field_value(file, "path", "") or "")
        if not path or path in seen:
            continue
        seen.add(path)
        language = str(_field_value(file, "language", "") or "code")
        lines.extend(format_symbol_file(path, language, _field_value(file, "imports", []), _field_value(file, "symbols", []), max_per_file=max_per_file))
    return lines


def format_symbol_file(path: str, language: str, imports: object, symbols: object, max_per_file: int = 12) -> list[str]:
    import_values = [str(item) for item in imports if isinstance(item, str)] if isinstance(imports, list) else []
    symbol_values = [
        item
        for item in symbols
        if hasattr(item, "name") or (isinstance(item, dict) and item.get("name"))
    ] if isinstance(symbols, list) else []
    lines = [f"    - {path} ({language})"]
    if import_values:
        shown_imports = ", ".join(import_values[:8])
        suffix = f" (+{len(import_values) - 8} more)" if len(import_values) > 8 else ""
        lines.append(f"      imports: {shown_imports}{suffix}")
    if symbol_values:
        for symbol in symbol_values[:max_per_file]:
            name = str(_field_value(symbol, "name", "") or "")
            kind = str(_field_value(symbol, "kind", "symbol") or "symbol")
            line = _field_value(symbol, "line", None)
            location = f":{line}" if isinstance(line, int) else ""
            lines.append(f"      - {kind} {name}{location}")
        if len(symbol_values) > max_per_file:
            lines.append(f"      - [{len(symbol_values) - max_per_file} additional symbol(s) omitted]")
    else:
        lines.append("      symbols: none")
    return lines


def get_repo_map_text(
    project_root: str | Path = ".",
    path: str | None = None,
    max_depth: int = 3,
    max_files: int = 80,
    max_symbols: int = 120,
) -> str:
    get_report = _commands_attr("get_repo_map_report", get_repo_map_report)
    formatter = _commands_attr("format_repo_map_report_text", format_repo_map_report_text)
    return formatter(get_report(project_root, path=path, max_depth=max_depth, max_files=max_files, max_symbols=max_symbols))
