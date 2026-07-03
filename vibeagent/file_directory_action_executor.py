from __future__ import annotations

from .action_parsing_helpers import directory_transfer_pairs, format_file_mode
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
    CheckSetExecutableAction,
    CheckSetExecutableObservation,
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
    SetExecutableAction,
    SetExecutableObservation,
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
    preview_set_project_file_executable,
    set_project_file_executable,
)


def execute_directory_file_action(workspace: RunWorkspace, action: object) -> Observation | None:
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
