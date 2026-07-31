from __future__ import annotations

from typing import TypeAlias

from .action_file_edit_types import (
    AppendFileAction,
    CheckAppendFileAction,
    CheckCopyDirectoriesAction,
    CheckCopyDirectoryAction,
    CheckCopyFileAction,
    CheckCopyFilesAction,
    CheckCreateDirectoriesAction,
    CheckCreateDirectoryAction,
    CheckDeleteEmptyDirectoriesAction,
    CheckDeleteEmptyDirectoryAction,
    CheckDeleteFileAction,
    CheckDeleteFilesAction,
    CheckEditFileAction,
    CheckInsertLinesAction,
    CheckMoveDirectoriesAction,
    CheckMoveDirectoryAction,
    CheckMoveFileAction,
    CheckMoveFilesAction,
    CheckMultiEditAction,
    CheckPatchAction,
    CheckPatchesAction,
    CheckRegexReplaceAction,
    CheckReplaceLinesAction,
    CheckSetExecutableAction,
    CopyDirectoriesAction,
    CopyDirectoryAction,
    CopyFileAction,
    CopyFilesAction,
    CreateDirectoriesAction,
    CreateDirectoryAction,
    DeleteEmptyDirectoriesAction,
    DeleteEmptyDirectoryAction,
    DeleteFileAction,
    DeleteFilesAction,
    EditFileAction,
    InsertLinesAction,
    MoveDirectoriesAction,
    MoveDirectoryAction,
    MoveFileAction,
    MoveFilesAction,
    MultiEditAction,
    PatchFileAction,
    PatchFilesAction,
    RegexReplaceAction,
    ReplaceLinesAction,
    SetExecutableAction,
)
from .action_notebook_types import CheckNotebookEditAction, NotebookEditAction


FileEditAgentAction: TypeAlias = (
    CheckEditFileAction
    | EditFileAction
    | CheckNotebookEditAction
    | NotebookEditAction
    | MultiEditAction
    | CheckMultiEditAction
    | CheckReplaceLinesAction
    | ReplaceLinesAction
    | CheckInsertLinesAction
    | InsertLinesAction
    | CheckAppendFileAction
    | AppendFileAction
    | RegexReplaceAction
    | CheckRegexReplaceAction
    | CheckPatchAction
    | CheckPatchesAction
    | PatchFileAction
    | PatchFilesAction
    | CheckDeleteFileAction
    | DeleteFileAction
    | CheckDeleteFilesAction
    | DeleteFilesAction
    | CheckMoveFileAction
    | MoveFileAction
    | CheckMoveFilesAction
    | MoveFilesAction
    | CheckCopyFileAction
    | CopyFileAction
    | CheckCopyFilesAction
    | CopyFilesAction
    | CheckMoveDirectoryAction
    | MoveDirectoryAction
    | CheckMoveDirectoriesAction
    | MoveDirectoriesAction
    | CheckCopyDirectoryAction
    | CopyDirectoryAction
    | CheckCopyDirectoriesAction
    | CopyDirectoriesAction
    | CheckCreateDirectoryAction
    | CreateDirectoryAction
    | CheckCreateDirectoriesAction
    | CreateDirectoriesAction
    | CheckDeleteEmptyDirectoryAction
    | DeleteEmptyDirectoryAction
    | CheckDeleteEmptyDirectoriesAction
    | DeleteEmptyDirectoriesAction
    | CheckSetExecutableAction
    | SetExecutableAction
)
