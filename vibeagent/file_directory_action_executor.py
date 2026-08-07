from __future__ import annotations

from .file_directory_copy_action_executor import execute_directory_copy_action
from .file_directory_create_action_executor import execute_directory_create_action
from .file_directory_move_action_executor import execute_directory_move_action
from .file_executable_action_executor import execute_executable_file_action
from .types import (
    CheckDeleteEmptyDirectoryAction,
    CheckDeleteEmptyDirectoryObservation,
    CheckDeleteEmptyDirectoriesAction,
    CheckDeleteEmptyDirectoriesObservation,
    DeleteEmptyDirectoryAction,
    DeleteEmptyDirectoryObservation,
    DeleteEmptyDirectoriesAction,
    DeleteEmptyDirectoriesObservation,
    Observation,
)
from .workspace import (
    RunWorkspace,
    delete_project_empty_directories,
    delete_project_empty_directory,
    preview_delete_project_empty_directories,
    preview_delete_project_empty_directory,
)


def execute_directory_file_action(workspace: RunWorkspace, action: object) -> Observation | None:
    executable_observation = execute_executable_file_action(workspace, action)
    if executable_observation is not None:
        return executable_observation

    move_observation = execute_directory_move_action(workspace, action)
    if move_observation is not None:
        return move_observation

    copy_observation = execute_directory_copy_action(workspace, action)
    if copy_observation is not None:
        return copy_observation

    create_observation = execute_directory_create_action(workspace, action)
    if create_observation is not None:
        return create_observation

    if isinstance(action, CheckDeleteEmptyDirectoryAction):
        try:
            preview_delete_project_empty_directory(workspace, action.path)
            ok = True
            message = f"Empty directory deletion can apply to {action.path}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckDeleteEmptyDirectoryObservation(
            kind="check_delete_empty_dir",
            path=action.path,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckDeleteEmptyDirectoriesAction):
        try:
            preview_delete_project_empty_directories(workspace, action.paths)
            ok = True
            message = f"Empty directory deletion can apply to {len(action.paths)} path(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckDeleteEmptyDirectoriesObservation(
            kind="check_delete_empty_dirs",
            paths=action.paths,
            ok=ok,
            message=message,
        )

    if isinstance(action, DeleteEmptyDirectoryAction):
        try:
            delete_project_empty_directory(workspace, action.path)
            ok = True
            message = f"Deleted empty directory {action.path}."
        except ValueError as error:
            ok = False
            message = str(error)
        return DeleteEmptyDirectoryObservation(
            kind="delete_empty_dir",
            path=action.path,
            ok=ok,
            message=message,
        )

    if isinstance(action, DeleteEmptyDirectoriesAction):
        try:
            delete_project_empty_directories(workspace, action.paths)
            ok = True
            message = f"Deleted {len(action.paths)} empty directory path(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return DeleteEmptyDirectoriesObservation(
            kind="delete_empty_dirs",
            paths=action.paths,
            ok=ok,
            message=message,
        )

    return None
