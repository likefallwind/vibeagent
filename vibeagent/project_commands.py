from __future__ import annotations

from pathlib import Path

from .command_parsing import parse_local_path_args
from .output_serialization import serialize_output_context_result, serialize_output_diagnostic
from .project_command_utils import (
    commands_attr as _commands_attr,
    execute_action as _execute_action,
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
from .project_file_info_commands import (
    file_type_text,
    format_file_info_report_text,
    format_image_info_report_text,
    get_file_info_report,
    get_file_info_text,
    get_image_info_report,
    get_image_info_text,
    serialize_file_info_result,
    serialize_image_info_result,
    yes_no_unknown,
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
from .project_repo_map_commands import (
    format_repo_map_report_text,
    format_repo_map_symbols,
    format_symbol_file,
    get_repo_map_report,
    get_repo_map_text,
)
from .types import (
    CodeOutlineAction,
    ProjectOverviewAction,
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
            "todos": {"shown": 0, "total": 0, "truncated": False, "items": []},
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
        "todos": {
            "shown": len(observation.todos),
            "total": observation.todos_total,
            "truncated": observation.todos_truncated,
            "items": [_plain_data(item) for item in observation.todos],
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
