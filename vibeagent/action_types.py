from __future__ import annotations

from typing import TypeAlias

from .action_checkpoint_types import (
    CheckCheckpointDeleteAction,
    CheckCheckpointPruneAction,
    CheckCheckpointRestoreAction,
    CheckpointCreateAction,
    CheckpointDeleteAction,
    CheckpointDiffAction,
    CheckpointListAction,
    CheckpointPruneAction,
    CheckpointRestoreAction,
    CheckpointShowAction,
    CheckpointStatusAction,
)
from .action_code_intel_types import (
    CheckReplacePythonDefinitionAction,
    CodeDefinitionsAction,
    CodeDependenciesAction,
    CodeOutlineAction,
    CodeReferenceContextsAction,
    CodeReferencesAction,
    CodeRenameAction,
    CodeRenamePreviewAction,
    ConfigCheckAction,
    PythonCallGraphAction,
    PythonCallsAction,
    PythonCheckAction,
    PythonDefinitionsAction,
    PythonDependenciesAction,
    PythonReferenceContextsAction,
    PythonReferencesAction,
    PythonRenameAction,
    PythonRenamePreviewAction,
    PythonSymbolsAction,
    ReplacePythonDefinitionAction,
)
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
    DirectoryTransfer,
    EditFileAction,
    EditOperation,
    InsertLinesAction,
    MoveDirectoriesAction,
    MoveDirectoryAction,
    MoveFileAction,
    MoveFileTransfer,
    MoveFilesAction,
    MultiEditAction,
    PatchFileAction,
    PatchFilesAction,
    RegexReplaceAction,
    ReplaceLinesAction,
    SetExecutableAction,
)
from .action_git_types import (
    CheckGitCommitAction,
    CheckGitFetchAction,
    CheckGitPullAction,
    CheckGitPushAction,
    CheckGitRestoreAction,
    CheckGitStageAction,
    CheckGitStashAction,
    CheckGitStashApplyAction,
    CheckGitStashDropAction,
    CheckGitSwitchAction,
    CheckGitUnstageAction,
    GitBlameAction,
    GitBranchesAction,
    GitChangesAction,
    GitCommitAction,
    GitConflictsAction,
    GitDiffAction,
    GitDiffContextsAction,
    GitDiffHunksAction,
    GitFetchAction,
    GitInfoAction,
    GitLogAction,
    GitPullAction,
    GitPushAction,
    GitRestoreAction,
    GitShowAction,
    GitStageAction,
    GitStashAction,
    GitStashApplyAction,
    GitStashDropAction,
    GitStashesAction,
    GitStatusAction,
    GitSwitchAction,
    GitUnstageAction,
)
from .action_json_types import (
    CheckJsonPatchAction,
    CheckJsonRemoveAction,
    CheckJsonSetAction,
    JsonPatchAction,
    JsonPatchOperation,
    JsonRemoveAction,
    JsonSetAction,
)
from .action_process_types import (
    CheckRunCommandsAction,
    CheckStartCommandAction,
    CheckStopAllProcessesAction,
    CheckStopProcessAction,
    CheckWriteProcessAction,
    CommandCheckAction,
    EnvironmentInfoAction,
    HttpCheckAction,
    HttpFetchAction,
    ListProcessesAction,
    PortCheckAction,
    ProcessOutputContextsAction,
    ProcessOutputDiagnosticsAction,
    ReadProcessAction,
    RunCommandAction,
    RunCommandItem,
    RunCommandsAction,
    StartCommandAction,
    StopAllProcessesAction,
    StopProcessAction,
    WaitProcessAction,
    WriteProcessAction,
)
from .action_project_types import (
    CheckFocusedTestCommandsAction,
    CheckSuggestedChecksAction,
    FinalReviewAction,
    FocusedTestCommandsAction,
    ProjectCommandsAction,
    ProjectInstructionsAction,
    ProjectManifestsAction,
    ProjectOverviewAction,
    ProjectTodosAction,
    RelatedTestsAction,
    ReviewChangesAction,
    RunFocusedTestCommandsAction,
    RunSuggestedChecksAction,
    SuggestChecksAction,
)
from .action_read_types import (
    CheckWriteFileAction,
    CheckWriteFilesAction,
    FileInfoAction,
    FindFilesAction,
    GlobAction,
    ImageInfoAction,
    ListFilesAction,
    ListTreeAction,
    OutputContextsAction,
    OutputDiagnosticsAction,
    ReadFileAction,
    ReadFileContextAction,
    ReadFileContextItem,
    ReadFileContextsAction,
    ReadFileRangeItem,
    ReadFileRangesAction,
    ReadFilesAction,
    RepoMapAction,
    SearchAction,
    SearchContextsAction,
    TailFileAction,
    WriteFileAction,
    WriteFileItem,
    WriteFilesAction,
)
from .action_session_types import (
    SessionAuditAction,
    SessionCommandsAction,
    SessionFailuresAction,
    SessionFilesAction,
    SessionHandoffAction,
    SessionOutputContextsAction,
    SessionOutputDiagnosticsAction,
    SessionPlanAction,
    RunSessionVerificationAction,
    SessionSearchAction,
    SessionSummaryAction,
    SessionTranscriptAction,
    SessionVerificationAction,
)
from .action_workflow_types import FinishAction, PlanItem, PlanItemStatus, UpdatePlanAction


# Small union of all supported model action types.
AgentAction: TypeAlias = (
    CheckWriteFileAction
    | WriteFileAction
    | CheckWriteFilesAction
    | WriteFilesAction
    | ListFilesAction
    | ListTreeAction
    | RepoMapAction
    | ReadFileAction
    | ReadFileContextAction
    | ReadFileContextsAction
    | OutputContextsAction
    | OutputDiagnosticsAction
    | TailFileAction
    | ReadFilesAction
    | ReadFileRangesAction
    | FileInfoAction
    | ImageInfoAction
    | PythonSymbolsAction
    | CodeOutlineAction
    | PythonCheckAction
    | ConfigCheckAction
    | CheckJsonSetAction
    | JsonSetAction
    | CheckJsonRemoveAction
    | JsonRemoveAction
    | CheckJsonPatchAction
    | JsonPatchAction
    | PythonDependenciesAction
    | CodeDependenciesAction
    | CodeReferencesAction
    | CodeReferenceContextsAction
    | CodeDefinitionsAction
    | CodeRenamePreviewAction
    | CodeRenameAction
    | PythonDefinitionsAction
    | CheckReplacePythonDefinitionAction
    | ReplacePythonDefinitionAction
    | PythonCallsAction
    | PythonCallGraphAction
    | PythonReferencesAction
    | PythonReferenceContextsAction
    | PythonRenamePreviewAction
    | PythonRenameAction
    | SearchAction
    | SearchContextsAction
    | FindFilesAction
    | GlobAction
    | GitStatusAction
    | GitConflictsAction
    | GitInfoAction
    | GitChangesAction
    | GitBranchesAction
    | CheckGitFetchAction
    | GitFetchAction
    | CheckGitPullAction
    | GitPullAction
    | CheckGitPushAction
    | GitPushAction
    | CheckGitRestoreAction
    | GitRestoreAction
    | GitStashesAction
    | CheckGitStashAction
    | GitStashAction
    | CheckGitStashApplyAction
    | GitStashApplyAction
    | CheckGitStashDropAction
    | GitStashDropAction
    | CheckGitSwitchAction
    | GitSwitchAction
    | CheckGitStageAction
    | GitStageAction
    | CheckGitUnstageAction
    | GitUnstageAction
    | CheckGitCommitAction
    | GitCommitAction
    | ReviewChangesAction
    | FinalReviewAction
    | SuggestChecksAction
    | CheckSuggestedChecksAction
    | RunSuggestedChecksAction
    | ProjectCommandsAction
    | RelatedTestsAction
    | FocusedTestCommandsAction
    | CheckFocusedTestCommandsAction
    | RunFocusedTestCommandsAction
    | ProjectManifestsAction
    | ProjectInstructionsAction
    | ProjectTodosAction
    | ProjectOverviewAction
    | CommandCheckAction
    | CheckRunCommandsAction
    | CheckStartCommandAction
    | PortCheckAction
    | HttpCheckAction
    | HttpFetchAction
    | EnvironmentInfoAction
    | GitDiffAction
    | GitDiffHunksAction
    | GitDiffContextsAction
    | GitLogAction
    | GitShowAction
    | GitBlameAction
    | SessionSummaryAction
    | SessionPlanAction
    | SessionTranscriptAction
    | SessionSearchAction
    | SessionCommandsAction
    | SessionOutputContextsAction
    | SessionOutputDiagnosticsAction
    | SessionFilesAction
    | SessionFailuresAction
    | SessionVerificationAction
    | RunSessionVerificationAction
    | SessionAuditAction
    | SessionHandoffAction
    | CheckpointCreateAction
    | CheckpointListAction
    | CheckpointShowAction
    | CheckpointDiffAction
    | CheckpointStatusAction
    | CheckCheckpointRestoreAction
    | CheckpointRestoreAction
    | CheckCheckpointDeleteAction
    | CheckpointDeleteAction
    | CheckCheckpointPruneAction
    | CheckpointPruneAction
    | CheckEditFileAction
    | EditFileAction
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
    | RunCommandAction
    | RunCommandsAction
    | StartCommandAction
    | ReadProcessAction
    | ProcessOutputContextsAction
    | ProcessOutputDiagnosticsAction
    | WaitProcessAction
    | CheckWriteProcessAction
    | WriteProcessAction
    | ListProcessesAction
    | CheckStopAllProcessesAction
    | CheckStopProcessAction
    | StopProcessAction
    | StopAllProcessesAction
    | UpdatePlanAction
    | FinishAction
)
