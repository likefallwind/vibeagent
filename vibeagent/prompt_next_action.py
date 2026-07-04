from __future__ import annotations

from .prompt_next_action_checkpoint import CHECKPOINT_NEXT_ACTION_KINDS, checkpoint_next_action_instruction
from .prompt_next_action_completion import COMPLETION_NEXT_ACTION_KINDS, completion_next_action_instruction
from .prompt_next_action_edit import EDIT_NEXT_ACTION_KINDS, edit_next_action_instruction
from .prompt_next_action_error import ERROR_NEXT_ACTION_KINDS, error_next_action_instruction
from .prompt_next_action_git import GIT_NEXT_ACTION_KINDS, git_next_action_instruction
from .prompt_next_action_project import PROJECT_NEXT_ACTION_KINDS, project_next_action_instruction
from .prompt_next_action_read import READ_NEXT_ACTION_KINDS, read_next_action_instruction
from .prompt_next_action_runtime import RUNTIME_NEXT_ACTION_KINDS, runtime_next_action_instruction
from .prompt_next_action_session import SESSION_NEXT_ACTION_KINDS, session_next_action_instruction
from .types import Observation


def get_next_action_instruction(task: str, observations: list[Observation]) -> str:
    base = "Choose the next response: call a tool if needed, or answer directly if the task is complete."
    if not observations:
        return base

    latest = observations[-1]
    runtime_instruction = runtime_next_action_instruction(base, observations)
    if runtime_instruction is not None:
        return runtime_instruction

    if latest.kind in ERROR_NEXT_ACTION_KINDS:
        return error_next_action_instruction(base, latest)

    if latest.kind in COMPLETION_NEXT_ACTION_KINDS:
        return completion_next_action_instruction(base, latest)

    if latest.kind in SESSION_NEXT_ACTION_KINDS:
        return session_next_action_instruction(base, latest)

    if latest.kind in CHECKPOINT_NEXT_ACTION_KINDS:
        return checkpoint_next_action_instruction(base, latest)

    if latest.kind in PROJECT_NEXT_ACTION_KINDS:
        return project_next_action_instruction(base, latest)

    if latest.kind in GIT_NEXT_ACTION_KINDS:
        return git_next_action_instruction(base, latest)

    if latest.kind in EDIT_NEXT_ACTION_KINDS:
        return edit_next_action_instruction(base, latest)

    if latest.kind in READ_NEXT_ACTION_KINDS:
        return read_next_action_instruction(base, latest)

    if latest.kind == "python_traceback":
        return (
            f"{base} Do not repeat inspection unless you need specific missing information. "
            "If you already created the requested files, run one appropriate check or answer directly if the task is complete."
        )

    if latest.kind in RUNTIME_NEXT_ACTION_KINDS:
        return f"{base} Use the repository or session information to decide whether to continue, run a check, or answer directly."

    return f"{base} If the task is complete, answer directly or use finish."
