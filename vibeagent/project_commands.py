from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .command_parsing import parse_local_path_args
from .types import (
    CodeOutlineAction,
    FileInfoAction,
    FindFilesAction,
    GlobAction,
    ImageInfoAction,
    ListTreeAction,
    OutputContextsAction,
    OutputDiagnosticsAction,
    ProjectOverviewAction,
    RepoMapAction,
    SearchAction,
    SearchContextsAction,
)
from .workflow_commands import format_review_check
from .workspace_core import RunWorkspace


def _plain_data(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, list):
        return [_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _plain_data(item) for key, item in value.items()}
    return value


def _field_value(value: object, name: str, default: object = None) -> object:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _clip(value: str, max_length: int) -> str:
    compacted = value.strip()
    if len(compacted) <= max_length:
        return compacted
    return f"{compacted[:max_length]}\n[context output truncated]"


def _indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def _commands_attr(name: str, default: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    if commands_module is None:
        return default
    return getattr(commands_module, name, default)


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


def _format_project_command_report_item(item: object) -> str:
    available = bool(_field_value(item, "available", False))
    missing_tool = str(_field_value(item, "missing_tool", "") or "")
    command = str(_field_value(item, "command", "") or "")
    cwd = str(_field_value(item, "cwd", ".") or ".")
    source = str(_field_value(item, "file", "") or "")
    availability = "available" if available else f"missing {missing_tool}"
    return f"    - [{availability}] {command} (cwd: {cwd}, source: {source})"


def format_overview_report_text(report: dict[str, object]) -> str:
    git = report.get("git") if isinstance(report.get("git"), dict) else {}
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    tree = report.get("tree") if isinstance(report.get("tree"), dict) else {}
    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    manifests = report.get("manifests") if isinstance(report.get("manifests"), dict) else {}
    suggested_checks = report.get("suggestedChecks") if isinstance(report.get("suggestedChecks"), dict) else {}
    tools = report.get("tools") if isinstance(report.get("tools"), dict) else {}

    lines = [
        "Overview:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  gitRepo: {'yes' if bool(git.get('isRepo')) else 'no'}",
    ]
    if bool(git.get("isRepo")):
        branch = str(git.get("branch") or "(detached)")
        upstream = str(git.get("upstream") or "none")
        lines.append(f"  git: {branch} {git.get('head') or ''} upstream={upstream} ahead={git.get('ahead', 0)} behind={git.get('behind', 0)}")
    lines.extend(
        [
            f"  files: {files.get('shown', 0)}/{files.get('total', 0)}",
            f"  treeEntries: {tree.get('shown', 0)}/{tree.get('total', 0)}",
            f"  repoTruncated: {'yes' if bool(tree.get('truncated')) else 'no'}",
            f"  commands: {commands.get('shown', 0)}/{commands.get('total', 0)}",
            f"  manifests: {manifests.get('shown', 0)}/{manifests.get('total', 0)}",
            f"  suggestedChecks: {suggested_checks.get('shown', 0)}/{suggested_checks.get('total', 0)}",
            f"  tools: {tools.get('available', 0)}/{tools.get('total', 0)} available",
        ]
    )
    command_items = commands.get("items") if isinstance(commands.get("items"), list) else []
    if command_items:
        lines.append("  commandList:")
        lines.extend(_format_project_command_report_item(item) for item in command_items[:10])
    suggested_items = suggested_checks.get("items") if isinstance(suggested_checks.get("items"), list) else []
    if suggested_items:
        lines.append("  checks:")
        lines.extend(format_review_check(item) for item in suggested_items[:10] if isinstance(item, dict))
    manifest_items = manifests.get("items") if isinstance(manifests.get("items"), list) else []
    if manifest_items:
        lines.append("  manifestList:")
        for manifest in manifest_items[:10]:
            if isinstance(manifest, dict):
                lines.append(f"    - {manifest.get('path')} ({manifest.get('kind')}, items={manifest.get('item_count')}, ok={'yes' if bool(manifest.get('ok')) else 'no'})")
    tool_items = tools.get("items") if isinstance(tools.get("items"), list) else []
    if tool_items:
        lines.append("  toolAvailability:")
        for tool in tool_items[:20]:
            if isinstance(tool, dict):
                lines.append(f"    - {tool.get('name')}: {'yes' if bool(tool.get('available')) else 'no'}")
    git_status = str(git.get("status") or "")
    if git_status.strip():
        lines.append("  gitStatus:")
        lines.append(_indent_block(_clip(git_status.strip(), 2_000), spaces=4))
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


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

def get_search_report(
    project_root: str | Path = ".",
    query: str | None = None,
    path: str | None = None,
    max_matches: int = 80,
    regex: bool = False,
    case_sensitive: bool = True,
    context_lines: int = 0,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if query is None or not query.strip():
        return {
            "projectRoot": str(root),
            "ok": False,
            "query": "",
            "path": path or ".",
            "matches": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "regex": regex,
            "caseSensitive": case_sensitive,
            "contextLines": context_lines,
            "message": "Usage: /search <query>",
        }
    workspace = RunWorkspace(root=root, run_id="local-search", session_dir=root / ".vibeagent" / "sessions" / "local-search")
    observation = _execute_action(
        workspace,
        SearchAction(
            type="search",
            query=query.strip(),
            path=path,
            regex=regex,
            case_sensitive=case_sensitive,
            max_matches=max_matches,
            context_lines=context_lines,
        ),
    )
    if observation.kind != "search":
        return {
            "projectRoot": str(root),
            "ok": False,
            "query": query.strip(),
            "path": path or ".",
            "matches": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "regex": regex,
            "caseSensitive": case_sensitive,
            "contextLines": context_lines,
            "message": f"Unexpected observation: {observation.kind}",
        }

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "query": observation.query,
        "path": observation.path or ".",
        "matches": {
            "shown": len(observation.matches),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": list(observation.matches),
        },
        "regex": observation.regex,
        "caseSensitive": observation.case_sensitive,
        "contextLines": observation.context_lines,
        "message": observation.message,
    }


def format_search_report_text(report: dict[str, object]) -> str:
    if not report.get("query") and str(report.get("message") or "").startswith("Usage:"):
        return str(report.get("message") or "Usage: /search <query>")
    matches = report.get("matches") if isinstance(report.get("matches"), dict) else {}
    match_items = matches.get("items") if isinstance(matches.get("items"), list) else []

    lines = [
        "Search:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  query: {report.get('query') or ''}",
        f"  path: {report.get('path') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  matches: {matches.get('shown', 0)}/{matches.get('total', 0)}",
        f"  truncated: {'yes' if bool(matches.get('truncated')) else 'no'}",
        f"  regex: {'yes' if bool(report.get('regex')) else 'no'}",
        f"  caseSensitive: {'yes' if bool(report.get('caseSensitive', True)) else 'no'}",
        f"  contextLines: {report.get('contextLines', 0)}",
    ]
    if match_items:
        lines.append("  results:")
        for match in match_items:
            lines.append(_indent_block(str(match), spaces=4))
    else:
        lines.append("  results: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def get_search_text(
    project_root: str | Path = ".",
    query: str | None = None,
    path: str | None = None,
    max_matches: int = 80,
    regex: bool = False,
    case_sensitive: bool = True,
    context_lines: int = 0,
) -> str:
    get_report = _commands_attr("get_search_report", get_search_report)
    formatter = _commands_attr("format_search_report_text", format_search_report_text)
    return formatter(
        get_report(
            project_root,
            query=query,
            path=path,
            max_matches=max_matches,
            regex=regex,
            case_sensitive=case_sensitive,
            context_lines=context_lines,
        )
    )

def get_search_contexts_report(
    project_root: str | Path = ".",
    query: str | None = None,
    path: str | None = None,
    max_matches: int = 20,
    regex: bool = False,
    case_sensitive: bool = True,
    context_lines: int = 3,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if query is None or not query.strip():
        return {
            "projectRoot": str(root),
            "ok": False,
            "query": "",
            "path": path or ".",
            "contexts": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "regex": regex,
            "caseSensitive": case_sensitive,
            "contextLines": context_lines,
            "maxBytesPerContext": max_bytes_per_context,
            "message": "Usage: /search-contexts <query>",
        }
    workspace = RunWorkspace(root=root, run_id="local-search-contexts", session_dir=root / ".vibeagent" / "sessions" / "local-search-contexts")
    observation = _execute_action(
        workspace,
        SearchContextsAction(
            type="search_contexts",
            query=query.strip(),
            path=path,
            regex=regex,
            case_sensitive=case_sensitive,
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )
    if observation.kind != "search_contexts":
        return {
            "projectRoot": str(root),
            "ok": False,
            "query": query.strip(),
            "path": path or ".",
            "contexts": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "regex": regex,
            "caseSensitive": case_sensitive,
            "contextLines": context_lines,
            "maxBytesPerContext": max_bytes_per_context,
            "message": f"Unexpected observation: {observation.kind}",
        }

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "query": observation.query,
        "path": observation.path or ".",
        "contexts": {
            "shown": len(observation.contexts),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": [_plain_data(context) for context in observation.contexts],
        },
        "regex": observation.regex,
        "caseSensitive": observation.case_sensitive,
        "contextLines": observation.context_lines,
        "maxBytesPerContext": observation.max_bytes_per_context,
        "message": observation.message,
    }


def format_search_contexts_report_text(report: dict[str, object]) -> str:
    if not report.get("query") and str(report.get("message") or "").startswith("Usage:"):
        return str(report.get("message") or "Usage: /search-contexts <query>")
    contexts = report.get("contexts") if isinstance(report.get("contexts"), dict) else {}
    context_items = contexts.get("items") if isinstance(contexts.get("items"), list) else []

    lines = [
        "Search contexts:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  query: {report.get('query') or ''}",
        f"  path: {report.get('path') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  contexts: {contexts.get('shown', 0)}/{contexts.get('total', 0)}",
        f"  truncated: {'yes' if bool(contexts.get('truncated')) else 'no'}",
        f"  regex: {'yes' if bool(report.get('regex')) else 'no'}",
        f"  caseSensitive: {'yes' if bool(report.get('caseSensitive', True)) else 'no'}",
        f"  contextLines: {report.get('contextLines', 3)}",
    ]
    if context_items:
        lines.append("  results:")
        for index, context in enumerate(context_items, start=1):
            if not isinstance(context, dict):
                continue
            lines.extend(
                [
                    f"    - index: {index}",
                    f"      path: {context.get('path')}",
                    f"      line: {context.get('line')}",
                    f"      range: {context.get('start_line')}-{context.get('end_line')}",
                    f"      truncated: {'yes' if bool(context.get('truncated')) else 'no'}",
                    "      content:",
                    _indent_block(str(context.get("content") or ""), spaces=8),
                ]
            )
    else:
        lines.append("  results: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def get_search_contexts_text(
    project_root: str | Path = ".",
    query: str | None = None,
    path: str | None = None,
    max_matches: int = 20,
    regex: bool = False,
    case_sensitive: bool = True,
    context_lines: int = 3,
    max_bytes_per_context: int = 20_000,
) -> str:
    get_report = _commands_attr("get_search_contexts_report", get_search_contexts_report)
    formatter = _commands_attr("format_search_contexts_report_text", format_search_contexts_report_text)
    return formatter(
        get_report(
            project_root,
            query=query,
            path=path,
            max_matches=max_matches,
            regex=regex,
            case_sensitive=case_sensitive,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        )
    )

def get_find_files_report(
    project_root: str | Path = ".",
    query: str | None = None,
    path: str | None = None,
    max_matches: int = 100,
    regex: bool = False,
    case_sensitive: bool = False,
    include_dirs: bool = False,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if query is None or not query.strip():
        return {
            "projectRoot": str(root),
            "ok": False,
            "query": "",
            "path": path,
            "matches": {"shown": 0, "total": 0, "truncated": False, "files": []},
            "maxMatches": max_matches,
            "regex": regex,
            "caseSensitive": case_sensitive,
            "includeDirs": include_dirs,
            "message": "Usage: /find-files [--path PATH] [--max-matches N] [--regex] [--case-sensitive] [--include-dirs] -- <query>",
        }
    workspace = RunWorkspace(root=root, run_id="local-find-files", session_dir=root / ".vibeagent" / "sessions" / "local-find-files")
    observation = _execute_action(
        workspace,
        FindFilesAction(
            type="find_files",
            query=query.strip(),
            path=path,
            max_matches=max_matches,
            regex=regex,
            case_sensitive=case_sensitive,
            include_dirs=include_dirs,
        ),
    )
    if observation.kind != "find_files":
        return {
            "projectRoot": str(root),
            "ok": False,
            "query": query.strip(),
            "path": path,
            "matches": {"shown": 0, "total": 0, "truncated": False, "files": []},
            "maxMatches": max_matches,
            "regex": regex,
            "caseSensitive": case_sensitive,
            "includeDirs": include_dirs,
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "query": observation.query,
        "path": observation.path,
        "matches": {
            "shown": len(observation.matches),
            "total": observation.total,
            "truncated": observation.truncated,
            "files": list(observation.matches),
        },
        "maxMatches": max_matches,
        "regex": observation.regex,
        "caseSensitive": observation.case_sensitive,
        "includeDirs": observation.include_dirs,
        "message": observation.message,
    }


def format_find_files_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    matches = report.get("matches") if isinstance(report.get("matches"), dict) else {}
    files = matches.get("files") if isinstance(matches, dict) and isinstance(matches.get("files"), list) else []
    lines = [
        "Find Files:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  query: {report.get('query') or ''}",
        f"  path: {report.get('path') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  matches: {matches.get('shown', 0)}/{matches.get('total', 0)}",
        f"  regex: {'yes' if bool(report.get('regex')) else 'no'}",
        f"  caseSensitive: {'yes' if bool(report.get('caseSensitive')) else 'no'}",
        f"  includeDirs: {'yes' if bool(report.get('includeDirs')) else 'no'}",
        f"  truncated: {'yes' if bool(matches.get('truncated')) else 'no'}",
    ]
    if files:
        lines.append("  files:")
        lines.extend(f"    - {path}" for path in files)
    else:
        lines.append("  files: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def get_find_files_text(
    project_root: str | Path = ".",
    query: str | None = None,
    path: str | None = None,
    max_matches: int = 100,
    regex: bool = False,
    case_sensitive: bool = False,
    include_dirs: bool = False,
) -> str:
    get_report = _commands_attr("get_find_files_report", get_find_files_report)
    formatter = _commands_attr("format_find_files_report_text", format_find_files_report_text)
    return formatter(
        get_report(
            project_root,
            query,
            path=path,
            max_matches=max_matches,
            regex=regex,
            case_sensitive=case_sensitive,
            include_dirs=include_dirs,
        )
    )

def get_glob_report(
    project_root: str | Path = ".",
    pattern: str | None = None,
    max_matches: int = 200,
    include_dirs: bool = False,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if pattern is None or not pattern.strip():
        return {
            "projectRoot": str(root),
            "ok": False,
            "pattern": "",
            "matches": {"shown": 0, "total": 0, "truncated": False, "files": []},
            "maxMatches": max_matches,
            "includeDirs": include_dirs,
            "message": "Usage: /glob [--max-matches N] [--include-dirs] -- <pattern>",
        }
    workspace = RunWorkspace(root=root, run_id="local-glob", session_dir=root / ".vibeagent" / "sessions" / "local-glob")
    observation = _execute_action(
        workspace,
        GlobAction(
            type="glob",
            pattern=pattern.strip(),
            max_matches=max_matches,
            include_dirs=include_dirs,
        ),
    )
    if observation.kind != "glob":
        return {
            "projectRoot": str(root),
            "ok": False,
            "pattern": pattern.strip(),
            "matches": {"shown": 0, "total": 0, "truncated": False, "files": []},
            "maxMatches": max_matches,
            "includeDirs": include_dirs,
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "pattern": observation.pattern,
        "matches": {
            "shown": len(observation.matches),
            "total": observation.total,
            "truncated": observation.truncated,
            "files": list(observation.matches),
        },
        "maxMatches": max_matches,
        "includeDirs": include_dirs,
        "message": observation.message,
    }


def format_glob_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    matches = report.get("matches") if isinstance(report.get("matches"), dict) else {}
    files = matches.get("files") if isinstance(matches, dict) and isinstance(matches.get("files"), list) else []
    lines = [
        "Glob:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  pattern: {report.get('pattern') or ''}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  matches: {matches.get('shown', 0)}/{matches.get('total', 0)}",
        f"  includeDirs: {'yes' if bool(report.get('includeDirs')) else 'no'}",
        f"  truncated: {'yes' if bool(matches.get('truncated')) else 'no'}",
    ]
    if files:
        lines.append("  files:")
        lines.extend(f"    - {path}" for path in files)
    else:
        lines.append("  files: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def get_glob_text(
    project_root: str | Path = ".",
    pattern: str | None = None,
    max_matches: int = 200,
    include_dirs: bool = False,
) -> str:
    get_report = _commands_attr("get_glob_report", get_glob_report)
    formatter = _commands_attr("format_glob_report_text", format_glob_report_text)
    return formatter(get_report(project_root, pattern, max_matches=max_matches, include_dirs=include_dirs))

def get_tree_report(
    project_root: str | Path = ".",
    path: str | None = None,
    max_depth: int = 3,
    max_entries: int = 200,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    selected_path = path.strip() if path else None
    workspace = RunWorkspace(root=root, run_id="local-tree", session_dir=root / ".vibeagent" / "sessions" / "local-tree")
    observation = _execute_action(
        workspace,
        ListTreeAction(
            type="list_tree",
            path=selected_path,
            max_depth=max_depth,
            max_entries=max_entries,
        ),
    )
    if observation.kind != "list_tree":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": selected_path or ".",
            "entries": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "maxDepth": max_depth,
            "maxEntries": max_entries,
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path,
        "entries": {
            "shown": len(observation.entries),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": list(observation.entries),
        },
        "maxDepth": observation.max_depth,
        "maxEntries": max_entries,
        "message": observation.message,
    }


def format_tree_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    entries = report.get("entries") if isinstance(report.get("entries"), dict) else {}
    items = entries.get("items") if isinstance(entries, dict) and isinstance(entries.get("items"), list) else []
    lines = [
        "Tree:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  path: {report.get('path') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  entries: {entries.get('shown', 0)}/{entries.get('total', 0)}",
        f"  maxDepth: {report.get('maxDepth', 0)}",
        f"  truncated: {'yes' if bool(entries.get('truncated')) else 'no'}",
    ]
    if items:
        lines.append("  tree:")
        lines.extend(f"    - {entry}" for entry in items)
    else:
        lines.append("  tree: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def get_tree_text(
    project_root: str | Path = ".",
    path: str | None = None,
    max_depth: int = 3,
    max_entries: int = 200,
) -> str:
    get_report = _commands_attr("get_tree_report", get_tree_report)
    formatter = _commands_attr("format_tree_report_text", format_tree_report_text)
    return formatter(get_report(project_root, path, max_depth=max_depth, max_entries=max_entries))

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


def get_output_contexts_text(
    project_root: str | Path = ".",
    text: str | None = None,
    context_lines: int = 5,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    if not text or not text.strip():
        return "Usage: /output-contexts <text>"
    if len(text) > 200_000:
        return "Usage: /output-contexts <text>\nError: text must be at most 200000 characters."
    if context_lines < 0:
        return "Usage: /output-contexts <text>\nError: context_lines must be at least 0."
    if context_lines > 500:
        return "Usage: /output-contexts <text>\nError: context_lines must be at most 500."
    if max_contexts < 1:
        return "Usage: /output-contexts <text>\nError: max_contexts must be at least 1."
    if max_contexts > 100:
        return "Usage: /output-contexts <text>\nError: max_contexts must be at most 100."
    if max_bytes_per_context < 1_000:
        return "Usage: /output-contexts <text>\nError: max_bytes_per_context must be at least 1000."
    if max_bytes_per_context > 200_000:
        return "Usage: /output-contexts <text>\nError: max_bytes_per_context must be at most 200000."

    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-output-contexts", session_dir=root / ".vibeagent" / "sessions" / "local-output-contexts")
    observation = _execute_action(
        workspace,
        OutputContextsAction(
            type="output_contexts",
            text=text,
            context_lines=context_lines,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )
    if observation.kind != "output_contexts":
        return f"Output contexts:\n  projectRoot: {root}\n  message: Unexpected observation: {observation.kind}"

    ok_count = sum(1 for item in observation.contexts if item.ok)
    lines = [
        "Output contexts:",
        f"  projectRoot: {root}",
        f"  contexts: {ok_count}/{len(observation.contexts)}",
        f"  totalRefs: {observation.total_refs}",
        f"  contextLines: {context_lines}",
        f"  maxContexts: {max_contexts}",
        f"  maxBytesPerContext: {max_bytes_per_context}",
        f"  truncated: {'yes' if observation.truncated else 'no'}",
        f"  message: {observation.message}",
    ]
    for item in observation.contexts:
        column = f":{item.column}" if item.column is not None else ""
        lines.extend(
            [
                "",
                f"Context: {item.path}:{item.line}{column}",
                f"  raw: {item.raw}",
                f"  ok: {'yes' if item.ok else 'no'}",
                f"  range: {item.start_line}:{item.end_line}",
                f"  contextLines: {item.context_lines}",
                f"  targetLineExists: {'yes' if item.target_line_exists else 'no'}",
                f"  lines: {item.line_count}/{item.total_lines if item.total_lines is not None else 'unknown'}",
                f"  maxBytes: {item.max_bytes}",
                f"  truncated: {'yes' if item.truncated else 'no'}",
                f"  message: {item.message}",
            ]
        )
        if item.content:
            lines.append("  content:")
            lines.append(_indent_block(item.content.rstrip("\n"), spaces=4))
        else:
            lines.append("  content: none")
    return "\n".join(lines)


def serialize_output_context_result(item: object) -> dict[str, object]:
    return {
        "path": str(getattr(item, "path", "")),
        "line": getattr(item, "line", None),
        "column": getattr(item, "column", None),
        "raw": str(getattr(item, "raw", "")),
        "ok": bool(getattr(item, "ok", False)),
        "content": str(getattr(item, "content", "")),
        "message": str(getattr(item, "message", "")),
        "contextLines": getattr(item, "context_lines", None),
        "startLine": getattr(item, "start_line", None),
        "endLine": getattr(item, "end_line", None),
        "lineCount": getattr(item, "line_count", 0),
        "totalLines": getattr(item, "total_lines", None),
        "targetLineExists": bool(getattr(item, "target_line_exists", False)),
        "truncated": bool(getattr(item, "truncated", False)),
        "maxBytes": getattr(item, "max_bytes", None),
    }


def serialize_output_diagnostic(item: object) -> dict[str, object]:
    return {
        "severity": str(getattr(item, "severity", "")),
        "outputLine": getattr(item, "output_line", None),
        "text": str(getattr(item, "text", "")),
        "path": getattr(item, "path", None),
        "line": getattr(item, "line", None),
        "column": getattr(item, "column", None),
        "raw": getattr(item, "raw", None),
    }


def get_output_contexts_report(
    project_root: str | Path = ".",
    text: str | None = None,
    context_lines: int = 5,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if not text or not text.strip():
        return {
            "projectRoot": str(root),
            "ok": False,
            "contexts": {"ok": 0, "total": 0, "items": []},
            "totalRefs": 0,
            "contextLines": context_lines,
            "maxContexts": max_contexts,
            "maxBytesPerContext": max_bytes_per_context,
            "truncated": False,
            "message": "Usage: /output-contexts <text>",
        }
    if len(text) > 200_000:
        return {
            "projectRoot": str(root),
            "ok": False,
            "contexts": {"ok": 0, "total": 0, "items": []},
            "totalRefs": 0,
            "contextLines": context_lines,
            "maxContexts": max_contexts,
            "maxBytesPerContext": max_bytes_per_context,
            "truncated": False,
            "message": "Usage: /output-contexts <text>\nError: text must be at most 200000 characters.",
        }
    if context_lines < 0:
        message = "Usage: /output-contexts <text>\nError: context_lines must be at least 0."
    elif context_lines > 500:
        message = "Usage: /output-contexts <text>\nError: context_lines must be at most 500."
    elif max_contexts < 1:
        message = "Usage: /output-contexts <text>\nError: max_contexts must be at least 1."
    elif max_contexts > 100:
        message = "Usage: /output-contexts <text>\nError: max_contexts must be at most 100."
    elif max_bytes_per_context < 1_000:
        message = "Usage: /output-contexts <text>\nError: max_bytes_per_context must be at least 1000."
    elif max_bytes_per_context > 200_000:
        message = "Usage: /output-contexts <text>\nError: max_bytes_per_context must be at most 200000."
    else:
        message = ""
    if message:
        return {
            "projectRoot": str(root),
            "ok": False,
            "contexts": {"ok": 0, "total": 0, "items": []},
            "totalRefs": 0,
            "contextLines": context_lines,
            "maxContexts": max_contexts,
            "maxBytesPerContext": max_bytes_per_context,
            "truncated": False,
            "message": message,
        }

    workspace = RunWorkspace(root=root, run_id="local-output-contexts", session_dir=root / ".vibeagent" / "sessions" / "local-output-contexts")
    observation = _execute_action(
        workspace,
        OutputContextsAction(
            type="output_contexts",
            text=text,
            context_lines=context_lines,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )
    if observation.kind != "output_contexts":
        return {
            "projectRoot": str(root),
            "ok": False,
            "contexts": {"ok": 0, "total": 0, "items": []},
            "totalRefs": 0,
            "contextLines": context_lines,
            "maxContexts": max_contexts,
            "maxBytesPerContext": max_bytes_per_context,
            "truncated": False,
            "message": f"Unexpected observation: {observation.kind}",
        }

    items = [serialize_output_context_result(item) for item in observation.contexts]
    ok_count = sum(1 for item in items if item["ok"])
    return {
        "projectRoot": str(root),
        "ok": ok_count == len(items),
        "contexts": {"ok": ok_count, "total": len(items), "items": items},
        "totalRefs": observation.total_refs,
        "contextLines": context_lines,
        "maxContexts": max_contexts,
        "maxBytesPerContext": max_bytes_per_context,
        "truncated": observation.truncated,
        "message": observation.message,
    }


def format_output_contexts_report_text(report: dict[str, object]) -> str:
    contexts = report.get("contexts") if isinstance(report.get("contexts"), dict) else {}
    items = contexts.get("items") if isinstance(contexts.get("items"), list) else []
    lines = [
        "Output contexts:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  contexts: {contexts.get('ok', 0)}/{contexts.get('total', 0)}",
        f"  totalRefs: {report.get('totalRefs', 0)}",
        f"  contextLines: {report.get('contextLines') if report.get('contextLines') is not None else 'unknown'}",
        f"  maxContexts: {report.get('maxContexts') if report.get('maxContexts') is not None else 'unknown'}",
        f"  maxBytesPerContext: {report.get('maxBytesPerContext') if report.get('maxBytesPerContext') is not None else 'unknown'}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]
    for raw_item in items:
        item = raw_item if isinstance(raw_item, dict) else {}
        column = f":{item.get('column')}" if item.get("column") is not None else ""
        lines.extend(
            [
                "",
                f"Context: {item.get('path') or ''}:{item.get('line') if item.get('line') is not None else 'unknown'}{column}",
                f"  raw: {item.get('raw') or ''}",
                f"  ok: {'yes' if bool(item.get('ok')) else 'no'}",
                f"  range: {item.get('startLine')}:{item.get('endLine')}",
                f"  contextLines: {item.get('contextLines') if item.get('contextLines') is not None else 'unknown'}",
                f"  targetLineExists: {'yes' if bool(item.get('targetLineExists')) else 'no'}",
                f"  lines: {item.get('lineCount', 0)}/{item.get('totalLines') if item.get('totalLines') is not None else 'unknown'}",
                f"  maxBytes: {item.get('maxBytes') if item.get('maxBytes') is not None else 'unknown'}",
                f"  truncated: {'yes' if bool(item.get('truncated')) else 'no'}",
                f"  message: {item.get('message') or ''}",
            ]
        )
        content = str(item.get("content") or "")
        if content:
            lines.append("  content:")
            lines.append(_indent_block(content.rstrip("\n"), spaces=4))
        else:
            lines.append("  content: none")
    return "\n".join(lines)


def get_output_diagnostics_text(
    project_root: str | Path = ".",
    text: str | None = None,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    if not text or not text.strip():
        return "Usage: /output-diagnostics <text>"
    if len(text) > 200_000:
        return "Usage: /output-diagnostics <text>\nError: text must be at most 200000 characters."
    if context_lines < 0:
        return "Usage: /output-diagnostics <text>\nError: context_lines must be at least 0."
    if context_lines > 500:
        return "Usage: /output-diagnostics <text>\nError: context_lines must be at most 500."
    if max_diagnostics < 1:
        return "Usage: /output-diagnostics <text>\nError: max_diagnostics must be at least 1."
    if max_diagnostics > 200:
        return "Usage: /output-diagnostics <text>\nError: max_diagnostics must be at most 200."
    if max_contexts < 1:
        return "Usage: /output-diagnostics <text>\nError: max_contexts must be at least 1."
    if max_contexts > 100:
        return "Usage: /output-diagnostics <text>\nError: max_contexts must be at most 100."
    if max_bytes_per_context < 1_000:
        return "Usage: /output-diagnostics <text>\nError: max_bytes_per_context must be at least 1000."
    if max_bytes_per_context > 200_000:
        return "Usage: /output-diagnostics <text>\nError: max_bytes_per_context must be at most 200000."

    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-output-diagnostics", session_dir=root / ".vibeagent" / "sessions" / "local-output-diagnostics")
    observation = _execute_action(
        workspace,
        OutputDiagnosticsAction(
            type="output_diagnostics",
            text=text,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )
    if observation.kind != "output_diagnostics":
        return f"Output diagnostics:\n  projectRoot: {root}\n  message: Unexpected observation: {observation.kind}"

    ok_count = sum(1 for item in observation.contexts if item.ok)
    lines = [
        "Output diagnostics:",
        f"  projectRoot: {root}",
        f"  diagnostics: {len(observation.diagnostics)}/{observation.total_diagnostics}",
        f"  contexts: {ok_count}/{len(observation.contexts)}",
        f"  totalRefs: {observation.total_refs}",
        f"  contextLines: {context_lines}",
        f"  maxDiagnostics: {max_diagnostics}",
        f"  maxContexts: {max_contexts}",
        f"  maxBytesPerContext: {max_bytes_per_context}",
        f"  diagnosticsTruncated: {'yes' if observation.diagnostics_truncated else 'no'}",
        f"  contextsTruncated: {'yes' if observation.contexts_truncated else 'no'}",
        f"  message: {observation.message}",
    ]
    for diagnostic in observation.diagnostics:
        location = ""
        if diagnostic.path and diagnostic.line is not None:
            column = f":{diagnostic.column}" if diagnostic.column is not None else ""
            location = f" {diagnostic.path}:{diagnostic.line}{column}"
        lines.append(f"  - {diagnostic.severity} outputLine={diagnostic.output_line}{location}: {diagnostic.text}")
    for item in observation.contexts:
        column = f":{item.column}" if item.column is not None else ""
        lines.extend(
            [
                "",
                f"Context: {item.path}:{item.line}{column}",
                f"  raw: {item.raw}",
                f"  ok: {'yes' if item.ok else 'no'}",
                f"  range: {item.start_line}:{item.end_line}",
                f"  contextLines: {item.context_lines}",
                f"  targetLineExists: {'yes' if item.target_line_exists else 'no'}",
                f"  lines: {item.line_count}/{item.total_lines if item.total_lines is not None else 'unknown'}",
                f"  maxBytes: {item.max_bytes}",
                f"  truncated: {'yes' if item.truncated else 'no'}",
                f"  message: {item.message}",
            ]
        )
        if item.content:
            lines.append("  content:")
            lines.append(_indent_block(item.content.rstrip("\n"), spaces=4))
        else:
            lines.append("  content: none")
    return "\n".join(lines)


def get_output_diagnostics_report(
    project_root: str | Path = ".",
    text: str | None = None,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
    usage: str = "/output-diagnostics <text>",
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if not text or not text.strip():
        return {
            "projectRoot": str(root),
            "ok": False,
            "diagnostics": {"shown": 0, "total": 0, "items": []},
            "contexts": {"ok": 0, "total": 0, "items": []},
            "totalRefs": 0,
            "contextLines": context_lines,
            "maxDiagnostics": max_diagnostics,
            "maxContexts": max_contexts,
            "maxBytesPerContext": max_bytes_per_context,
            "diagnosticsTruncated": False,
            "contextsTruncated": False,
            "message": f"Usage: {usage}",
        }
    if len(text) > 200_000:
        message = f"Usage: {usage}\nError: text must be at most 200000 characters."
    elif context_lines < 0:
        message = f"Usage: {usage}\nError: context_lines must be at least 0."
    elif context_lines > 500:
        message = f"Usage: {usage}\nError: context_lines must be at most 500."
    elif max_diagnostics < 1:
        message = f"Usage: {usage}\nError: max_diagnostics must be at least 1."
    elif max_diagnostics > 200:
        message = f"Usage: {usage}\nError: max_diagnostics must be at most 200."
    elif max_contexts < 1:
        message = f"Usage: {usage}\nError: max_contexts must be at least 1."
    elif max_contexts > 100:
        message = f"Usage: {usage}\nError: max_contexts must be at most 100."
    elif max_bytes_per_context < 1_000:
        message = f"Usage: {usage}\nError: max_bytes_per_context must be at least 1000."
    elif max_bytes_per_context > 200_000:
        message = f"Usage: {usage}\nError: max_bytes_per_context must be at most 200000."
    else:
        message = ""
    if message:
        return {
            "projectRoot": str(root),
            "ok": False,
            "diagnostics": {"shown": 0, "total": 0, "items": []},
            "contexts": {"ok": 0, "total": 0, "items": []},
            "totalRefs": 0,
            "contextLines": context_lines,
            "maxDiagnostics": max_diagnostics,
            "maxContexts": max_contexts,
            "maxBytesPerContext": max_bytes_per_context,
            "diagnosticsTruncated": False,
            "contextsTruncated": False,
            "message": message,
        }

    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-output-diagnostics", session_dir=root / ".vibeagent" / "sessions" / "local-output-diagnostics")
    observation = _execute_action(
        workspace,
        OutputDiagnosticsAction(
            type="output_diagnostics",
            text=text,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )
    if observation.kind != "output_diagnostics":
        return {
            "projectRoot": str(root),
            "ok": False,
            "diagnostics": {"shown": 0, "total": 0, "items": []},
            "contexts": {"ok": 0, "total": 0, "items": []},
            "totalRefs": 0,
            "contextLines": context_lines,
            "maxDiagnostics": max_diagnostics,
            "maxContexts": max_contexts,
            "maxBytesPerContext": max_bytes_per_context,
            "diagnosticsTruncated": False,
            "contextsTruncated": False,
            "message": f"Unexpected observation: {observation.kind}",
        }

    diagnostics = [serialize_output_diagnostic(item) for item in observation.diagnostics]
    contexts = [serialize_output_context_result(item) for item in observation.contexts]
    ok_count = sum(1 for item in contexts if item["ok"])
    return {
        "projectRoot": str(root),
        "ok": ok_count == len(contexts),
        "diagnostics": {"shown": len(diagnostics), "total": observation.total_diagnostics, "items": diagnostics},
        "contexts": {"ok": ok_count, "total": len(contexts), "items": contexts},
        "totalRefs": observation.total_refs,
        "contextLines": context_lines,
        "maxDiagnostics": max_diagnostics,
        "maxContexts": max_contexts,
        "maxBytesPerContext": max_bytes_per_context,
        "diagnosticsTruncated": observation.diagnostics_truncated,
        "contextsTruncated": observation.contexts_truncated,
        "message": observation.message,
    }


def format_output_diagnostics_report_text(report: dict[str, object], *, title: str = "Output diagnostics") -> str:
    diagnostics = report.get("diagnostics") if isinstance(report.get("diagnostics"), dict) else {}
    diagnostic_items = diagnostics.get("items") if isinstance(diagnostics.get("items"), list) else []
    contexts = report.get("contexts") if isinstance(report.get("contexts"), dict) else {}
    context_items = contexts.get("items") if isinstance(contexts.get("items"), list) else []
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  diagnostics: {diagnostics.get('shown', 0)}/{diagnostics.get('total', 0)}",
        f"  contexts: {contexts.get('ok', 0)}/{contexts.get('total', 0)}",
        f"  totalRefs: {report.get('totalRefs', 0)}",
        f"  contextLines: {report.get('contextLines') if report.get('contextLines') is not None else 'unknown'}",
        f"  maxDiagnostics: {report.get('maxDiagnostics') if report.get('maxDiagnostics') is not None else 'unknown'}",
        f"  maxContexts: {report.get('maxContexts') if report.get('maxContexts') is not None else 'unknown'}",
        f"  maxBytesPerContext: {report.get('maxBytesPerContext') if report.get('maxBytesPerContext') is not None else 'unknown'}",
        f"  diagnosticsTruncated: {'yes' if bool(report.get('diagnosticsTruncated')) else 'no'}",
        f"  contextsTruncated: {'yes' if bool(report.get('contextsTruncated')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]
    for raw_diagnostic in diagnostic_items:
        diagnostic = raw_diagnostic if isinstance(raw_diagnostic, dict) else {}
        location = ""
        if diagnostic.get("path") and diagnostic.get("line") is not None:
            column = f":{diagnostic.get('column')}" if diagnostic.get("column") is not None else ""
            location = f" {diagnostic.get('path')}:{diagnostic.get('line')}{column}"
        lines.append(
            f"  - {diagnostic.get('severity')} outputLine={diagnostic.get('outputLine')}{location}: {diagnostic.get('text') or ''}"
        )
    for raw_item in context_items:
        item = raw_item if isinstance(raw_item, dict) else {}
        column = f":{item.get('column')}" if item.get("column") is not None else ""
        lines.extend(
            [
                "",
                f"Context: {item.get('path') or ''}:{item.get('line') if item.get('line') is not None else 'unknown'}{column}",
                f"  raw: {item.get('raw') or ''}",
                f"  ok: {'yes' if bool(item.get('ok')) else 'no'}",
                f"  range: {item.get('startLine')}:{item.get('endLine')}",
                f"  contextLines: {item.get('contextLines') if item.get('contextLines') is not None else 'unknown'}",
                f"  targetLineExists: {'yes' if bool(item.get('targetLineExists')) else 'no'}",
                f"  lines: {item.get('lineCount', 0)}/{item.get('totalLines') if item.get('totalLines') is not None else 'unknown'}",
                f"  maxBytes: {item.get('maxBytes') if item.get('maxBytes') is not None else 'unknown'}",
                f"  truncated: {'yes' if bool(item.get('truncated')) else 'no'}",
                f"  message: {item.get('message') or ''}",
            ]
        )
        content = str(item.get("content") or "")
        if content:
            lines.append("  content:")
            lines.append(_indent_block(content.rstrip("\n"), spaces=4))
        else:
            lines.append("  content: none")
    return "\n".join(lines)


def get_python_traceback_report(
    project_root: str | Path = ".",
    text: str | None = None,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    return get_output_diagnostics_report(
        project_root,
        text,
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
        usage="/python-traceback <text>",
    )


def format_python_traceback_report_text(report: dict[str, object]) -> str:
    return format_output_diagnostics_report_text(report, title="Python traceback")


def get_python_traceback_text(
    project_root: str | Path = ".",
    text: str | None = None,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    rendered = get_output_diagnostics_text(
        project_root,
        text,
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
    )
    return (
        rendered.replace("Output diagnostics:", "Python traceback:", 1)
        .replace("Usage: /output-diagnostics <text>", "Usage: /python-traceback <text>", 1)
    )
