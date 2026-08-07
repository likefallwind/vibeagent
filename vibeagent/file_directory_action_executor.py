from __future__ import annotations

from .action_parsing_helpers import directory_transfer_pairs
from .file_executable_action_executor import execute_executable_file_action
from .types import (
    CheckCreateDirectoryAction,
    CheckCreateDirectoryObservation,
    CheckCreateDirectoriesAction,
    CheckCreateDirectoriesObservation,
    CheckCopyDirectoryAction,
    CheckCopyDirectoryObservation,
    CheckCopyDirectoriesAction,
    CheckCopyDirectoriesObservation,
    CheckDeleteEmptyDirectoryAction,
    CheckDeleteEmptyDirectoryObservation,
    CheckDeleteEmptyDirectoriesAction,
    CheckDeleteEmptyDirectoriesObservation,
    CheckMoveDirectoryAction,
    CheckMoveDirectoryObservation,
    CheckMoveDirectoriesAction,
    CheckMoveDirectoriesObservation,
    CopyDirectoryAction,
    CopyDirectoryObservation,
    CopyDirectoriesAction,
    CopyDirectoriesObservation,
    CreateDirectoryAction,
    CreateDirectoryObservation,
    CreateDirectoriesAction,
    CreateDirectoriesObservation,
    DeleteEmptyDirectoryAction,
    DeleteEmptyDirectoryObservation,
    DeleteEmptyDirectoriesAction,
    DeleteEmptyDirectoriesObservation,
    MoveDirectoryAction,
    MoveDirectoryObservation,
    MoveDirectoriesAction,
    MoveDirectoriesObservation,
    Observation,
)
from .workspace import (
    RunWorkspace,
    copy_project_directory,
    copy_project_directories,
    create_project_directories,
    create_project_directory,
    delete_project_empty_directories,
    delete_project_empty_directory,
    move_project_directories,
    move_project_directory,
    preview_copy_project_directories,
    preview_copy_project_directory,
    preview_create_project_directories,
    preview_create_project_directory,
    preview_delete_project_empty_directories,
    preview_delete_project_empty_directory,
    preview_move_project_directories,
    preview_move_project_directory,
)


def execute_directory_file_action(workspace: RunWorkspace, action: object) -> Observation | None:
    executable_observation = execute_executable_file_action(workspace, action)
    if executable_observation is not None:
        return executable_observation

    if isinstance(action, CheckMoveDirectoryAction):
        try:
            preview_move_project_directory(workspace, action.source, action.destination)
            ok = True
            message = f"Directory move can apply from {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckMoveDirectoryObservation(
            kind="check_move_dir",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, MoveDirectoryAction):
        try:
            move_project_directory(workspace, action.source, action.destination)
            ok = True
            message = f"Moved directory {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return MoveDirectoryObservation(
            kind="move_dir",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckMoveDirectoriesAction):
        try:
            preview_move_project_directories(workspace, directory_transfer_pairs(action.transfers))
            ok = True
            message = f"Directory move can apply to {len(action.transfers)} transfer(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckMoveDirectoriesObservation(
            kind="check_move_dirs",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, MoveDirectoriesAction):
        try:
            move_project_directories(workspace, directory_transfer_pairs(action.transfers))
            ok = True
            message = f"Moved {len(action.transfers)} directory transfer(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return MoveDirectoriesObservation(
            kind="move_dirs",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCopyDirectoryAction):
        try:
            preview_copy_project_directory(workspace, action.source, action.destination)
            ok = True
            message = f"Directory copy can apply from {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCopyDirectoryObservation(
            kind="check_copy_dir",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCopyDirectoriesAction):
        try:
            preview_copy_project_directories(workspace, directory_transfer_pairs(action.transfers))
            ok = True
            message = f"Directory copy can apply to {len(action.transfers)} transfer(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCopyDirectoriesObservation(
            kind="check_copy_dirs",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CopyDirectoryAction):
        try:
            copy_project_directory(workspace, action.source, action.destination)
            ok = True
            message = f"Copied directory {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CopyDirectoryObservation(
            kind="copy_dir",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CopyDirectoriesAction):
        try:
            copy_project_directories(workspace, directory_transfer_pairs(action.transfers))
            ok = True
            message = f"Copied {len(action.transfers)} directory transfer(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CopyDirectoriesObservation(
            kind="copy_dirs",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

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
