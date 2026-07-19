from __future__ import annotations

from .types import (
    CheckWriteFileAction,
    CheckWriteFileObservation,
    CheckWriteFileResult,
    CheckWriteFilesAction,
    CheckWriteFilesObservation,
    Observation,
    WriteFileAction,
    WriteFileObservation,
    WriteFileResult,
    WriteFilesAction,
    WriteFilesObservation,
)
from .workspace import RunWorkspace, preview_write_run_file, preview_write_run_files, write_run_file, write_run_files


def execute_write_file_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, CheckWriteFileAction):
        try:
            _, diff = preview_write_run_file(workspace, action.path, action.content)
            return CheckWriteFileObservation(
                kind="check_write_file",
                path=action.path,
                ok=True,
                message=f"Write can apply to {action.path}.",
                diff=diff,
            )
        except ValueError as error:
            return CheckWriteFileObservation(
                kind="check_write_file",
                path=action.path,
                ok=False,
                message=str(error),
                diff="",
            )

    if isinstance(action, WriteFileAction):
        try:
            write_run_file(workspace, action.path, action.content)
            return WriteFileObservation(kind="write_file", path=action.path, ok=True, message=f"Wrote {action.path}")
        except ValueError as error:
            return WriteFileObservation(kind="write_file", path=action.path, ok=False, message=str(error))

    if isinstance(action, CheckWriteFilesAction):
        try:
            previews = preview_write_run_files(workspace, [(file.path, file.content) for file in action.files])
            files = [
                CheckWriteFileResult(path=relative_path, ok=True, message=f"Write can apply to {relative_path}.", diff=diff)
                for relative_path, _target, diff in previews
            ]
            return CheckWriteFilesObservation(
                kind="check_write_files",
                files=files,
                ok=True,
                message=f"Write can apply to {len(files)} file(s).",
            )
        except ValueError as error:
            files = [
                CheckWriteFileResult(path=file.path, ok=False, message=str(error), diff="")
                for file in action.files
            ]
            return CheckWriteFilesObservation(
                kind="check_write_files",
                files=files,
                ok=False,
                message=str(error),
            )

    if isinstance(action, WriteFilesAction):
        try:
            write_run_files(workspace, [(file.path, file.content) for file in action.files])
            files = [WriteFileResult(path=file.path, ok=True, message=f"Wrote {file.path}") for file in action.files]
            return WriteFilesObservation(
                kind="write_files",
                files=files,
                ok=True,
                message=f"Wrote {len(files)} file(s).",
            )
        except ValueError as error:
            files = [WriteFileResult(path=file.path, ok=False, message=str(error)) for file in action.files]
            return WriteFilesObservation(
                kind="write_files",
                files=files,
                ok=False,
                message=str(error),
            )

    return None
