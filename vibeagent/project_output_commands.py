from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .local_command_workspace import local_command_workspace
from .output_serialization import serialize_output_context_result
from .project_output_diagnostic_commands import (
    OUTPUT_DIAGNOSTICS_USAGE,
    PYTHON_TRACEBACK_USAGE,
    get_output_diagnostics_report,
    get_output_diagnostics_text,
    get_python_traceback_report,
    get_python_traceback_text,
)
from .project_output_reports import (
    format_output_contexts_report_text,
    format_output_diagnostics_report_text,
    format_python_traceback_report_text,
    indent_block as _indent_block,
)
from .project_output_validation import validate_output_context_options
from .types import OutputContextsAction

OUTPUT_CONTEXTS_USAGE = "Usage: /output-contexts <text>"


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
        return OUTPUT_CONTEXTS_USAGE
    validation_error = validate_output_context_options(
        OUTPUT_CONTEXTS_USAGE,
        text=text,
        context_lines=context_lines,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
    )
    if validation_error:
        return validation_error

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
    message = validate_output_context_options(
        OUTPUT_CONTEXTS_USAGE,
        text=text,
        context_lines=context_lines,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
    ) or ""
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
