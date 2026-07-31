from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .local_command_workspace import local_command_workspace
from .output_serialization import serialize_output_context_result, serialize_output_diagnostic
from .project_output_reports import indent_block as _indent_block
from .project_output_validation import validate_output_diagnostic_options
from .types import OutputDiagnosticsAction

OUTPUT_DIAGNOSTICS_USAGE = "Usage: /output-diagnostics <text>"
PYTHON_TRACEBACK_USAGE = "Usage: /python-traceback <text>"


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def get_output_diagnostics_text(
    project_root: str | Path = ".",
    text: str | None = None,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    if not text or not text.strip():
        return OUTPUT_DIAGNOSTICS_USAGE
    validation_error = validate_output_diagnostic_options(
        OUTPUT_DIAGNOSTICS_USAGE,
        text=text,
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
    )
    if validation_error:
        return validation_error

    root = Path(project_root).resolve()
    workspace = local_command_workspace(root, "local-output-diagnostics")
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
    message = validate_output_diagnostic_options(
        f"Usage: {usage}",
        text=text,
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
    ) or ""
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

    workspace = local_command_workspace(root, "local-output-diagnostics")
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
        usage=PYTHON_TRACEBACK_USAGE.removeprefix("Usage: "),
    )


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
        .replace(OUTPUT_DIAGNOSTICS_USAGE, PYTHON_TRACEBACK_USAGE, 1)
    )
