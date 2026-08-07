from __future__ import annotations

from .types import (
    CheckCreateDirectoriesAction,
    CheckCreateDirectoriesObservation,
    CheckCreateDirectoryAction,
    CheckCreateDirectoryObservation,
    CreateDirectoriesAction,
    CreateDirectoriesObservation,
    CreateDirectoryAction,
    CreateDirectoryObservation,
    Observation,
)
from .workspace import (
    RunWorkspace,
    create_project_directories,
    create_project_directory,
    preview_create_project_directories,
    preview_create_project_directory,
)


def execute_directory_create_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, CheckCreateDirectoryAction):
        try:
            preview_create_project_directory(workspace, action.path)
            ok = True
            message = f"Directory creation can apply to {action.path}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCreateDirectoryObservation(
            kind="check_create_dir",
            path=action.path,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCreateDirectoriesAction):
        try:
            preview_create_project_directories(workspace, action.paths)
            ok = True
            message = f"Directory creation can apply to {len(action.paths)} path(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCreateDirectoriesObservation(
            kind="check_create_dirs",
            paths=action.paths,
            ok=ok,
            message=message,
        )

    if isinstance(action, CreateDirectoryAction):
        try:
            create_project_directory(workspace, action.path)
            ok = True
            message = f"Created directory {action.path}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CreateDirectoryObservation(
            kind="create_dir",
            path=action.path,
            ok=ok,
            message=message,
        )

    if isinstance(action, CreateDirectoriesAction):
        try:
            create_project_directories(workspace, action.paths)
            ok = True
            message = f"Created {len(action.paths)} directory path(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CreateDirectoriesObservation(
            kind="create_dirs",
            paths=action.paths,
            ok=ok,
            message=message,
        )

    return None
