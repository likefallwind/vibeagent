from __future__ import annotations

from pathlib import Path

from .command_parsing import parse_optional_single_path_argument
from .smart_code_common import (
    commands_attr as _commands_attr,
    execute_action_for_commands as _execute_action,
    plain_data as _plain_data,
    symbol_report_base as _symbol_report_base,
)
from .smart_code_parsing import parse_symbol_path_argument
from .types import (
    PythonCallGraphAction,
    PythonCallsAction,
    PythonDefinitionsAction,
    PythonReferenceContextsAction,
    PythonReferencesAction,
)
from .workspace_core import RunWorkspace


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
