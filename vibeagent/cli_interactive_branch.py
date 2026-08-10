from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .session_branching import create_session_branch
from .workspace_core import RunWorkspace


@dataclass(frozen=True)
class InteractiveBranchSwitch:
    workspace: RunWorkspace | None = None
    source_run_id: str | None = None
    context: str | None = None
    text: str = ""
    error: str | None = None


def prepare_interactive_branch_switch(
    project_root: Path,
    current_run_id: str | None,
    name: str | None,
    additional_directories: tuple[Path, ...],
    *,
    get_resume_context: Callable[..., tuple[str | None, str | None, str]],
) -> InteractiveBranchSwitch:
    if current_run_id is None:
        return InteractiveBranchSwitch(error="no coding session is active.")
    selected, context, context_text = get_resume_context(current_run_id)
    if selected is None or context is None:
        return InteractiveBranchSwitch(error=context_text)
    try:
        branch = create_session_branch(
            project_root,
            selected,
            name=name,
            additional_directories=additional_directories,
        )
    except (OSError, ValueError) as error:
        return InteractiveBranchSwitch(error=str(error))
    return InteractiveBranchSwitch(
        workspace=branch.workspace,
        source_run_id=selected,
        context=context,
        text=branch.text,
    )


__all__ = ["InteractiveBranchSwitch", "prepare_interactive_branch_switch"]
