from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
import shlex
import sys

from .actions import execute_action as _default_execute_action
from .command_parsing import parse_optional_single_path_argument
from .edit_commands import format_check_location
from .process_commands import decode_stdin_escapes
from .types import (
    CheckReplacePythonDefinitionAction,
    CodeDefinitionsAction,
    CodeDependenciesAction,
    CodeReferenceContextsAction,
    CodeReferencesAction,
    CodeRenameAction,
    CodeRenamePreviewAction,
    PythonCallGraphAction,
    PythonCallsAction,
    PythonCheckAction,
    PythonDefinitionsAction,
    PythonDependenciesAction,
    PythonReferenceContextsAction,
    PythonReferencesAction,
    PythonRenameAction,
    PythonRenamePreviewAction,
    ReplacePythonDefinitionAction,
)
from .workspace_core import RunWorkspace


def _plain_data(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, list):
        return [_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _plain_data(item) for key, item in value.items()}
    return value


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


def get_python_check_report(project_root: str | Path = ".", argument: str | None = None, max_files: int = 200) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        path = parse_optional_single_path_argument(argument)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": ".",
            "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "maxFiles": max_files,
            "message": f"Usage: /python-check [path]\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-python-check", session_dir=root / ".vibeagent" / "sessions" / "local-python-check")
    observation = _execute_action(workspace, PythonCheckAction(type="python_check", path=path, max_files=max_files))
    if observation.kind != "python_check":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path or ".",
            "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "maxFiles": max_files,
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path or ".",
        "files": {
            "shown": len(observation.files),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": [_plain_data(item) for item in observation.files],
        },
        "maxFiles": max_files,
        "message": observation.message,
    }


def format_python_check_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = files.get("items") if isinstance(files.get("items"), list) else []
    lines = [
        "Python check:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or '.'}",
        f"  files: {files.get('shown', 0)}/{files.get('total', 0)}",
        f"  truncated: {'yes' if bool(files.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if items:
        lines.append("  items:")
        for item in items:
            if isinstance(item, dict):
                location = format_check_location(item.get("line"), item.get("column"))
                lines.append(f"    - {item.get('path')}: {'ok' if bool(item.get('ok')) else 'failed'}{location} - {item.get('message')}")
    else:
        lines.append("  items: none")
    return "\n".join(lines)


def get_python_deps_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_files: int = 100,
    max_imports: int = 500,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        path = parse_optional_single_path_argument(argument)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": ".",
            "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "maxFiles": max_files,
            "maxImports": max_imports,
            "message": f"Usage: /python-deps [path]\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-python-deps", session_dir=root / ".vibeagent" / "sessions" / "local-python-deps")
    observation = _execute_action(
        workspace,
        PythonDependenciesAction(type="python_dependencies", path=path, max_files=max_files, max_imports=max_imports),
    )
    if observation.kind != "python_dependencies":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path or ".",
            "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "maxFiles": max_files,
            "maxImports": max_imports,
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path or ".",
        "files": {
            "shown": len(observation.files),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": [_plain_data(item) for item in observation.files],
        },
        "maxFiles": max_files,
        "maxImports": max_imports,
        "message": observation.message,
    }


def format_python_deps_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = files.get("items") if isinstance(files.get("items"), list) else []
    lines = [
        "Python dependencies:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or '.'}",
        f"  files: {files.get('shown', 0)}/{files.get('total', 0)}",
        f"  truncated: {'yes' if bool(files.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if items:
        lines.append("  files:")
        for item in items:
            if not isinstance(item, dict):
                continue
            local_modules = item.get("local_modules") if isinstance(item.get("local_modules"), list) else []
            external_modules = item.get("external_modules") if isinstance(item.get("external_modules"), list) else []
            imports = item.get("imports") if isinstance(item.get("imports"), list) else []
            lines.append(f"    - {item.get('path')} ({item.get('module') or '.'}): {'ok' if bool(item.get('ok')) else 'failed'} - {item.get('message')}")
            lines.append(f"      local: {', '.join(str(value) for value in local_modules) if local_modules else '-'}")
            lines.append(f"      external: {', '.join(str(value) for value in external_modules) if external_modules else '-'}")
            if imports:
                lines.append("      imports:")
                for import_ref in imports:
                    if not isinstance(import_ref, dict):
                        continue
                    name = import_ref.get("name") or "-"
                    alias = f" as {import_ref.get('alias')}" if import_ref.get("alias") else ""
                    module = import_ref.get("module") or "."
                    lines.append(
                        f"        - line {import_ref.get('line')} {import_ref.get('kind')}: {module}.{name}{alias} "
                        f"-> {import_ref.get('target')} local={'yes' if bool(import_ref.get('local')) else 'no'}"
                    )
            else:
                lines.append("      imports: none")
    else:
        lines.append("  files: none")
    return "\n".join(lines)


def _symbol_report_base(project_root: str | Path, usage: str, parser, argument: str | None, symbol: str | None, path: str | None) -> tuple[Path, str | None, str | None, dict[str, object] | None]:
    root = Path(project_root).resolve()
    try:
        parsed_symbol, parsed_path = parser(argument, symbol=symbol, path=path, usage=usage)
    except ValueError as error:
        return root, None, None, {
            "projectRoot": str(root),
            "ok": False,
            "symbol": symbol or "",
            "path": path or ".",
            "items": {"shown": 0, "total": 0, "truncated": False, "results": []},
            "errors": [str(error)],
            "message": f"Usage: {usage}\nError: {error}",
        }
    return root, parsed_symbol, parsed_path, None


def get_python_defs_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 50,
    max_lines: int = 120,
) -> dict[str, object]:
    root, parsed_symbol, parsed_path, usage_report = _symbol_report_base(project_root, "/python-defs <symbol> [path]", parse_symbol_path_argument, argument, symbol, path)
    if usage_report is not None:
        usage_report["maxMatches"] = max_matches
        usage_report["maxLines"] = max_lines
        return usage_report
    workspace = RunWorkspace(root=root, run_id="local-python-defs", session_dir=root / ".vibeagent" / "sessions" / "local-python-defs")
    observation = _execute_action(
        workspace,
        PythonDefinitionsAction(type="python_definitions", symbol=parsed_symbol or "", path=parsed_path, max_matches=max_matches, max_lines=max_lines),
    )
    if observation.kind != "python_definitions":
        return _python_symbol_unexpected_report(root, parsed_symbol or "", parsed_path, "definitions", f"Unexpected observation: {observation.kind}", max_matches=max_matches, max_lines=max_lines)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "symbol": observation.symbol,
        "path": observation.path or ".",
        "definitions": {"shown": len(observation.definitions), "total": observation.total, "truncated": observation.truncated, "items": [_plain_data(item) for item in observation.definitions]},
        "errors": list(observation.errors),
        "maxMatches": max_matches,
        "maxLines": max_lines,
        "message": observation.message,
    }


def _python_symbol_unexpected_report(root: Path, symbol: str, path: str | None, key: str, message: str, **limits: object) -> dict[str, object]:
    report: dict[str, object] = {
        "projectRoot": str(root),
        "ok": False,
        "symbol": symbol,
        "path": path or ".",
        key: {"shown": 0, "total": 0, "truncated": False, "items": []},
        "errors": [],
        "message": message,
    }
    report.update(limits)
    return report


def format_python_defs_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    definitions = report.get("definitions") if isinstance(report.get("definitions"), dict) else {}
    items = definitions.get("items") if isinstance(definitions.get("items"), list) else []
    lines = _python_symbol_header("Python definitions:", report, "definitions", definitions)
    _append_errors(lines, report.get("errors"))
    if items:
        lines.append("  matches:")
        for item in items:
            if not isinstance(item, dict):
                continue
            lines.append(f"    - {item.get('path')}:{item.get('line')}:{item.get('end_line')} ({item.get('kind')}) {item.get('qualified_name')} truncated={'yes' if bool(item.get('truncated')) else 'no'}")
            if item.get("content"):
                lines.append("      content:")
                lines.extend(f"        {line}" for line in str(item.get("content")).splitlines())
    else:
        lines.append("  matches: none")
    return "\n".join(lines)


def get_python_refs_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 200,
) -> dict[str, object]:
    root, parsed_symbol, parsed_path, usage_report = _symbol_report_base(project_root, "/python-refs <symbol> [path]", parse_symbol_path_argument, argument, symbol, path)
    if usage_report is not None:
        usage_report["maxMatches"] = max_matches
        return usage_report
    workspace = RunWorkspace(root=root, run_id="local-python-refs", session_dir=root / ".vibeagent" / "sessions" / "local-python-refs")
    observation = _execute_action(workspace, PythonReferencesAction(type="python_references", symbol=parsed_symbol or "", path=parsed_path, max_matches=max_matches))
    if observation.kind != "python_references":
        return _python_symbol_unexpected_report(root, parsed_symbol or "", parsed_path, "references", f"Unexpected observation: {observation.kind}", max_matches=max_matches)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "symbol": observation.symbol,
        "path": observation.path or ".",
        "references": {"shown": len(observation.references), "total": observation.total, "truncated": observation.truncated, "items": [_plain_data(item) for item in observation.references]},
        "errors": list(observation.errors),
        "maxMatches": max_matches,
        "message": observation.message,
    }


def format_python_refs_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    references = report.get("references") if isinstance(report.get("references"), dict) else {}
    items = references.get("items") if isinstance(references.get("items"), list) else []
    lines = _python_symbol_header("Python references:", report, "references", references)
    _append_errors(lines, report.get("errors"))
    if items:
        lines.append("  matches:")
        for item in items:
            if isinstance(item, dict):
                lines.append(f"    - {item.get('path')}:{item.get('line')}:{item.get('column')} ({item.get('kind')}) {item.get('context')}")
    else:
        lines.append("  matches: none")
    return "\n".join(lines)


def get_python_ref_contexts_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 50,
    context_lines: int = 3,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root, parsed_symbol, parsed_path, usage_report = _symbol_report_base(project_root, "/python-ref-contexts <symbol> [path]", parse_symbol_path_argument, argument, symbol, path)
    if usage_report is not None:
        usage_report["maxMatches"] = max_matches
        usage_report["contextLines"] = context_lines
        usage_report["maxBytesPerContext"] = max_bytes_per_context
        return usage_report
    workspace = RunWorkspace(root=root, run_id="local-python-ref-contexts", session_dir=root / ".vibeagent" / "sessions" / "local-python-ref-contexts")
    observation = _execute_action(
        workspace,
        PythonReferenceContextsAction(
            type="python_reference_contexts",
            symbol=parsed_symbol or "",
            path=parsed_path,
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )
    if observation.kind != "python_reference_contexts":
        return _python_symbol_unexpected_report(root, parsed_symbol or "", parsed_path, "contexts", f"Unexpected observation: {observation.kind}", max_matches=max_matches, context_lines=context_lines, max_bytes_per_context=max_bytes_per_context)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "symbol": observation.symbol,
        "path": observation.path or ".",
        "contexts": {"shown": len(observation.contexts), "total": observation.total, "truncated": observation.truncated, "items": [_plain_data(item) for item in observation.contexts]},
        "errors": list(observation.errors),
        "maxMatches": max_matches,
        "contextLines": observation.context_lines,
        "maxBytesPerContext": observation.max_bytes_per_context,
        "message": observation.message,
    }


def format_python_ref_contexts_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    contexts = report.get("contexts") if isinstance(report.get("contexts"), dict) else {}
    items = contexts.get("items") if isinstance(contexts.get("items"), list) else []
    lines = _python_symbol_header("Python reference contexts:", report, "contexts", contexts)
    lines.insert(-1, f"  contextLines: {report.get('contextLines', 3)}")
    lines.insert(-1, f"  maxBytesPerContext: {report.get('maxBytesPerContext', 20000)}")
    _append_errors(lines, report.get("errors"))
    if items:
        lines.append("  contexts:")
        for item in items:
            if not isinstance(item, dict):
                continue
            lines.append(f"    - {item.get('path')}:{item.get('line')}:{item.get('column')} ({item.get('kind')}) range={item.get('start_line')}-{item.get('end_line')} truncated={'yes' if bool(item.get('truncated')) else 'no'}")
            if item.get("matched_line"):
                lines.append(f"      match: {item.get('matched_line')}")
            if item.get("content"):
                lines.append("      content:")
                lines.extend(f"        {line}" for line in str(item.get("content")).splitlines())
    else:
        lines.append("  contexts: none")
    return "\n".join(lines)


def get_python_calls_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 200,
) -> dict[str, object]:
    root, parsed_symbol, parsed_path, usage_report = _symbol_report_base(project_root, "/python-calls <symbol> [path]", parse_symbol_path_argument, argument, symbol, path)
    if usage_report is not None:
        usage_report["maxMatches"] = max_matches
        return usage_report
    workspace = RunWorkspace(root=root, run_id="local-python-calls", session_dir=root / ".vibeagent" / "sessions" / "local-python-calls")
    observation = _execute_action(workspace, PythonCallsAction(type="python_calls", symbol=parsed_symbol or "", path=parsed_path, max_matches=max_matches))
    if observation.kind != "python_calls":
        return _python_symbol_unexpected_report(root, parsed_symbol or "", parsed_path, "calls", f"Unexpected observation: {observation.kind}", max_matches=max_matches)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "symbol": observation.symbol,
        "path": observation.path or ".",
        "calls": {"shown": len(observation.calls), "total": observation.total, "truncated": observation.truncated, "items": [_plain_data(item) for item in observation.calls]},
        "errors": list(observation.errors),
        "maxMatches": max_matches,
        "message": observation.message,
    }


def format_python_calls_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    calls = report.get("calls") if isinstance(report.get("calls"), dict) else {}
    items = calls.get("items") if isinstance(calls.get("items"), list) else []
    lines = _python_symbol_header("Python calls:", report, "calls", calls)
    _append_errors(lines, report.get("errors"))
    if items:
        lines.append("  matches:")
        for item in items:
            if isinstance(item, dict):
                caller = item.get("caller") or "<module>"
                lines.append(f"    - {item.get('path')}:{item.get('line')}:{item.get('column')} {caller} -> {item.get('callee')} :: {item.get('context')}")
    else:
        lines.append("  matches: none")
    return "\n".join(lines)


def get_python_call_graph_report(project_root: str | Path = ".", argument: str | None = None, max_files: int = 100, max_edges: int = 500) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        path = parse_optional_single_path_argument(argument)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": ".",
            "edges": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "errors": [str(error)],
            "maxFiles": max_files,
            "maxEdges": max_edges,
            "message": f"Usage: /python-call-graph [path]\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-python-call-graph", session_dir=root / ".vibeagent" / "sessions" / "local-python-call-graph")
    observation = _execute_action(workspace, PythonCallGraphAction(type="python_call_graph", path=path, max_files=max_files, max_edges=max_edges))
    if observation.kind != "python_call_graph":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path or ".",
            "edges": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "errors": [],
            "maxFiles": max_files,
            "maxEdges": max_edges,
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path or ".",
        "edges": {"shown": len(observation.edges), "total": observation.total, "truncated": observation.truncated, "items": [_plain_data(item) for item in observation.edges]},
        "errors": list(observation.errors),
        "maxFiles": max_files,
        "maxEdges": max_edges,
        "message": observation.message,
    }


def format_python_call_graph_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    edges = report.get("edges") if isinstance(report.get("edges"), dict) else {}
    items = edges.get("items") if isinstance(edges.get("items"), list) else []
    lines = [
        "Python call graph:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or '.'}",
        f"  edges: {edges.get('shown', 0)}/{edges.get('total', 0)}",
        f"  truncated: {'yes' if bool(edges.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    _append_errors(lines, report.get("errors"))
    if items:
        lines.append("  edges:")
        for item in items:
            if isinstance(item, dict):
                caller = item.get("caller") or "<module>"
                lines.append(f"    - {item.get('path')}:{item.get('line')}:{item.get('column')} {caller} -> {item.get('callee')} :: {item.get('context')}")
    else:
        lines.append("  edges: none")
    return "\n".join(lines)


def _python_symbol_header(title: str, report: dict[str, object], label: str, bucket: dict[str, object]) -> list[str]:
    return [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  symbol: {report.get('symbol') or ''}",
        f"  path: {report.get('path') or '.'}",
        f"  {label}: {bucket.get('shown', 0)}/{bucket.get('total', 0)}",
        f"  truncated: {'yes' if bool(bucket.get('truncated')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]


def _append_errors(lines: list[str], errors: object) -> None:
    if isinstance(errors, list) and errors:
        lines.append("  errors:")
        lines.extend(f"    - {error}" for error in errors)


def get_python_check_text(project_root: str | Path = ".", argument: str | None = None, max_files: int = 200) -> str:
    get_report = _commands_attr("get_python_check_report", get_python_check_report)
    formatter = _commands_attr("format_python_check_report_text", format_python_check_report_text)
    return formatter(get_report(project_root, argument, max_files=max_files))

def get_python_deps_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_files: int = 100,
    max_imports: int = 500,
) -> str:
    get_report = _commands_attr("get_python_deps_report", get_python_deps_report)
    formatter = _commands_attr("format_python_deps_report_text", format_python_deps_report_text)
    return formatter(get_report(project_root, argument, max_files=max_files, max_imports=max_imports))

def get_python_defs_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 50,
    max_lines: int = 120,
) -> str:
    get_report = _commands_attr("get_python_defs_report", get_python_defs_report)
    formatter = _commands_attr("format_python_defs_report_text", format_python_defs_report_text)
    return formatter(
        get_report(
            project_root,
            argument=argument,
            symbol=symbol,
            path=path,
            max_matches=max_matches,
            max_lines=max_lines,
        )
    )

def get_python_refs_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 200,
) -> str:
    get_report = _commands_attr("get_python_refs_report", get_python_refs_report)
    formatter = _commands_attr("format_python_refs_report_text", format_python_refs_report_text)
    return formatter(get_report(project_root, argument=argument, symbol=symbol, path=path, max_matches=max_matches))

def get_python_ref_contexts_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 50,
    context_lines: int = 3,
    max_bytes_per_context: int = 20_000,
) -> str:
    get_report = _commands_attr("get_python_ref_contexts_report", get_python_ref_contexts_report)
    formatter = _commands_attr("format_python_ref_contexts_report_text", format_python_ref_contexts_report_text)
    return formatter(
        get_report(
            project_root,
            argument=argument,
            symbol=symbol,
            path=path,
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        )
    )

def get_python_calls_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 200,
) -> str:
    get_report = _commands_attr("get_python_calls_report", get_python_calls_report)
    formatter = _commands_attr("format_python_calls_report_text", format_python_calls_report_text)
    return formatter(get_report(project_root, argument=argument, symbol=symbol, path=path, max_matches=max_matches))

def get_python_call_graph_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_files: int = 100,
    max_edges: int = 500,
) -> str:
    get_report = _commands_attr("get_python_call_graph_report", get_python_call_graph_report)
    formatter = _commands_attr("format_python_call_graph_report_text", format_python_call_graph_report_text)
    return formatter(get_report(project_root, argument, max_files=max_files, max_edges=max_edges))

def get_python_rename_preview_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 500,
) -> str:
    report = get_python_rename_preview_report(
        project_root,
        argument=argument,
        symbol=symbol,
        new_name=new_name,
        path=path,
        max_files=max_files,
        max_replacements=max_replacements,
    )
    return format_python_rename_report_text("Python rename preview:", report)


def get_python_rename_preview_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 500,
) -> dict[str, object]:
    usage = "/python-rename-preview <symbol> <new_name> [path]"
    root = Path(project_root).resolve()
    try:
        parsed_symbol, parsed_new_name, parsed_path = parse_rename_argument(
            argument,
            symbol=symbol,
            new_name=new_name,
            path=path,
            usage=usage,
        )
    except ValueError as error:
        return _rename_usage_report(root, usage, symbol, new_name, path, max_files, max_replacements, str(error))
    workspace = RunWorkspace(root=root, run_id="local-python-rename-preview", session_dir=root / ".vibeagent" / "sessions" / "local-python-rename-preview")
    observation = _execute_action(
        workspace,
        PythonRenamePreviewAction(
            type="python_rename_preview",
            symbol=parsed_symbol,
            new_name=parsed_new_name,
            path=parsed_path,
            max_files=max_files,
            max_replacements=max_replacements,
        ),
    )
    if observation.kind != "python_rename_preview":
        return _rename_unexpected_report(root, parsed_symbol, parsed_new_name, parsed_path, max_files, max_replacements, f"Unexpected observation: {observation.kind}")
    return _rename_observation_report(root, observation, max_files=max_files, max_replacements=max_replacements)


def get_python_rename_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 2000,
) -> str:
    report = get_python_rename_report(
        project_root,
        argument=argument,
        symbol=symbol,
        new_name=new_name,
        path=path,
        max_files=max_files,
        max_replacements=max_replacements,
    )
    return format_python_rename_report_text("Python rename:", report)


def get_python_rename_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 2000,
) -> dict[str, object]:
    usage = "/python-rename <symbol> <new_name> [path]"
    root = Path(project_root).resolve()
    try:
        parsed_symbol, parsed_new_name, parsed_path = parse_rename_argument(
            argument,
            symbol=symbol,
            new_name=new_name,
            path=path,
            usage=usage,
        )
    except ValueError as error:
        return _rename_usage_report(root, usage, symbol, new_name, path, max_files, max_replacements, str(error))
    workspace = RunWorkspace(root=root, run_id="local-python-rename", session_dir=root / ".vibeagent" / "sessions" / "local-python-rename")
    observation = _execute_action(
        workspace,
        PythonRenameAction(
            type="python_rename",
            symbol=parsed_symbol,
            new_name=parsed_new_name,
            path=parsed_path,
            max_files=max_files,
            max_replacements=max_replacements,
        ),
    )
    if observation.kind != "python_rename":
        return _rename_unexpected_report(root, parsed_symbol, parsed_new_name, parsed_path, max_files, max_replacements, f"Unexpected observation: {observation.kind}")
    return _rename_observation_report(root, observation, max_files=max_files, max_replacements=max_replacements)


def get_check_replace_python_definition_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    content: str | None = None,
    path: str | None = None,
) -> str:
    report = get_check_replace_python_definition_report(project_root, argument=argument, symbol=symbol, content=content, path=path)
    return format_replace_python_definition_report_text("Check replace Python definition:", report)


def get_check_replace_python_definition_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    content: str | None = None,
    path: str | None = None,
) -> dict[str, object]:
    usage = "/check-replace-python-def <symbol> <content> [path]"
    root = Path(project_root).resolve()
    try:
        parsed_symbol, parsed_content, parsed_path = parse_replace_python_definition_argument(
            argument,
            symbol=symbol,
            content=content,
            path=path,
            usage=usage,
        )
    except ValueError as error:
        return _replace_python_definition_usage_report(root, usage, symbol, path, str(error))
    workspace = RunWorkspace(root=root, run_id="local-check-replace-python-def", session_dir=root / ".vibeagent" / "sessions" / "local-check-replace-python-def")
    observation = _execute_action(
        workspace,
        CheckReplacePythonDefinitionAction(
            type="check_replace_python_definition",
            symbol=parsed_symbol,
            content=parsed_content,
            path=parsed_path,
        ),
    )
    if observation.kind != "check_replace_python_definition":
        return _replace_python_definition_unexpected_report(root, parsed_symbol, parsed_path, f"Unexpected observation: {observation.kind}")
    return _replace_python_definition_observation_report(root, observation)


def get_replace_python_definition_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    content: str | None = None,
    path: str | None = None,
) -> str:
    report = get_replace_python_definition_report(project_root, argument=argument, symbol=symbol, content=content, path=path)
    return format_replace_python_definition_report_text("Replace Python definition:", report)


def get_replace_python_definition_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    content: str | None = None,
    path: str | None = None,
) -> dict[str, object]:
    usage = "/replace-python-def <symbol> <content> [path]"
    root = Path(project_root).resolve()
    try:
        parsed_symbol, parsed_content, parsed_path = parse_replace_python_definition_argument(
            argument,
            symbol=symbol,
            content=content,
            path=path,
            usage=usage,
        )
    except ValueError as error:
        return _replace_python_definition_usage_report(root, usage, symbol, path, str(error))
    workspace = RunWorkspace(root=root, run_id="local-replace-python-def", session_dir=root / ".vibeagent" / "sessions" / "local-replace-python-def")
    observation = _execute_action(
        workspace,
        ReplacePythonDefinitionAction(
            type="replace_python_definition",
            symbol=parsed_symbol,
            content=parsed_content,
            path=parsed_path,
        ),
    )
    if observation.kind != "replace_python_definition":
        return _replace_python_definition_unexpected_report(root, parsed_symbol, parsed_path, f"Unexpected observation: {observation.kind}")
    return _replace_python_definition_observation_report(root, observation)


def _replace_python_definition_usage_report(root: Path, usage: str, symbol: str | None, path: str | None, error: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "symbol": symbol or "",
        "path": path or ".",
        "definition": {"qualifiedName": None, "path": None, "startLine": None, "endLine": None},
        "diff": "",
        "message": f"Usage: {usage}\nError: {error}",
    }


def _replace_python_definition_unexpected_report(root: Path, symbol: str, path: str | None, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "symbol": symbol,
        "path": path or ".",
        "definition": {"qualifiedName": None, "path": None, "startLine": None, "endLine": None},
        "diff": "",
        "message": message,
    }


def _replace_python_definition_observation_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "symbol": getattr(observation, "symbol"),
        "path": getattr(observation, "path") or ".",
        "definition": {
            "qualifiedName": getattr(observation, "qualified_name"),
            "path": getattr(observation, "definition_path"),
            "startLine": getattr(observation, "start_line"),
            "endLine": getattr(observation, "end_line"),
        },
        "diff": str(getattr(observation, "diff", "")),
        "message": str(getattr(observation, "message")),
    }


def format_replace_python_definition_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    definition = report.get("definition") if isinstance(report.get("definition"), dict) else {}
    diff = str(report.get("diff") or "")
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  symbol: {report.get('symbol') or ''}",
        f"  path: {report.get('path') or '.'}",
        f"  definition: {definition.get('qualifiedName') or '-'}",
        f"  definitionPath: {definition.get('path') or '-'}",
        f"  lines: {definition.get('startLine') or '-'}:{definition.get('endLine') or '-'}",
        f"  message: {message}",
    ]
    if diff:
        lines.append("  diff:")
        lines.extend(f"    {diff_line}" for diff_line in diff.splitlines())
    return "\n".join(lines)


def format_replace_python_definition_observation(title: str, root: Path, observation: object) -> str:
    return format_replace_python_definition_report_text(title, _replace_python_definition_observation_report(root, observation))


def _rename_usage_report(root: Path, usage: str, symbol: str | None, new_name: str | None, path: str | None, max_files: int, max_replacements: int, error: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "symbol": symbol or "",
        "newName": new_name or "",
        "path": path or ".",
        "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
        "totalFiles": 0,
        "totalReplacements": 0,
        "truncated": False,
        "errors": [error],
        "diff": "",
        "maxFiles": max_files,
        "maxReplacements": max_replacements,
        "message": f"Usage: {usage}\nError: {error}",
    }


def _rename_unexpected_report(root: Path, symbol: str, new_name: str, path: str | None, max_files: int, max_replacements: int, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "symbol": symbol,
        "newName": new_name,
        "path": path or ".",
        "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
        "totalFiles": 0,
        "totalReplacements": 0,
        "truncated": False,
        "errors": [],
        "diff": "",
        "maxFiles": max_files,
        "maxReplacements": max_replacements,
        "message": message,
    }


def _rename_observation_report(root: Path, observation: object, *, max_files: int, max_replacements: int) -> dict[str, object]:
    files = list(getattr(observation, "files"))
    total_files = int(getattr(observation, "total_files"))
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "symbol": getattr(observation, "symbol"),
        "newName": getattr(observation, "new_name"),
        "path": getattr(observation, "path") or ".",
        "files": {
            "shown": len(files),
            "total": total_files,
            "truncated": bool(getattr(observation, "truncated", False)),
            "items": [_plain_data(item) for item in files],
        },
        "totalFiles": total_files,
        "totalReplacements": int(getattr(observation, "total_replacements")),
        "truncated": bool(getattr(observation, "truncated", False)),
        "errors": list(getattr(observation, "errors")),
        "diff": str(getattr(observation, "diff", "")),
        "maxFiles": max_files,
        "maxReplacements": max_replacements,
        "message": str(getattr(observation, "message")),
    }


def format_python_rename_report_text(title: str, report: dict[str, object]) -> str:
    return _format_rename_report_text(title, report, include_language=False)


def _format_rename_report_text(title: str, report: dict[str, object], *, include_language: bool) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = files.get("items") if isinstance(files.get("items"), list) else []
    diff = str(report.get("diff") or "")
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  rename: {report.get('symbol') or ''} -> {report.get('newName') or ''}",
        f"  path: {report.get('path') or '.'}",
        f"  files: {files.get('shown', 0)}/{files.get('total', 0)}",
        f"  replacements: {report.get('totalReplacements', 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    _append_errors(lines, report.get("errors"))
    if items:
        lines.append("  files:")
        for item in items:
            if not isinstance(item, dict):
                continue
            replacements = item.get("replacements") if isinstance(item.get("replacements"), list) else []
            if include_language:
                lines.append(
                    f"    - {item.get('path')} ({item.get('language')}): "
                    f"replacements={len(replacements)} truncated={'yes' if bool(item.get('truncated')) else 'no'}"
                )
            else:
                lines.append(f"    - {item.get('path')}: replacements={len(replacements)} truncated={'yes' if bool(item.get('truncated')) else 'no'}")
            for replacement in replacements:
                if not isinstance(replacement, dict):
                    continue
                detail = str(replacement.get("language") if include_language else replacement.get("kind") or "").strip()
                prefix = f"{detail}: " if detail else ""
                lines.append(f"      - {replacement.get('line')}:{replacement.get('column')}-{replacement.get('end_column')} {prefix}{replacement.get('old')} -> {replacement.get('new')} :: {replacement.get('context')}")
            item_diff = str(item.get("diff") or "")
            if item_diff:
                lines.append("      diff:")
                lines.extend(f"        {diff_line}" for diff_line in item_diff.splitlines())
    else:
        lines.append("  files: none")
    if diff:
        lines.append("  diff:")
        lines.extend(f"    {diff_line}" for diff_line in diff.splitlines())
    return "\n".join(lines)


def format_python_rename_observation(title: str, root: Path, observation: object) -> str:
    return format_python_rename_report_text(title, _rename_observation_report(root, observation, max_files=100, max_replacements=2000))

def get_code_deps_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_files: int = 100,
    max_imports: int = 500,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        path = parse_optional_single_path_argument(argument)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": ".",
            "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "maxFiles": max_files,
            "maxImports": max_imports,
            "message": f"Usage: /code-deps [path]\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-code-deps", session_dir=root / ".vibeagent" / "sessions" / "local-code-deps")
    observation = _execute_action(
        workspace,
        CodeDependenciesAction(type="code_dependencies", path=path, max_files=max_files, max_imports=max_imports),
    )
    if observation.kind != "code_dependencies":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path or ".",
            "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "maxFiles": max_files,
            "maxImports": max_imports,
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path or ".",
        "files": {
            "shown": len(observation.files),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": [_plain_data(item) for item in observation.files],
        },
        "maxFiles": max_files,
        "maxImports": max_imports,
        "message": observation.message,
    }


def format_code_deps_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = files.get("items") if isinstance(files.get("items"), list) else []
    lines = [
        "Code dependencies:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or '.'}",
        f"  files: {files.get('shown', 0)}/{files.get('total', 0)}",
        f"  truncated: {'yes' if bool(files.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if items:
        lines.append("  files:")
        for item in items:
            if not isinstance(item, dict):
                continue
            dependencies = item.get("dependencies") if isinstance(item.get("dependencies"), list) else []
            imports = item.get("imports") if isinstance(item.get("imports"), list) else []
            lines.append(f"    - {item.get('path')} ({item.get('language')}): {'ok' if bool(item.get('ok')) else 'failed'} - {item.get('message')}")
            lines.append(f"      dependencies: {', '.join(str(value) for value in dependencies) if dependencies else '-'}")
            if imports:
                lines.append("      imports:")
                for import_ref in imports:
                    if isinstance(import_ref, dict):
                        lines.append(f"        - line {import_ref.get('line')} {import_ref.get('kind')}: {import_ref.get('source')} :: {import_ref.get('raw')}")
            else:
                lines.append("      imports: none")
    else:
        lines.append("  files: none")
    return "\n".join(lines)


def _code_symbol_usage_report(
    report: dict[str, object],
    key: str,
    *,
    max_matches: int,
    max_lines: int | None = None,
    context_lines: int | None = None,
    max_bytes_per_context: int | None = None,
) -> dict[str, object]:
    report[key] = report.pop("items")
    report["maxMatches"] = max_matches
    if max_lines is not None:
        report["maxLines"] = max_lines
    if context_lines is not None:
        report["contextLines"] = context_lines
    if max_bytes_per_context is not None:
        report["maxBytesPerContext"] = max_bytes_per_context
    return report


def _code_symbol_unexpected_report(root: Path, symbol: str, path: str | None, key: str, message: str, **limits: object) -> dict[str, object]:
    report: dict[str, object] = {
        "projectRoot": str(root),
        "ok": False,
        "symbol": symbol,
        "path": path or ".",
        key: {"shown": 0, "total": 0, "truncated": False, "items": []},
        "message": message,
    }
    report.update(limits)
    return report


def _code_symbol_header(title: str, report: dict[str, object], label: str, bucket: dict[str, object]) -> list[str]:
    return [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  symbol: {report.get('symbol') or ''}",
        f"  path: {report.get('path') or '.'}",
        f"  {label}: {bucket.get('shown', 0)}/{bucket.get('total', 0)}",
        f"  truncated: {'yes' if bool(bucket.get('truncated')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]


def get_code_refs_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 200,
) -> dict[str, object]:
    root, parsed_symbol, parsed_path, usage_report = _symbol_report_base(project_root, "/code-refs <symbol> [path]", parse_symbol_path_argument, argument, symbol, path)
    if usage_report is not None:
        return _code_symbol_usage_report(usage_report, "references", max_matches=max_matches)
    workspace = RunWorkspace(root=root, run_id="local-code-refs", session_dir=root / ".vibeagent" / "sessions" / "local-code-refs")
    observation = _execute_action(workspace, CodeReferencesAction(type="code_references", symbol=parsed_symbol or "", path=parsed_path, max_matches=max_matches))
    if observation.kind != "code_references":
        return _code_symbol_unexpected_report(root, parsed_symbol or "", parsed_path, "references", f"Unexpected observation: {observation.kind}", maxMatches=max_matches)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "symbol": observation.symbol,
        "path": observation.path or ".",
        "references": {"shown": len(observation.references), "total": observation.total, "truncated": observation.truncated, "items": [_plain_data(item) for item in observation.references]},
        "maxMatches": max_matches,
        "message": observation.message,
    }


def format_code_refs_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    references = report.get("references") if isinstance(report.get("references"), dict) else {}
    items = references.get("items") if isinstance(references.get("items"), list) else []
    lines = _code_symbol_header("Code references:", report, "references", references)
    if items:
        lines.append("  matches:")
        for item in items:
            if isinstance(item, dict):
                lines.append(f"    - {item.get('path')}:{item.get('line')}:{item.get('column')} ({item.get('language')}) {item.get('context')}")
    else:
        lines.append("  matches: none")
    return "\n".join(lines)


def get_code_ref_contexts_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 50,
    context_lines: int = 3,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root, parsed_symbol, parsed_path, usage_report = _symbol_report_base(project_root, "/code-ref-contexts <symbol> [path]", parse_symbol_path_argument, argument, symbol, path)
    if usage_report is not None:
        return _code_symbol_usage_report(
            usage_report,
            "contexts",
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        )
    workspace = RunWorkspace(root=root, run_id="local-code-ref-contexts", session_dir=root / ".vibeagent" / "sessions" / "local-code-ref-contexts")
    observation = _execute_action(
        workspace,
        CodeReferenceContextsAction(
            type="code_reference_contexts",
            symbol=parsed_symbol or "",
            path=parsed_path,
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )
    if observation.kind != "code_reference_contexts":
        return _code_symbol_unexpected_report(
            root,
            parsed_symbol or "",
            parsed_path,
            "contexts",
            f"Unexpected observation: {observation.kind}",
            maxMatches=max_matches,
            contextLines=context_lines,
            maxBytesPerContext=max_bytes_per_context,
        )
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "symbol": observation.symbol,
        "path": observation.path or ".",
        "contexts": {"shown": len(observation.contexts), "total": observation.total, "truncated": observation.truncated, "items": [_plain_data(item) for item in observation.contexts]},
        "maxMatches": max_matches,
        "contextLines": observation.context_lines,
        "maxBytesPerContext": observation.max_bytes_per_context,
        "message": observation.message,
    }


def format_code_ref_contexts_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    contexts = report.get("contexts") if isinstance(report.get("contexts"), dict) else {}
    items = contexts.get("items") if isinstance(contexts.get("items"), list) else []
    lines = _code_symbol_header("Code reference contexts:", report, "contexts", contexts)
    lines.insert(-1, f"  contextLines: {report.get('contextLines', 3)}")
    lines.insert(-1, f"  maxBytesPerContext: {report.get('maxBytesPerContext', 20000)}")
    if items:
        lines.append("  contexts:")
        for item in items:
            if not isinstance(item, dict):
                continue
            language = item.get("language") or "unknown"
            lines.append(f"    - {item.get('path')}:{item.get('line')}:{item.get('column')} ({language} {item.get('kind')}) range={item.get('start_line')}-{item.get('end_line')} truncated={'yes' if bool(item.get('truncated')) else 'no'}")
            if item.get("matched_line"):
                lines.append(f"      match: {item.get('matched_line')}")
            if item.get("content"):
                lines.append("      content:")
                lines.extend(f"        {line}" for line in str(item.get("content")).splitlines())
    else:
        lines.append("  contexts: none")
    return "\n".join(lines)


def get_code_defs_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 50,
    max_lines: int = 80,
) -> dict[str, object]:
    root, parsed_symbol, parsed_path, usage_report = _symbol_report_base(project_root, "/code-defs <symbol> [path]", parse_symbol_path_argument, argument, symbol, path)
    if usage_report is not None:
        return _code_symbol_usage_report(usage_report, "definitions", max_matches=max_matches, max_lines=max_lines)
    workspace = RunWorkspace(root=root, run_id="local-code-defs", session_dir=root / ".vibeagent" / "sessions" / "local-code-defs")
    observation = _execute_action(
        workspace,
        CodeDefinitionsAction(type="code_definitions", symbol=parsed_symbol or "", path=parsed_path, max_matches=max_matches, max_lines=max_lines),
    )
    if observation.kind != "code_definitions":
        return _code_symbol_unexpected_report(
            root,
            parsed_symbol or "",
            parsed_path,
            "definitions",
            f"Unexpected observation: {observation.kind}",
            maxMatches=max_matches,
            maxLines=max_lines,
        )
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "symbol": observation.symbol,
        "path": observation.path or ".",
        "definitions": {"shown": len(observation.definitions), "total": observation.total, "truncated": observation.truncated, "items": [_plain_data(item) for item in observation.definitions]},
        "errors": list(observation.errors),
        "maxMatches": max_matches,
        "maxLines": max_lines,
        "message": observation.message,
    }


def format_code_defs_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    definitions = report.get("definitions") if isinstance(report.get("definitions"), dict) else {}
    items = definitions.get("items") if isinstance(definitions.get("items"), list) else []
    lines = _code_symbol_header("Code definitions:", report, "definitions", definitions)
    _append_errors(lines, report.get("errors"))
    if items:
        lines.append("  matches:")
        for item in items:
            if not isinstance(item, dict):
                continue
            lines.append(f"    - {item.get('path')}:{item.get('line')}:{item.get('end_line')} ({item.get('language')} {item.get('kind')}) {item.get('name')} truncated={'yes' if bool(item.get('truncated')) else 'no'}")
            if item.get("content"):
                lines.append("      content:")
                lines.extend(f"        {line}" for line in str(item.get("content")).splitlines())
    else:
        lines.append("  matches: none")
    return "\n".join(lines)


def get_code_deps_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_files: int = 100,
    max_imports: int = 500,
) -> str:
    get_report = _commands_attr("get_code_deps_report", get_code_deps_report)
    formatter = _commands_attr("format_code_deps_report_text", format_code_deps_report_text)
    return formatter(get_report(project_root, argument, max_files=max_files, max_imports=max_imports))

def get_code_refs_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 200,
) -> str:
    get_report = _commands_attr("get_code_refs_report", get_code_refs_report)
    formatter = _commands_attr("format_code_refs_report_text", format_code_refs_report_text)
    return formatter(get_report(project_root, argument=argument, symbol=symbol, path=path, max_matches=max_matches))

def get_code_ref_contexts_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 50,
    context_lines: int = 3,
    max_bytes_per_context: int = 20_000,
) -> str:
    get_report = _commands_attr("get_code_ref_contexts_report", get_code_ref_contexts_report)
    formatter = _commands_attr("format_code_ref_contexts_report_text", format_code_ref_contexts_report_text)
    return formatter(
        get_report(
            project_root,
            argument=argument,
            symbol=symbol,
            path=path,
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        )
    )

def get_code_defs_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 50,
    max_lines: int = 80,
) -> str:
    get_report = _commands_attr("get_code_defs_report", get_code_defs_report)
    formatter = _commands_attr("format_code_defs_report_text", format_code_defs_report_text)
    return formatter(
        get_report(
            project_root,
            argument=argument,
            symbol=symbol,
            path=path,
            max_matches=max_matches,
            max_lines=max_lines,
        )
    )

def get_code_rename_preview_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 500,
) -> str:
    report = get_code_rename_preview_report(
        project_root,
        argument=argument,
        symbol=symbol,
        new_name=new_name,
        path=path,
        max_files=max_files,
        max_replacements=max_replacements,
    )
    return format_code_rename_report_text("Code rename preview:", report)


def get_code_rename_preview_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 500,
) -> dict[str, object]:
    usage = "/code-rename-preview <symbol> <new_name> [path]"
    root = Path(project_root).resolve()
    try:
        parsed_symbol, parsed_new_name, parsed_path = parse_rename_argument(
            argument,
            symbol=symbol,
            new_name=new_name,
            path=path,
            usage=usage,
        )
    except ValueError as error:
        return _rename_usage_report(root, usage, symbol, new_name, path, max_files, max_replacements, str(error))
    workspace = RunWorkspace(root=root, run_id="local-code-rename-preview", session_dir=root / ".vibeagent" / "sessions" / "local-code-rename-preview")
    observation = _execute_action(
        workspace,
        CodeRenamePreviewAction(
            type="code_rename_preview",
            symbol=parsed_symbol,
            new_name=parsed_new_name,
            path=parsed_path,
            max_files=max_files,
            max_replacements=max_replacements,
        ),
    )
    if observation.kind != "code_rename_preview":
        return _rename_unexpected_report(root, parsed_symbol, parsed_new_name, parsed_path, max_files, max_replacements, f"Unexpected observation: {observation.kind}")
    return _rename_observation_report(root, observation, max_files=max_files, max_replacements=max_replacements)


def get_code_rename_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 2000,
) -> str:
    report = get_code_rename_report(
        project_root,
        argument=argument,
        symbol=symbol,
        new_name=new_name,
        path=path,
        max_files=max_files,
        max_replacements=max_replacements,
    )
    return format_code_rename_report_text("Code rename:", report)


def get_code_rename_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 2000,
) -> dict[str, object]:
    usage = "/code-rename <symbol> <new_name> [path]"
    root = Path(project_root).resolve()
    try:
        parsed_symbol, parsed_new_name, parsed_path = parse_rename_argument(
            argument,
            symbol=symbol,
            new_name=new_name,
            path=path,
            usage=usage,
        )
    except ValueError as error:
        return _rename_usage_report(root, usage, symbol, new_name, path, max_files, max_replacements, str(error))
    workspace = RunWorkspace(root=root, run_id="local-code-rename", session_dir=root / ".vibeagent" / "sessions" / "local-code-rename")
    observation = _execute_action(
        workspace,
        CodeRenameAction(
            type="code_rename",
            symbol=parsed_symbol,
            new_name=parsed_new_name,
            path=parsed_path,
            max_files=max_files,
            max_replacements=max_replacements,
        ),
    )
    if observation.kind != "code_rename":
        return _rename_unexpected_report(root, parsed_symbol, parsed_new_name, parsed_path, max_files, max_replacements, f"Unexpected observation: {observation.kind}")
    return _rename_observation_report(root, observation, max_files=max_files, max_replacements=max_replacements)


def format_code_rename_report_text(title: str, report: dict[str, object]) -> str:
    return _format_rename_report_text(title, report, include_language=True)


def format_code_rename_observation(title: str, root: Path, observation: object) -> str:
    return format_code_rename_report_text(title, _rename_observation_report(root, observation, max_files=100, max_replacements=2000))


def parse_symbol_path_argument(
    argument: str | None,
    *,
    symbol: str | None = None,
    path: str | None = None,
    usage: str,
) -> tuple[str, str | None]:
    if symbol is not None:
        parsed_symbol = symbol.strip()
        if not parsed_symbol:
            raise ValueError(f"{usage} requires a non-empty symbol.")
        if "\n" in parsed_symbol or "\r" in parsed_symbol:
            raise ValueError("symbol must be a single-line string.")
        return parsed_symbol, path.strip() if path and path.strip() else None

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires a symbol.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if not parts:
        raise ValueError(f"{usage} requires a symbol.")
    if len(parts) > 2:
        raise ValueError("expected a symbol and optional path.")
    parsed_symbol = parts[0].strip()
    if not parsed_symbol:
        raise ValueError(f"{usage} requires a non-empty symbol.")
    if "\n" in parsed_symbol or "\r" in parsed_symbol:
        raise ValueError("symbol must be a single-line string.")
    return parsed_symbol, parts[1] if len(parts) == 2 else None


def parse_rename_argument(
    argument: str | None,
    *,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    usage: str,
) -> tuple[str, str, str | None]:
    if symbol is not None or new_name is not None:
        if symbol is None or new_name is None:
            raise ValueError(f"{usage} requires both symbol and new_name.")
        parsed_symbol = symbol.strip()
        parsed_new_name = new_name.strip()
        if not parsed_symbol:
            raise ValueError(f"{usage} requires a non-empty symbol.")
        if not parsed_new_name:
            raise ValueError(f"{usage} requires a non-empty new_name.")
        if "\n" in parsed_symbol or "\r" in parsed_symbol or "\n" in parsed_new_name or "\r" in parsed_new_name:
            raise ValueError("symbol and new_name must be single-line strings.")
        return parsed_symbol, parsed_new_name, path.strip() if path and path.strip() else None

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires symbol and new_name.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) < 2:
        raise ValueError(f"{usage} requires symbol and new_name.")
    if len(parts) > 3:
        raise ValueError("expected symbol, new_name, and optional path.")
    parsed_symbol = parts[0].strip()
    parsed_new_name = parts[1].strip()
    if not parsed_symbol:
        raise ValueError(f"{usage} requires a non-empty symbol.")
    if not parsed_new_name:
        raise ValueError(f"{usage} requires a non-empty new_name.")
    if "\n" in parsed_symbol or "\r" in parsed_symbol or "\n" in parsed_new_name or "\r" in parsed_new_name:
        raise ValueError("symbol and new_name must be single-line strings.")
    return parsed_symbol, parsed_new_name, parts[2] if len(parts) == 3 else None


def parse_replace_python_definition_argument(
    argument: str | None,
    *,
    symbol: str | None = None,
    content: str | None = None,
    path: str | None = None,
    usage: str,
) -> tuple[str, str, str | None]:
    if symbol is not None or content is not None:
        if symbol is None or content is None:
            raise ValueError(f"{usage} requires both symbol and content.")
        parsed_symbol = symbol.strip()
        if not parsed_symbol:
            raise ValueError(f"{usage} requires a non-empty symbol.")
        if "\n" in parsed_symbol or "\r" in parsed_symbol:
            raise ValueError("symbol must be a single-line string.")
        parsed_content = decode_stdin_escapes(content)
        if not parsed_content.strip():
            raise ValueError(f"{usage} requires non-empty content.")
        return parsed_symbol, parsed_content, path.strip() if path and path.strip() else None

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires symbol and content.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) < 2:
        raise ValueError(f"{usage} requires symbol and content.")
    if len(parts) > 3:
        raise ValueError("expected symbol, content, and optional path.")
    parsed_symbol = parts[0].strip()
    if not parsed_symbol:
        raise ValueError(f"{usage} requires a non-empty symbol.")
    if "\n" in parsed_symbol or "\r" in parsed_symbol:
        raise ValueError("symbol must be a single-line string.")
    parsed_content = decode_stdin_escapes(parts[1])
    if not parsed_content.strip():
        raise ValueError(f"{usage} requires non-empty content.")
    return parsed_symbol, parsed_content, parts[2] if len(parts) == 3 else None
