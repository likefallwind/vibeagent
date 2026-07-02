from __future__ import annotations

from pathlib import Path

from .command_parsing import parse_optional_single_path_argument
from .edit_commands import format_check_location
from .smart_code_common import (
    commands_attr as _commands_attr,
    execute_action_for_commands as _execute_action,
    format_rename_report_text as _format_rename_report_text,
    plain_data as _plain_data,
    rename_observation_report as _rename_observation_report,
    rename_unexpected_report as _rename_unexpected_report,
    rename_usage_report as _rename_usage_report,
    symbol_report_base as _symbol_report_base,
)
from .smart_code_formatting import (
    format_code_defs_report_text,
    format_code_deps_report_text,
    format_code_ref_contexts_report_text,
    format_code_refs_report_text,
)
from .smart_code_parsing import parse_rename_argument, parse_replace_python_definition_argument, parse_symbol_path_argument
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


def format_python_rename_report_text(title: str, report: dict[str, object]) -> str:
    return _format_rename_report_text(title, report, include_language=False)


def format_python_rename_observation(title: str, root: Path, observation: object) -> str:
    return format_python_rename_report_text(title, _rename_observation_report(root, observation, max_files=100, max_replacements=2000))
