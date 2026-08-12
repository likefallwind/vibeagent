from __future__ import annotations

from typing import Any

from .action_parsing_scalars import ActionParseError, parse_nonnegative_int, parse_optional_positive_int
from .action_parsing_sandbox import parse_dangerously_disable_sandbox
from .types import RunCommandItem


def parse_run_command_items(value: Any, raw: str, action_type: str) -> list[RunCommandItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError(f"{action_type} action requires a non-empty commands list.", raw)
    if len(value) > 10:
        raise ActionParseError(f"{action_type} action commands must contain at most 10 items.", raw)

    commands: list[RunCommandItem] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"{action_type} command {index} must be an object.", raw)
        command = item.get("command")
        if not isinstance(command, str) or not command.strip():
            raise ActionParseError(f"{action_type} command {index} requires a non-empty command.", raw)
        cwd = item.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise ActionParseError(f"{action_type} command {index} cwd must be a string when provided.", raw)
        description = item.get("description")
        if description is not None and (not isinstance(description, str) or not description.strip()):
            raise ActionParseError(
                f"{action_type} command {index} description must be a non-empty string when provided.",
                raw,
            )
        timeout_ms = parse_optional_positive_int(item.get("timeout_ms"), f"{action_type} command {index} timeout_ms", raw, maximum=600_000)
        if timeout_ms is not None and timeout_ms < 100:
            raise ActionParseError(f"{action_type} command {index} timeout_ms must be at least 100.", raw)
        max_output_chars = parse_optional_positive_int(
            item.get("max_output_chars"),
            f"{action_type} command {index} max_output_chars",
            raw,
            maximum=50_000,
        )
        if max_output_chars is not None and max_output_chars < 1_000:
            raise ActionParseError(f"{action_type} command {index} max_output_chars must be at least 1000.", raw)
        extract_output_contexts = item.get("extract_output_contexts", False)
        if not isinstance(extract_output_contexts, bool):
            raise ActionParseError(f"{action_type} command {index} extract_output_contexts must be a boolean.", raw)
        extract_output_diagnostics = item.get("extract_output_diagnostics", False)
        if not isinstance(extract_output_diagnostics, bool):
            raise ActionParseError(f"{action_type} command {index} extract_output_diagnostics must be a boolean.", raw)
        context_lines = parse_nonnegative_int(
            item.get("context_lines", 5),
            f"{action_type} command {index} context_lines",
            raw,
            maximum=500,
        )
        max_diagnostics = parse_optional_positive_int(
            item.get("max_diagnostics", 50),
            f"{action_type} command {index} max_diagnostics",
            raw,
            maximum=200,
        ) or 50
        max_contexts = parse_optional_positive_int(
            item.get("max_contexts", 20),
            f"{action_type} command {index} max_contexts",
            raw,
            maximum=100,
        ) or 20
        max_bytes_per_context = parse_optional_positive_int(
            item.get("max_bytes_per_context", 20_000),
            f"{action_type} command {index} max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1_000:
            raise ActionParseError(f"{action_type} command {index} max_bytes_per_context must be at least 1000.", raw)
        commands.append(
            RunCommandItem(
                command=command.strip(),
                timeout_ms=timeout_ms,
                cwd=cwd,
                max_output_chars=max_output_chars,
                extract_output_contexts=extract_output_contexts,
                extract_output_diagnostics=extract_output_diagnostics,
                context_lines=context_lines,
                max_diagnostics=max_diagnostics,
                max_contexts=max_contexts,
                max_bytes_per_context=max_bytes_per_context,
                description=description.strip() if isinstance(description, str) else None,
                dangerously_disable_sandbox=parse_dangerously_disable_sandbox(
                    item,
                    raw,
                    f"{action_type} command {index}",
                ),
            )
        )
    return commands
