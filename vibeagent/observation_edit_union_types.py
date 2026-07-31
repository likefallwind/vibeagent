from __future__ import annotations

from typing import TypeAlias

from .observation_edit_types import (
    AppendFileObservation,
    CheckAppendFileObservation,
    CheckCopyDirectoriesObservation,
    CheckCopyDirectoryObservation,
    CheckCopyFileObservation,
    CheckCopyFilesObservation,
    CheckCreateDirectoriesObservation,
    CheckCreateDirectoryObservation,
    CheckDeleteEmptyDirectoriesObservation,
    CheckDeleteEmptyDirectoryObservation,
    CheckDeleteFileObservation,
    CheckDeleteFilesObservation,
    CheckEditFileObservation,
    CheckInsertLinesObservation,
    CheckMoveDirectoriesObservation,
    CheckMoveDirectoryObservation,
    CheckMoveFileObservation,
    CheckMoveFilesObservation,
    CheckMultiEditObservation,
    CheckPatchObservation,
    CheckPatchesObservation,
    CheckRegexReplaceObservation,
    CheckReplaceLinesObservation,
    CheckReplacePythonDefinitionObservation,
    CheckSetExecutableObservation,
    CopyDirectoriesObservation,
    CopyDirectoryObservation,
    CopyFileObservation,
    CopyFilesObservation,
    CreateDirectoriesObservation,
    CreateDirectoryObservation,
    DeleteEmptyDirectoriesObservation,
    DeleteEmptyDirectoryObservation,
    DeleteFileObservation,
    DeleteFilesObservation,
    EditFileObservation,
    InsertLinesObservation,
    MoveDirectoriesObservation,
    MoveDirectoryObservation,
    MoveFileObservation,
    MoveFilesObservation,
    MultiEditObservation,
    PatchFileObservation,
    PatchFilesObservation,
    RegexReplaceObservation,
    ReplaceLinesObservation,
    ReplacePythonDefinitionObservation,
    SetExecutableObservation,
)
from .observation_file_mutation_types import (
    CheckJsonPatchObservation,
    CheckJsonRemoveObservation,
    CheckJsonSetObservation,
    CheckWriteFileObservation,
    CheckWriteFilesObservation,
    JsonPatchObservation,
    JsonRemoveObservation,
    JsonSetObservation,
    WriteFileObservation,
    WriteFilesObservation,
)


FileMutationObservation: TypeAlias = (
    CheckWriteFileObservation
    | WriteFileObservation
    | CheckWriteFilesObservation
    | WriteFilesObservation
    | CheckJsonSetObservation
    | JsonSetObservation
    | CheckJsonRemoveObservation
    | JsonRemoveObservation
    | CheckJsonPatchObservation
    | JsonPatchObservation
)


EditObservation: TypeAlias = (
    CheckEditFileObservation
    | EditFileObservation
    | MultiEditObservation
    | CheckMultiEditObservation
    | CheckReplacePythonDefinitionObservation
    | ReplacePythonDefinitionObservation
    | CheckReplaceLinesObservation
    | ReplaceLinesObservation
    | CheckInsertLinesObservation
    | InsertLinesObservation
    | CheckAppendFileObservation
    | AppendFileObservation
    | RegexReplaceObservation
    | CheckRegexReplaceObservation
    | CheckPatchObservation
    | CheckPatchesObservation
    | PatchFileObservation
    | PatchFilesObservation
    | CheckDeleteFileObservation
    | DeleteFileObservation
    | CheckDeleteFilesObservation
    | DeleteFilesObservation
    | CheckMoveFileObservation
    | MoveFileObservation
    | CheckMoveFilesObservation
    | MoveFilesObservation
    | CheckCopyFileObservation
    | CopyFileObservation
    | CheckCopyFilesObservation
    | CopyFilesObservation
    | CheckMoveDirectoryObservation
    | MoveDirectoryObservation
    | CheckMoveDirectoriesObservation
    | MoveDirectoriesObservation
    | CheckCopyDirectoryObservation
    | CopyDirectoryObservation
    | CheckCopyDirectoriesObservation
    | CopyDirectoriesObservation
    | CheckCreateDirectoryObservation
    | CreateDirectoryObservation
    | CheckCreateDirectoriesObservation
    | CreateDirectoriesObservation
    | CheckDeleteEmptyDirectoryObservation
    | DeleteEmptyDirectoryObservation
    | CheckDeleteEmptyDirectoriesObservation
    | DeleteEmptyDirectoriesObservation
    | CheckSetExecutableObservation
    | SetExecutableObservation
)
