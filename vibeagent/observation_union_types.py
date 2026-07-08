from __future__ import annotations

from typing import TypeAlias

from .observation_checkpoint_types import (
    CheckCheckpointDeleteObservation,
    CheckCheckpointPruneObservation,
    CheckCheckpointRestoreObservation,
    CheckpointCreateObservation,
    CheckpointDeleteObservation,
    CheckpointDiffObservation,
    CheckpointListObservation,
    CheckpointPruneObservation,
    CheckpointRestoreObservation,
    CheckpointShowObservation,
    CheckpointStatusObservation,
)
from .observation_code_intel_types import (
    CodeDefinitionsObservation,
    CodeDependenciesObservation,
    CodeReferenceContextsObservation,
    CodeReferencesObservation,
    CodeRenameObservation,
    CodeRenamePreviewObservation,
    PythonCallGraphObservation,
    PythonCallsObservation,
    PythonDefinitionsObservation,
    PythonDependenciesObservation,
    PythonReferenceContextsObservation,
    PythonReferencesObservation,
    PythonRenameObservation,
    PythonRenamePreviewObservation,
    RepoMapObservation,
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
    CheckWriteFilesObservation,
    JsonPatchObservation,
    JsonRemoveObservation,
    JsonSetObservation,
    WriteFileObservation,
    WriteFilesObservation,
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
    GitBranchesObservation,
    GitChangesObservation,
    GitCommitObservation,
    GitConflictsObservation,
    GitDiffContextsObservation,
    GitDiffHunksObservation,
    GitDiffObservation,
    GitFetchObservation,
    GitInfoObservation,
    GitLogObservation,
    GitPullObservation,
    GitPushObservation,
    GitRestoreObservation,
    GitShowObservation,
    GitStageObservation,
    GitStashApplyObservation,
    GitStashDropObservation,
    GitStashesObservation,
    GitStashObservation,
    GitStatusObservation,
    GitSwitchObservation,
    GitUnstageObservation,
)
from .observation_process_types import (
    CheckRunCommandsObservation,
    CheckStopAllProcessesObservation,
    CheckStopProcessObservation,
    CheckWriteProcessObservation,
    CommandCheckObservation,
    ListProcessesObservation,
    ProcessOutputContextsObservation,
    ProcessOutputDiagnosticsObservation,
    ReadProcessObservation,
    RunCommandObservation,
    RunCommandsObservation,
    StartCommandObservation,
    StopAllProcessesObservation,
    StopProcessObservation,
    WaitProcessObservation,
    WriteProcessObservation,
)
from .observation_project_types import (
    CheckFocusedTestCommandsObservation,
    CheckSuggestedChecksObservation,
    FocusedTestCommandsObservation,
    ProjectCommandsObservation,
    ProjectInstructionsObservation,
    ProjectManifestsObservation,
    ProjectOverviewObservation,
    ProjectTodosObservation,
    RelatedTestsObservation,
    RunFocusedTestCommandsObservation,
    RunSuggestedChecksObservation,
    SuggestChecksObservation,
    ToolSearchObservation,
)
from .observation_read_types import (
    CodeOutlineObservation,
    ConfigCheckObservation,
    FileInfoObservation,
    ImageInfoObservation,
    ListFilesObservation,
    ListTreeObservation,
    OutputContextsObservation,
    OutputDiagnosticsObservation,
    PythonCheckObservation,
    PythonSymbolsObservation,
    ReadFileContextObservation,
    ReadFileContextsObservation,
    ReadFileObservation,
    ReadFileRangesObservation,
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
)
from .observation_search_types import (
    FindFilesObservation,
    GlobObservation,
    SearchContextsObservation,
    SearchObservation,
)
from .observation_session_types import (
    RunSessionVerificationObservation,
    SessionAuditObservation,
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
    | ToolSearchObservation
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
    | RunSessionVerificationObservation
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
