from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .local_command_workspace import local_command_workspace
from .output_serialization import serialize_output_context_result, serialize_output_diagnostic
from .project_output_reports import (
    format_output_contexts_report_text,
    format_output_diagnostics_report_text,
    format_python_traceback_report_text,
    indent_block as _indent_block,
)
from .types import OutputContextsAction, OutputDiagnosticsAction

OUTPUT_CONTEXTS_USAGE = "Usage: /output-contexts <text>"
OUTPUT_DIAGNOSTICS_USAGE = "Usage: /output-diagnostics <text>"
PYTHON_TRACEBACK_USAGE = "Usage: /python-traceback <text>"


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def _usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def get_output_contexts_text(
    project_root: str | Path = ".",
    text: str | None = None,
    context_lines: int = 5,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    if not text or not text.strip():
        return OUTPUT_CONTEXTS_USAGE
    if len(text) > 200_000:
        return _usage_error(OUTPUT_CONTEXTS_USAGE, "text must be at most 200000 characters.")
    if context_lines < 0:
        return _usage_error(OUTPUT_CONTEXTS_USAGE, "context_lines must be at least 0.")
    if context_lines > 500:
        return _usage_error(OUTPUT_CONTEXTS_USAGE, "context_lines must be at most 500.")
    if max_contexts < 1:
        return _usage_error(OUTPUT_CONTEXTS_USAGE, "max_contexts must be at least 1.")
    if max_contexts > 100:
        return _usage_error(OUTPUT_CONTEXTS_USAGE, "max_contexts must be at most 100.")
    if max_bytes_per_context < 1_000:
        return _usage_error(OUTPUT_CONTEXTS_USAGE, "max_bytes_per_context must be at least 1000.")
    if max_bytes_per_context > 200_000:
        return _usage_error(OUTPUT_CONTEXTS_USAGE, "max_bytes_per_context must be at most 200000.")

    root = Path(project_root).resolve()
    workspace = local_command_workspace(root, "local-output-contexts")
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
            "message": OUTPUT_CONTEXTS_USAGE,
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
            "message": _usage_error(OUTPUT_CONTEXTS_USAGE, "text must be at most 200000 characters."),
        }
    if context_lines < 0:
        message = _usage_error(OUTPUT_CONTEXTS_USAGE, "context_lines must be at least 0.")
    elif context_lines > 500:
        message = _usage_error(OUTPUT_CONTEXTS_USAGE, "context_lines must be at most 500.")
    elif max_contexts < 1:
        message = _usage_error(OUTPUT_CONTEXTS_USAGE, "max_contexts must be at least 1.")
    elif max_contexts > 100:
        message = _usage_error(OUTPUT_CONTEXTS_USAGE, "max_contexts must be at most 100.")
    elif max_bytes_per_context < 1_000:
        message = _usage_error(OUTPUT_CONTEXTS_USAGE, "max_bytes_per_context must be at least 1000.")
    elif max_bytes_per_context > 200_000:
        message = _usage_error(OUTPUT_CONTEXTS_USAGE, "max_bytes_per_context must be at most 200000.")
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

    workspace = local_command_workspace(root, "local-output-contexts")
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
    if len(text) > 200_000:
        return _usage_error(OUTPUT_DIAGNOSTICS_USAGE, "text must be at most 200000 characters.")
    if context_lines < 0:
        return _usage_error(OUTPUT_DIAGNOSTICS_USAGE, "context_lines must be at least 0.")
    if context_lines > 500:
        return _usage_error(OUTPUT_DIAGNOSTICS_USAGE, "context_lines must be at most 500.")
    if max_diagnostics < 1:
        return _usage_error(OUTPUT_DIAGNOSTICS_USAGE, "max_diagnostics must be at least 1.")
    if max_diagnostics > 200:
        return _usage_error(OUTPUT_DIAGNOSTICS_USAGE, "max_diagnostics must be at most 200.")
    if max_contexts < 1:
        return _usage_error(OUTPUT_DIAGNOSTICS_USAGE, "max_contexts must be at least 1.")
    if max_contexts > 100:
        return _usage_error(OUTPUT_DIAGNOSTICS_USAGE, "max_contexts must be at most 100.")
    if max_bytes_per_context < 1_000:
        return _usage_error(OUTPUT_DIAGNOSTICS_USAGE, "max_bytes_per_context must be at least 1000.")
    if max_bytes_per_context > 200_000:
        return _usage_error(OUTPUT_DIAGNOSTICS_USAGE, "max_bytes_per_context must be at most 200000.")

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
