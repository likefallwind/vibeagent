from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .output_serialization import serialize_output_context_result, serialize_output_diagnostic
from .types import OutputContextsAction, OutputDiagnosticsAction
from .workspace_core import RunWorkspace


def _indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


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
