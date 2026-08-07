from __future__ import annotations

from .agent_observation_utils import summarize
from . import types as t


def build_process_step_label(action: object) -> str | None:
    if isinstance(action, t.RunCommandAction):
        suffix = f" in {action.cwd}" if action.cwd else ""
        if action.description:
            return f"Run: {summarize(action.description, 80)}{suffix}"
        return f"Run {summarize(action.command, 80)}{suffix}"
    if isinstance(action, t.RunSessionVerificationAction):
        return f"Run session verification {action.run_id or 'current'}"
    if isinstance(action, t.StartCommandAction):
        suffix = f" in {action.cwd}" if action.cwd else ""
        if action.description:
            return f"Start: {summarize(action.description, 80)}{suffix}"
        return f"Start {summarize(action.command, 80)}{suffix}"
    if isinstance(action, t.ReadProcessAction):
        return f"Read process {action.process_id}"
    if isinstance(action, t.ListProcessesAction):
        return "List background processes"
    if isinstance(action, t.CheckStopAllProcessesAction):
        return "Check stop all background processes"
    if isinstance(action, t.StopProcessAction):
        return f"Stop process {action.process_id}"
    if isinstance(action, t.StopAllProcessesAction):
        return "Stop all background processes"
    return None
