from __future__ import annotations

from typing import Any

from .action_parsing_helpers import parse_optional_positive_int
from .action_parsing_session_fields import (
    parse_output_context_limits,
    parse_run_id,
    parse_session_command_limits,
)
from .types import (
    SessionCommandsAction,
    SessionOutputContextsAction,
    SessionOutputDiagnosticsAction,
)


SESSION_OUTPUT_ACTION_TYPES = {
    "session_commands",
    "session_output_contexts",
    "session_output_diagnostics",
}


def parse_session_output_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type == "session_commands":
        run_id = parse_run_id(value.get("run_id"), raw, "session_commands")
        max_commands, max_output_chars = parse_session_command_limits(
            {**value, "max_output_chars": value.get("max_output_chars", 2_000)},
            raw,
        )
        return SessionCommandsAction(
            type="session_commands",
            run_id=run_id,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
        )

    if action_type == "session_output_contexts":
        run_id = parse_run_id(value.get("run_id"), raw, "session_output_contexts")
        max_commands, max_output_chars = parse_session_command_limits(value, raw)
        context_lines, max_contexts, max_bytes_per_context = parse_output_context_limits(value, raw, default_context_lines=5)
        parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200)
        return SessionOutputContextsAction(
            type="session_output_contexts",
            run_id=run_id,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
            context_lines=context_lines,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "session_output_diagnostics":
        run_id = parse_run_id(value.get("run_id"), raw, "session_output_diagnostics")
        max_commands, max_output_chars = parse_session_command_limits(value, raw)
        context_lines, max_contexts, max_bytes_per_context = parse_output_context_limits(value, raw, default_context_lines=2)
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
        return SessionOutputDiagnosticsAction(
            type="session_output_diagnostics",
            run_id=run_id,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    return None
