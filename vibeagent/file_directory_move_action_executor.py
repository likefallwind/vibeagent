from __future__ import annotations

from .action_parsing_helpers import directory_transfer_pairs
from .types import (
    CheckMoveDirectoriesAction,
    CheckMoveDirectoriesObservation,
    CheckMoveDirectoryAction,
    CheckMoveDirectoryObservation,
    MoveDirectoriesAction,
    MoveDirectoriesObservation,
    MoveDirectoryAction,
    MoveDirectoryObservation,
    Observation,
)
from .workspace import (
    RunWorkspace,
    move_project_directories,
    move_project_directory,
    preview_move_project_directories,
    preview_move_project_directory,
)


def execute_directory_move_action(workspace: RunWorkspace, action: object) -> Observation | None:
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

    return None
