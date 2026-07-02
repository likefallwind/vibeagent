from __future__ import annotations

from .types import (
    CheckCopyFileAction,
    CheckCopyFileObservation,
    CheckCopyFilesAction,
    CheckCopyFilesObservation,
    CheckDeleteFileAction,
    CheckDeleteFileObservation,
    CheckDeleteFilesAction,
    CheckDeleteFilesObservation,
    CheckMoveFileAction,
    CheckMoveFileObservation,
    CheckMoveFilesAction,
    CheckMoveFilesObservation,
    CopyFileAction,
    CopyFileObservation,
    CopyFilesAction,
    CopyFilesObservation,
    DeleteFileAction,
    DeleteFileObservation,
    DeleteFilesAction,
    DeleteFilesObservation,
    MoveFileAction,
    MoveFileObservation,
    MoveFilesAction,
    MoveFilesObservation,
    Observation,
)
from .workspace import (
    RunWorkspace,
    copy_project_file,
    copy_project_files,
    delete_project_file,
    delete_project_files,
    move_project_file,
    move_project_files,
    preview_copy_project_file,
    preview_copy_project_files,
    preview_delete_project_file,
    preview_delete_project_files,
    preview_move_project_file,
    preview_move_project_files,
)


def execute_path_file_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, CheckDeleteFileAction):
        try:
            _, diff = preview_delete_project_file(workspace, action.path)
            ok = True
            message = f"Delete can apply to {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckDeleteFileObservation(
            kind="check_delete_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, DeleteFileAction):
        try:
            _, diff = delete_project_file(workspace, action.path)
            ok = True
            message = f"Deleted {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return DeleteFileObservation(
            kind="delete_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckDeleteFilesAction):
        try:
            _, diff = preview_delete_project_files(workspace, action.paths)
            ok = True
            message = f"Delete can apply to {len(action.paths)} file(s)."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckDeleteFilesObservation(
            kind="check_delete_files",
            paths=action.paths,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, DeleteFilesAction):
        try:
            _, diff = delete_project_files(workspace, action.paths)
            ok = True
            message = f"Deleted {len(action.paths)} file(s)."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return DeleteFilesObservation(
            kind="delete_files",
            paths=action.paths,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckMoveFileAction):
        try:
            preview_move_project_file(workspace, action.source, action.destination)
            ok = True
            message = f"Move can apply from {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckMoveFileObservation(
            kind="check_move_file",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, MoveFileAction):
        try:
            move_project_file(workspace, action.source, action.destination)
            ok = True
            message = f"Moved {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return MoveFileObservation(
            kind="move_file",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckMoveFilesAction):
        try:
            preview_move_project_files(workspace, [transfer.__dict__ for transfer in action.transfers])
            ok = True
            message = f"Move can apply to {len(action.transfers)} file(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckMoveFilesObservation(
            kind="check_move_files",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, MoveFilesAction):
        try:
            move_project_files(workspace, [transfer.__dict__ for transfer in action.transfers])
            ok = True
            message = f"Moved {len(action.transfers)} file(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return MoveFilesObservation(
            kind="move_files",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCopyFileAction):
        try:
            preview_copy_project_file(workspace, action.source, action.destination)
            ok = True
            message = f"Copy can apply from {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCopyFileObservation(
            kind="check_copy_file",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CopyFileAction):
        try:
            copy_project_file(workspace, action.source, action.destination)
            ok = True
            message = f"Copied {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CopyFileObservation(
            kind="copy_file",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCopyFilesAction):
        try:
            preview_copy_project_files(workspace, [transfer.__dict__ for transfer in action.transfers])
            ok = True
            message = f"Copy can apply to {len(action.transfers)} file(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCopyFilesObservation(
            kind="check_copy_files",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CopyFilesAction):
        try:
            copy_project_files(workspace, [transfer.__dict__ for transfer in action.transfers])
            ok = True
            message = f"Copied {len(action.transfers)} file(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CopyFilesObservation(
            kind="copy_files",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    return None
