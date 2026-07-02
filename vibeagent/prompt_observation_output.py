from __future__ import annotations

from .prompt_observation_utils import truncate


def format_output_context_item_lines(item: object) -> list[str]:
    column = f":{item.column}" if item.column is not None else ""
    lines = [
        (
            f"context: {item.path}:{item.line}{column} raw={item.raw!r} "
            f"ok={str(item.ok).lower()} range={item.start_line}:{item.end_line} "
            f"contextLines={item.context_lines} targetExists={str(item.target_line_exists).lower()} "
            f"lines={item.line_count}/{item.total_lines if item.total_lines is not None else 'unknown'} "
            f"truncated={str(item.truncated).lower()} maxBytes={item.max_bytes} "
            f"message={item.message}"
        )
    ]
    if item.ok:
        lines.append(f"content:\n{truncate(item.content)}")
    return lines


def format_raw_output_diagnostic(item: object) -> str:
    location = ""
    if item.path:
        location = f" location={item.path}:{item.line if item.line is not None else '?'}"
        if item.column is not None:
            location += f":{item.column}"
    return (
        f"diagnostic: severity={item.severity} outputLine={item.output_line}"
        f"{location} raw={item.raw!r} text={item.text}"
    )


def format_output_contexts_observation(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. output_contexts: {observation.message} "
            f"totalRefs={observation.total_refs} truncated={str(observation.truncated).lower()}"
        )
    ]
    for item in observation.contexts:
        parts.extend(format_output_context_item_lines(item))
    return "\n".join(parts)


def format_output_diagnostics_observation(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. output_diagnostics: {observation.message} "
            f"diagnostics={len(observation.diagnostics)}/{observation.total_diagnostics} "
            f"refs={observation.total_refs} "
            f"diagnosticsTruncated={str(observation.diagnostics_truncated).lower()} "
            f"contextsTruncated={str(observation.contexts_truncated).lower()}"
        )
    ]
    for diagnostic in observation.diagnostics:
        location = (
            f" {diagnostic.path}:{diagnostic.line}{':' + str(diagnostic.column) if diagnostic.column is not None else ''}"
            if diagnostic.path and diagnostic.line is not None
            else ""
        )
        parts.append(
            f"diagnostic: {diagnostic.severity} outputLine={diagnostic.output_line}{location} text={diagnostic.text!r}"
        )
    for item in observation.contexts:
        parts.extend(format_output_context_item_lines(item))
    return "\n".join(parts)


def format_session_output_contexts_observation(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. session_output_contexts {observation.run_id}: {observation.message} "
            f"ok={str(observation.ok).lower()} "
            f"commands={observation.shown_commands}/{observation.command_count} "
            f"totalRefs={observation.total_refs} truncated={str(observation.truncated).lower()}"
        )
    ]
    for item in observation.contexts:
        parts.extend(format_output_context_item_lines(item))
    return "\n".join(parts)


def format_session_output_diagnostics_observation(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. session_output_diagnostics {observation.run_id}: {observation.message} "
            f"ok={str(observation.ok).lower()} "
            f"commands={observation.shown_commands}/{observation.command_count} "
            f"diagnostics={len(observation.diagnostics)}/{observation.total_diagnostics} "
            f"totalRefs={observation.total_refs} "
            f"diagnosticsTruncated={str(observation.diagnostics_truncated).lower()} "
            f"contextsTruncated={str(observation.contexts_truncated).lower()}"
        )
    ]
    for diagnostic in observation.diagnostics:
        parts.append(format_raw_output_diagnostic(diagnostic))
    for item in observation.contexts:
        parts.extend(format_output_context_item_lines(item))
    return "\n".join(parts)


def format_command_output_diagnostics(result: object) -> str:
    diagnostics = getattr(result, "output_diagnostics", [])
    total = getattr(result, "output_diagnostic_total", 0)
    truncated = getattr(result, "output_diagnostics_truncated", False)
    if not diagnostics and not total:
        return "outputDiagnostics: none"
    lines = [
        (
            f"outputDiagnostics: {len(diagnostics)}/{total} "
            f"truncated={str(bool(truncated)).lower()}"
        )
    ]
    for item in diagnostics:
        lines.append(format_raw_output_diagnostic(item))
    return "\n".join(lines)


def format_command_output_contexts(result: object) -> str:
    contexts = getattr(result, "output_contexts", [])
    total_refs = getattr(result, "output_context_total_refs", 0)
    truncated = getattr(result, "output_contexts_truncated", False)
    if not contexts and not total_refs:
        return "outputContexts: none"
    lines = [
        (
            f"outputContexts: {len(contexts)}/{total_refs} "
            f"truncated={str(bool(truncated)).lower()}"
        )
    ]
    for item in contexts:
        lines.extend(format_output_context_item_lines(item))
    return "\n".join(lines)


__all__ = [
    "format_command_output_contexts",
    "format_command_output_diagnostics",
    "format_output_context_item_lines",
    "format_output_contexts_observation",
    "format_output_diagnostics_observation",
    "format_raw_output_diagnostic",
    "format_session_output_contexts_observation",
    "format_session_output_diagnostics_observation",
]
