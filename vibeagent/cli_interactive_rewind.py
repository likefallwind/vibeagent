from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shlex

from .command_types import LocalCommand
from .session_rewind import (
    SessionRewindResult,
    format_session_rewind_points,
    rewind_session,
)


_MODES = {"both", "code", "conversation"}


def run_interactive_rewind_command(
    command: LocalCommand,
    *,
    project_root: Path,
    run_id: str | None,
    get_resume_context: Callable[..., tuple[str | None, str | None, str]],
) -> SessionRewindResult | None:
    if command.type != "rewind":
        return None
    if command.argument is None:
        return SessionRewindResult(format_session_rewind_points(project_root, run_id))
    try:
        parts = shlex.split(command.argument)
    except ValueError as error:
        return SessionRewindResult(f"Rewind error: {error}", error=str(error))
    if not 1 <= len(parts) <= 2 or (len(parts) == 2 and parts[1] not in _MODES):
        message = "Usage: /rewind [checkpoint-id|latest] [both|code|conversation]"
        return SessionRewindResult(message, error=message)
    mode = parts[1] if len(parts) == 2 else "both"
    return rewind_session(
        project_root,
        run_id,
        parts[0],
        mode,  # type: ignore[arg-type]
        get_resume_context=get_resume_context,
    )


__all__ = ["run_interactive_rewind_command"]
