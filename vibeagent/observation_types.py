from __future__ import annotations

from typing import TypeAlias

from .observation_checkpoint_types import (
    CheckCheckpointDeleteObservation,
    CheckCheckpointPruneObservation,
    CheckCheckpointRestoreObservation,
    CheckpointCreateObservation,
    CheckpointDeleteObservation,
    CheckpointDiffObservation,
    CheckpointInfo,
    CheckpointListObservation,
    CheckpointPruneObservation,
    CheckpointRestoreObservation,
    CheckpointShowObservation,
    CheckpointStatusObservation,
)
from .observation_code_intel_types import (
    CodeDefinition,
    CodeDefinitionsObservation,
    CodeDependenciesObservation,
    CodeDependenciesResult,
    CodeImportRef,
    CodeReference,
    CodeReferenceContextsObservation,
    CodeReferencesObservation,
    CodeRenameObservation,
    CodeRenamePreviewFile,
    CodeRenamePreviewObservation,
    CodeRenameReplacement,
    PythonCall,
    PythonCallGraphObservation,
    PythonCallsObservation,
    PythonDefinition,
    PythonDefinitionsObservation,
    PythonDependenciesObservation,
    PythonDependenciesResult,
    PythonImportRef,
    PythonReference,
    PythonReferenceContextsObservation,
    PythonReferencesObservation,
    PythonRenameObservation,
    PythonRenamePreviewFile,
    PythonRenamePreviewObservation,
    PythonRenameReplacement,
    ReferenceContextResult,
    RepoMapObservation,
    RepoMapPythonFile,
)
from .observation_common_types import (
    ApprovalDeniedObservation,
    FinishObservation,
    ToolErrorObservation,
    UpdatePlanObservation,
)
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
    CheckWriteFileResult,
    CheckWriteFilesObservation,
    JsonPatchObservation,
    JsonRemoveObservation,
    JsonSetObservation,
    WriteFileObservation,
    WriteFileResult,
    WriteFilesObservation,
)
from .observation_process_types import (
    CheckRunCommandsObservation,
    CheckStopAllProcessesObservation,
    CheckStopProcessObservation,
    CheckWriteProcessObservation,
    CommandCheckObservation,
    CommandResult,
    ListProcessesObservation,
    ProcessInfo,
    ProcessOutputContextsObservation,
    ProcessOutputDiagnosticsObservation,
    ReadProcessObservation,
    RunCommandObservation,
    RunCommandsObservation,
    StartCommandObservation,
    StopAllProcessesObservation,
    StopProcessObservation,
    StoppedProcessInfo,
    WaitProcessObservation,
    WriteProcessObservation,
)
from .observation_project_types import (
    CheckFocusedTestCommandsObservation,
    CheckSuggestedChecksObservation,
    FocusedTestCommand,
    FocusedTestCommandsObservation,
    ProjectCommand,
    ProjectCommandsObservation,
    ProjectInstructionSource,
    ProjectInstructionsObservation,
    ProjectManifest,
    ProjectManifestItem,
    ProjectManifestsObservation,
    ProjectOverviewObservation,
    ProjectTodo,
    ProjectTodosObservation,
    RelatedTestCandidate,
    RelatedTestsObservation,
    RunFocusedTestCommandsObservation,
    RunSuggestedChecksObservation,
    SuggestChecksObservation,
    SuggestedCheck,
)
from .observation_read_types import (
    CodeOutlineObservation,
    CodeOutlineResult,
    ConfigCheckObservation,
    ConfigCheckResult,
    FileInfoObservation,
    FileInfoResult,
    ImageInfoObservation,
    ImageInfoResult,
    ListFilesObservation,
    ListTreeObservation,
    OutputContextResult,
    OutputContextsObservation,
    OutputDiagnostic,
    OutputDiagnosticsObservation,
    PythonCheckObservation,
    PythonCheckResult,
    PythonSymbol,
    PythonSymbolsObservation,
    PythonSymbolsResult,
    ReadFileContextObservation,
    ReadFileContextResult,
    ReadFileContextsObservation,
    ReadFileObservation,
    ReadFileRangeResult,
    ReadFileRangesObservation,
    ReadFileResult,
    ReadFilesObservation,
    TailFileObservation,
)
from .observation_review_types import (
    FinalReviewObservation,
    ReviewChangesObservation,
)
from .observation_runtime_types import (
    CheckStartCommandObservation,
    EnvironmentInfoObservation,
    HttpCheckObservation,
    HttpFetchObservation,
    PortCheckObservation,
    RuntimeToolInfo,
)
from .observation_search_types import (
    FindFilesObservation,
    GlobObservation,
    SearchContextResult,
    SearchContextsObservation,
    SearchObservation,
)
from .observation_session_types import (
    SessionAuditObservation,
    SessionAuditProcess,
    SessionCommandsObservation,
    SessionFailuresObservation,
    SessionFilesObservation,
    SessionHandoffObservation,
    SessionOutputContextsObservation,
    SessionOutputDiagnosticsObservation,
    SessionPlanObservation,
    SessionSearchObservation,
    SessionSummaryObservation,
    SessionTranscriptObservation,
    SessionVerificationObservation,
)
from .observation_git_types import (
    CheckGitCommitObservation,
    CheckGitFetchObservation,
    CheckGitPullObservation,
    CheckGitPushObservation,
    CheckGitRestoreObservation,
    CheckGitStageObservation,
    CheckGitStashApplyObservation,
    CheckGitStashDropObservation,
    CheckGitStashObservation,
    CheckGitSwitchObservation,
    CheckGitUnstageObservation,
    GitBlameObservation,
    GitBranchInfo,
    GitBranchesObservation,
    GitChangeFile,
    GitChangesObservation,
    GitCommitObservation,
    GitConflictMarker,
    GitConflictStatus,
    GitConflictsObservation,
    GitDiffContext,
    GitDiffContextsObservation,
    GitDiffHunk,
    GitDiffHunksObservation,
    GitDiffObservation,
    GitFetchObservation,
    GitInfoObservation,
    GitLogObservation,
    GitPullObservation,
    GitPushObservation,
    GitRemote,
    GitRestoreObservation,
    GitShowObservation,
    GitStageObservation,
    GitStashApplyObservation,
    GitStashDropObservation,
    GitStashEntry,
    GitStashObservation,
    GitStashesObservation,
    GitStatusObservation,
    GitSwitchObservation,
    GitUnstageObservation,
    UntrackedFilePreview,
)


# Unified envelope returned from one agent step.
Observation: TypeAlias = (
    CheckWriteFileObservation
    | WriteFileObservation
    | CheckWriteFilesObservation
    | WriteFilesObservation
    | ListFilesObservation
    | ListTreeObservation
    | RepoMapObservation
    | ReadFileObservation
    | ReadFileContextObservation
    | ReadFileContextsObservation
    | OutputContextsObservation
    | OutputDiagnosticsObservation
    | TailFileObservation
    | ReadFilesObservation
    | ReadFileRangesObservation
    | FileInfoObservation
    | ImageInfoObservation
    | PythonSymbolsObservation
    | CodeOutlineObservation
    | PythonCheckObservation
    | ConfigCheckObservation
    | CheckJsonSetObservation
    | JsonSetObservation
    | CheckJsonRemoveObservation
    | JsonRemoveObservation
    | CheckJsonPatchObservation
    | JsonPatchObservation
    | PythonDependenciesObservation
    | CodeDependenciesObservation
    | CodeReferencesObservation
    | CodeReferenceContextsObservation
    | CodeDefinitionsObservation
    | CodeRenamePreviewObservation
    | CodeRenameObservation
    | PythonDefinitionsObservation
    | PythonCallsObservation
    | PythonCallGraphObservation
    | PythonReferencesObservation
    | PythonReferenceContextsObservation
    | PythonRenamePreviewObservation
    | PythonRenameObservation
    | SearchObservation
    | SearchContextsObservation
    | FindFilesObservation
    | GlobObservation
    | GitStatusObservation
    | GitConflictsObservation
    | GitInfoObservation
    | GitChangesObservation
    | GitBranchesObservation
    | CheckGitFetchObservation
    | GitFetchObservation
    | CheckGitPullObservation
    | GitPullObservation
    | CheckGitPushObservation
    | GitPushObservation
    | CheckGitRestoreObservation
    | GitRestoreObservation
    | GitStashesObservation
    | CheckGitStashObservation
    | GitStashObservation
    | CheckGitStashApplyObservation
    | GitStashApplyObservation
    | CheckGitStashDropObservation
    | GitStashDropObservation
    | CheckGitSwitchObservation
    | GitSwitchObservation
    | CheckGitStageObservation
    | GitStageObservation
    | CheckGitUnstageObservation
    | GitUnstageObservation
    | CheckGitCommitObservation
    | GitCommitObservation
    | ReviewChangesObservation
    | FinalReviewObservation
    | SuggestChecksObservation
    | CheckSuggestedChecksObservation
    | RunSuggestedChecksObservation
    | ProjectCommandsObservation
    | RelatedTestsObservation
    | FocusedTestCommandsObservation
    | CheckFocusedTestCommandsObservation
    | RunFocusedTestCommandsObservation
    | ProjectManifestsObservation
    | ProjectInstructionsObservation
    | ProjectTodosObservation
    | ProjectOverviewObservation
    | CommandCheckObservation
    | CheckRunCommandsObservation
    | CheckStartCommandObservation
    | PortCheckObservation
    | HttpCheckObservation
    | HttpFetchObservation
    | EnvironmentInfoObservation
    | GitDiffObservation
    | GitDiffHunksObservation
    | GitDiffContextsObservation
    | GitLogObservation
    | GitShowObservation
    | GitBlameObservation
    | SessionSummaryObservation
    | SessionPlanObservation
    | SessionTranscriptObservation
    | SessionSearchObservation
    | SessionCommandsObservation
    | SessionOutputContextsObservation
    | SessionOutputDiagnosticsObservation
    | SessionFilesObservation
    | SessionFailuresObservation
    | SessionVerificationObservation
    | SessionAuditObservation
    | SessionHandoffObservation
    | CheckpointCreateObservation
    | CheckpointListObservation
    | CheckpointShowObservation
    | CheckpointDiffObservation
    | CheckpointStatusObservation
    | CheckCheckpointRestoreObservation
    | CheckpointRestoreObservation
    | CheckCheckpointDeleteObservation
    | CheckpointDeleteObservation
    | CheckCheckpointPruneObservation
    | CheckpointPruneObservation
    | CheckEditFileObservation
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
    | RunCommandObservation
    | RunCommandsObservation
    | StartCommandObservation
    | ReadProcessObservation
    | ProcessOutputContextsObservation
    | ProcessOutputDiagnosticsObservation
    | WaitProcessObservation
    | CheckWriteProcessObservation
    | WriteProcessObservation
    | ListProcessesObservation
    | CheckStopAllProcessesObservation
    | CheckStopProcessObservation
    | StopProcessObservation
    | StopAllProcessesObservation
    | UpdatePlanObservation
    | FinishObservation
    | ToolErrorObservation
    | ApprovalDeniedObservation
)

# Status tokens are constrained to keep logger and callers consistent.
