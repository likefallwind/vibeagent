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
    DelegateTaskObservation,
    FinishObservation,
    TaskOutputObservation,
    TaskStopObservation,
    ToolErrorObservation,
    UpdatePlanObservation,
    UserInputObservation,
)
from .observation_edit_union_types import EditObservation, FileMutationObservation
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
    EnterWorktreeObservation,
    ExitWorktreeObservation,
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
from .observation_notebook_types import (
    CheckNotebookEditObservation,
    NotebookEditObservation,
    NotebookReadObservation,
)
from .observation_mcp_types import McpCallObservation, McpServersObservation, McpToolsObservation
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
    ProjectAgentsObservation,
    ProjectInstructionsObservation,
    ProjectSkillsObservation,
    ProjectManifestsObservation,
    ProjectOverviewObservation,
    ProjectTodosObservation,
    RelatedTestsObservation,
    RunFocusedTestCommandsObservation,
    RunSuggestedChecksObservation,
    SuggestChecksObservation,
    SkillObservation,
    ToolSearchObservation,
)
from .observation_read_types import (
    CodeOutlineObservation,
    ConfigCheckObservation,
    FileInfoObservation,
    ImageInfoObservation,
    ViewImageObservation,
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
    WebFetchObservation,
    WebSearchObservation,
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
    FileMutationObservation
    | ListFilesObservation
    | ListTreeObservation
    | RepoMapObservation
    | NotebookReadObservation
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
    | ViewImageObservation
    | PythonSymbolsObservation
    | CodeOutlineObservation
    | PythonCheckObservation
    | ConfigCheckObservation
    | McpServersObservation
    | McpToolsObservation
    | McpCallObservation
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
    | EnterWorktreeObservation
    | ExitWorktreeObservation
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
    | ProjectSkillsObservation
    | ProjectAgentsObservation
    | SkillObservation
    | ProjectTodosObservation
    | ProjectOverviewObservation
    | CommandCheckObservation
    | CheckRunCommandsObservation
    | CheckStartCommandObservation
    | PortCheckObservation
    | HttpCheckObservation
    | HttpFetchObservation
    | WebFetchObservation
    | WebSearchObservation
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
    | EditObservation
    | CheckNotebookEditObservation
    | NotebookEditObservation
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
    | UserInputObservation
    | DelegateTaskObservation
    | TaskOutputObservation
    | TaskStopObservation
    | FinishObservation
    | ToolErrorObservation
    | ApprovalDeniedObservation
)
