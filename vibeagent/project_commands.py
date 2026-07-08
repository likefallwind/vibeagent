from __future__ import annotations

from pathlib import Path

from .command_parsing import parse_local_path_args
from .output_serialization import serialize_output_context_result, serialize_output_diagnostic
from .project_command_utils import (
    commands_attr as _commands_attr,
    execute_action as _execute_action,
    field_value as _field_value,
    plain_data as _plain_data,
)
from .project_discovery_commands import (
    format_find_files_report_text,
    format_glob_report_text,
    format_search_contexts_report_text,
    format_search_report_text,
    format_tree_report_text,
    get_find_files_report,
    get_find_files_text,
    get_glob_report,
    get_glob_text,
    get_search_contexts_report,
    get_search_contexts_text,
    get_search_report,
    get_search_text,
    get_tree_report,
    get_tree_text,
)
from .project_output_commands import (
    format_output_contexts_report_text,
    format_output_diagnostics_report_text,
    format_python_traceback_report_text,
    get_output_contexts_report,
    get_output_contexts_text,
    get_output_diagnostics_report,
    get_output_diagnostics_text,
    get_python_traceback_report,
    get_python_traceback_text,
)
from .project_overview_reports import (
    format_overview_report_text,
    format_project_command_report_item as _format_project_command_report_item,
)
from .types import (
    CodeOutlineAction,
    FileInfoAction,
    ImageInfoAction,
    ProjectOverviewAction,
    RepoMapAction,
)
from .workspace_core import RunWorkspace


def get_overview_report(project_root: str | Path = ".", max_files: int = 80, max_commands: int = 20, max_checks: int = 10) -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-overview", session_dir=root / ".vibeagent" / "sessions" / "local-overview")
    observation = _execute_action(
        workspace,
        ProjectOverviewAction(
            type="project_overview",
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
        ),
    )
    if observation.kind != "project_overview":
        return {
            "projectRoot": str(root),
            "ok": False,
            "git": {"isRepo": False, "branch": "", "head": "", "upstream": "", "ahead": 0, "behind": 0, "status": ""},
            "files": {"shown": 0, "total": 0, "paths": []},
            "tree": {"shown": 0, "total": 0, "truncated": False, "entries": []},
            "commands": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "manifests": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "instructions": {"shown": 0, "total": 0, "truncated": False, "sources": []},
            "suggestedChecks": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "tools": {"available": 0, "total": 0, "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }

    tools = [_plain_data(tool) for tool in observation.tools]
    return {
        "projectRoot": observation.project_root,
        "ok": observation.ok,
        "git": {
            "isRepo": observation.is_git_repo,
            "branch": observation.git_branch,
            "head": observation.git_head,
            "upstream": observation.git_upstream,
            "ahead": observation.git_ahead,
            "behind": observation.git_behind,
            "status": observation.git_status,
        },
        "files": {"shown": len(observation.files), "total": observation.total_files, "paths": list(observation.files)},
        "tree": {
            "shown": len(observation.tree),
            "total": observation.total_tree_entries,
            "truncated": observation.repo_truncated,
            "entries": list(observation.tree),
        },
        "commands": {
            "shown": len(observation.commands),
            "total": observation.commands_total,
            "truncated": observation.commands_truncated,
            "items": [_plain_data(item) for item in observation.commands],
        },
        "manifests": {
            "shown": len(observation.manifests),
            "total": observation.manifest_files_total,
            "truncated": observation.manifests_truncated,
            "items": [_plain_data(item) for item in observation.manifests],
        },
        "instructions": {
            "shown": len(observation.instruction_sources),
            "total": observation.instruction_files_total,
            "truncated": observation.instructions_truncated,
            "sources": [_plain_data(item) for item in observation.instruction_sources],
        },
        "suggestedChecks": {
            "shown": len(observation.suggested_checks),
            "total": observation.suggested_checks_total,
            "truncated": observation.suggested_checks_truncated,
            "items": [_plain_data(item) for item in observation.suggested_checks],
        },
        "tools": {
            "available": sum(1 for item in tools if isinstance(item, dict) and bool(item.get("available"))),
            "total": len(tools),
            "items": tools,
        },
        "message": observation.message,
    }


def get_overview_text(project_root: str | Path = ".", max_files: int = 80, max_commands: int = 20, max_checks: int = 10) -> str:
    get_report = _commands_attr("get_overview_report", get_overview_report)
    formatter = _commands_attr("format_overview_report_text", format_overview_report_text)
    return formatter(get_report(project_root, max_files=max_files, max_commands=max_commands, max_checks=max_checks))

def get_repo_map_report(
    project_root: str | Path = ".",
    path: str | None = None,
    max_depth: int = 3,
    max_files: int = 80,
    max_symbols: int = 120,
) -> str:
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


def serialize_symbol(symbol: object) -> dict[str, object]:
    return {
        "name": str(getattr(symbol, "name", "")),
        "kind": str(getattr(symbol, "kind", "")),
        "line": int(getattr(symbol, "line", 0)),
        "endLine": getattr(symbol, "end_line", None),
        "parent": getattr(symbol, "parent", None),
    }


def serialize_symbol_file(file: object) -> dict[str, object]:
    symbols = list(getattr(file, "symbols", []))
    imports = list(getattr(file, "imports", []))
    return {
        "path": str(getattr(file, "path", "")),
        "ok": bool(getattr(file, "ok", False)),
        "language": getattr(file, "language", None),
        "imports": imports,
        "symbols": [serialize_symbol(symbol) for symbol in symbols],
        "counts": {"imports": len(imports), "symbols": len(symbols)},
        "message": str(getattr(file, "message", "")),
    }


def format_serialized_symbol_file(file: dict[str, object]) -> list[str]:
    path = str(file.get("path") or "")
    language = str(file.get("language") or "code")
    imports = file.get("imports") if isinstance(file.get("imports"), list) else []
    symbols = file.get("symbols") if isinstance(file.get("symbols"), list) else []
    lines = [f"    - {path} ({language})"]
    if imports:
        import_values = [str(item) for item in imports if isinstance(item, str)]
        shown_imports = ", ".join(import_values[:8])
        suffix = f" (+{len(import_values) - 8} more)" if len(import_values) > 8 else ""
        lines.append(f"      imports: {shown_imports}{suffix}")
    if symbols:
        for symbol in symbols[:12]:
            if not isinstance(symbol, dict):
                continue
            kind = symbol.get("kind") or "symbol"
            name = symbol.get("name") or ""
            line = symbol.get("line") or 0
            parent = f" parent={symbol.get('parent')}" if symbol.get("parent") else ""
            lines.append(f"      - {kind} {name}:{line}{parent}")
        if len(symbols) > 12:
            lines.append(f"      - [{len(symbols) - 12} additional symbol(s) omitted]")
    else:
        lines.append("      symbols: none")
    return lines


def get_symbols_report(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
    max_symbols: int = 200,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        paths = parse_symbols_paths(argument)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "paths": [],
            "maxSymbols": max_symbols,
            "files": {"ok": 0, "total": 0, "items": []},
            "counts": {"symbols": 0, "imports": 0},
            "message": f"Usage: /symbols <path...>\nError: {error}",
        }
    if not paths:
        return {
            "projectRoot": str(root),
            "ok": False,
            "paths": [],
            "maxSymbols": max_symbols,
            "files": {"ok": 0, "total": 0, "items": []},
            "counts": {"symbols": 0, "imports": 0},
            "message": "Usage: /symbols <path...>",
        }

    workspace = RunWorkspace(root=root, run_id="local-symbols", session_dir=root / ".vibeagent" / "sessions" / "local-symbols")
    observation = _execute_action(
        workspace,
        CodeOutlineAction(
            type="code_outline",
            paths=paths,
            max_symbols=max_symbols,
        ),
    )
    if observation.kind != "code_outline":
        return {
            "projectRoot": str(root),
            "ok": False,
            "paths": paths,
            "maxSymbols": max_symbols,
            "files": {"ok": 0, "total": 0, "items": []},
            "counts": {"symbols": 0, "imports": 0},
            "message": f"Unexpected observation: {observation.kind}",
        }

    items = [serialize_symbol_file(file) for file in observation.files]
    ok_count = sum(1 for item in items if bool(item["ok"]))
    symbol_count = sum(int(item["counts"]["symbols"]) for item in items if bool(item["ok"]))
    import_count = sum(int(item["counts"]["imports"]) for item in items if bool(item["ok"]))
    return {
        "projectRoot": str(root),
        "ok": ok_count == len(items),
        "paths": paths,
        "maxSymbols": max_symbols,
        "files": {"ok": ok_count, "total": len(items), "items": items},
        "counts": {"symbols": symbol_count, "imports": import_count},
        "message": observation.message,
    }


def format_symbols_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = files.get("items") if isinstance(files, dict) and isinstance(files.get("items"), list) else []
    counts = report.get("counts") if isinstance(report.get("counts"), dict) else {}
    lines = [
        "Symbols:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  files: {files.get('ok', 0)}/{files.get('total', 0)}",
        f"  symbols: {counts.get('symbols', 0)}",
        f"  imports: {counts.get('imports', 0)}",
    ]
    if items:
        lines.append("  outlines:")
        for file in items:
            if not isinstance(file, dict):
                continue
            if bool(file.get("ok")):
                lines.extend(format_serialized_symbol_file(file))
            else:
                lines.append(f"    - {file.get('path')} (error): {file.get('message')}")
    else:
        lines.append("  outlines: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def get_symbols_text(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
    max_symbols: int = 200,
) -> str:
    get_report = _commands_attr("get_symbols_report", get_symbols_report)
    formatter = _commands_attr("format_symbols_report_text", format_symbols_report_text)
    return formatter(get_report(project_root, argument, max_symbols=max_symbols))

def parse_symbols_paths(argument: str | list[str] | None) -> list[str]:
    return parse_local_path_args(argument, max_paths=20)


def serialize_file_info_result(file: object) -> dict[str, object]:
    return {
        "path": str(getattr(file, "path", "")),
        "ok": bool(getattr(file, "ok", False)),
        "exists": bool(getattr(file, "exists", False)),
        "type": file_type_text(file),
        "isFile": bool(getattr(file, "is_file", False)),
        "isDirectory": bool(getattr(file, "is_dir", False)),
        "sizeBytes": getattr(file, "size_bytes", None),
        "lineCount": getattr(file, "line_count", None),
        "binary": getattr(file, "is_binary", None),
        "message": str(getattr(file, "message", "")),
    }


def get_file_info_report(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=50)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "paths": {"ok": 0, "total": 0, "items": []},
            "message": f"Usage: /file-info <path...>\nError: {error}",
        }
    if not paths:
        return {
            "projectRoot": str(root),
            "ok": False,
            "paths": {"ok": 0, "total": 0, "items": []},
            "message": "Usage: /file-info <path...>",
        }

    workspace = RunWorkspace(root=root, run_id="local-file-info", session_dir=root / ".vibeagent" / "sessions" / "local-file-info")
    observation = _execute_action(
        workspace,
        FileInfoAction(
            type="file_info",
            paths=paths,
        ),
    )
    if observation.kind != "file_info":
        return {
            "projectRoot": str(root),
            "ok": False,
            "paths": {"ok": 0, "total": len(paths), "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }
    items = [serialize_file_info_result(file) for file in observation.files]
    ok_count = sum(1 for item in items if bool(item["ok"]))
    return {
        "projectRoot": str(root),
        "ok": ok_count == len(items),
        "paths": {"ok": ok_count, "total": len(items), "items": items},
        "message": observation.message,
    }


def format_file_info_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    paths = report.get("paths") if isinstance(report.get("paths"), dict) else {}
    items = paths.get("items") if isinstance(paths, dict) and isinstance(paths.get("items"), list) else []
    lines = [
        "File info:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  paths: {paths.get('ok', 0)}/{paths.get('total', 0)}",
    ]
    if items:
        lines.append("  items:")
        for file in items:
            if not isinstance(file, dict):
                continue
            lines.append(f"    - {file.get('path')}")
            lines.append(f"      ok: {'yes' if bool(file.get('ok')) else 'no'}")
            lines.append(f"      exists: {'yes' if bool(file.get('exists')) else 'no'}")
            lines.append(f"      type: {file.get('type') or 'missing'}")
            lines.append(f"      sizeBytes: {file.get('sizeBytes') if file.get('sizeBytes') is not None else 'unknown'}")
            lines.append(f"      lineCount: {file.get('lineCount') if file.get('lineCount') is not None else 'unknown'}")
            lines.append(f"      binary: {yes_no_unknown(file.get('binary'))}")
            lines.append(f"      message: {file.get('message') or ''}")
    else:
        lines.append("  items: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def get_file_info_text(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
) -> str:
    get_report = _commands_attr("get_file_info_report", get_file_info_report)
    formatter = _commands_attr("format_file_info_report_text", format_file_info_report_text)
    return formatter(get_report(project_root, argument))

def serialize_image_info_result(image: object) -> dict[str, object]:
    exists = bool(getattr(image, "exists", False))
    is_file = bool(getattr(image, "is_file", False))
    return {
        "path": str(getattr(image, "path", "")),
        "ok": bool(getattr(image, "ok", False)),
        "exists": exists,
        "type": "file" if is_file else "missing" if not exists else "path",
        "isFile": is_file,
        "sizeBytes": getattr(image, "size_bytes", None),
        "format": getattr(image, "format", None),
        "mimeType": getattr(image, "mime_type", None),
        "width": getattr(image, "width", None),
        "height": getattr(image, "height", None),
        "message": str(getattr(image, "message", "")),
    }


def get_image_info_report(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=20)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "images": {"ok": 0, "total": 0, "items": []},
            "message": f"Usage: /image-info <path...>\nError: {error}",
        }
    if not paths:
        return {
            "projectRoot": str(root),
            "ok": False,
            "images": {"ok": 0, "total": 0, "items": []},
            "message": "Usage: /image-info <path...>",
        }

    workspace = RunWorkspace(root=root, run_id="local-image-info", session_dir=root / ".vibeagent" / "sessions" / "local-image-info")
    observation = _execute_action(
        workspace,
        ImageInfoAction(
            type="image_info",
            paths=paths,
        ),
    )
    if observation.kind != "image_info":
        return {
            "projectRoot": str(root),
            "ok": False,
            "images": {"ok": 0, "total": len(paths), "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }
    items = [serialize_image_info_result(image) for image in observation.images]
    ok_count = sum(1 for item in items if bool(item["ok"]))
    return {
        "projectRoot": str(root),
        "ok": ok_count == len(items),
        "images": {"ok": ok_count, "total": len(items), "items": items},
        "message": observation.message,
    }


def format_image_info_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    images = report.get("images") if isinstance(report.get("images"), dict) else {}
    items = images.get("items") if isinstance(images, dict) and isinstance(images.get("items"), list) else []
    lines = [
        "Image info:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  images: {images.get('ok', 0)}/{images.get('total', 0)}",
    ]
    if items:
        lines.append("  items:")
        for image in items:
            if not isinstance(image, dict):
                continue
            lines.append(f"    - {image.get('path')}")
            lines.append(f"      ok: {'yes' if bool(image.get('ok')) else 'no'}")
            lines.append(f"      exists: {'yes' if bool(image.get('exists')) else 'no'}")
            lines.append(f"      type: {image.get('type') or 'missing'}")
            lines.append(f"      sizeBytes: {image.get('sizeBytes') if image.get('sizeBytes') is not None else 'unknown'}")
            lines.append(f"      format: {image.get('format') or 'unknown'}")
            lines.append(f"      mimeType: {image.get('mimeType') or 'unknown'}")
            lines.append(f"      width: {image.get('width') if image.get('width') is not None else 'unknown'}")
            lines.append(f"      height: {image.get('height') if image.get('height') is not None else 'unknown'}")
            lines.append(f"      message: {image.get('message') or ''}")
    else:
        lines.append("  items: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def get_image_info_text(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
) -> str:
    get_report = _commands_attr("get_image_info_report", get_image_info_report)
    formatter = _commands_attr("format_image_info_report_text", format_image_info_report_text)
    return formatter(get_report(project_root, argument))

def file_type_text(file: object) -> str:
    if getattr(file, "is_file", False):
        return "file"
    if getattr(file, "is_dir", False):
        return "directory"
    return "missing" if not getattr(file, "exists", False) else "path"


def yes_no_unknown(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"
