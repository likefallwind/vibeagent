from __future__ import annotations

from .action_parsing_helpers import format_file_mode
from .types import (
    CheckSetExecutableAction,
    CheckSetExecutableObservation,
    Observation,
    SetExecutableAction,
    SetExecutableObservation,
)
from .workspace import (
    RunWorkspace,
    preview_set_project_file_executable,
    set_project_file_executable,
)


def execute_executable_file_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, CheckSetExecutableAction):
        try:
            _path, before, after = preview_set_project_file_executable(workspace, action.path, executable=action.executable)
            ok = True
            state = "executable" if action.executable else "not executable"
            message = f"Executable bit change can apply to set {action.path} {state}."
        except ValueError as error:
            before = 0
            after = 0
            ok = False
            message = str(error)
        return CheckSetExecutableObservation(
            kind="check_set_executable",
            path=action.path,
            executable=action.executable,
            ok=ok,
            mode_before=format_file_mode(before),
            mode_after=format_file_mode(after),
            message=message,
        )

    if isinstance(action, SetExecutableAction):
        try:
            _path, before, after = set_project_file_executable(workspace, action.path, executable=action.executable)
            ok = True
            state = "executable" if action.executable else "not executable"
            message = f"Set {action.path} {state}."
        except ValueError as error:
            before = 0
            after = 0
            ok = False
            message = str(error)
        return SetExecutableObservation(
            kind="set_executable",
            path=action.path,
            executable=action.executable,
            ok=ok,
            mode_before=format_file_mode(before),
            mode_after=format_file_mode(after),
            message=message,
        )

    return None
