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
    LspQueryAction,
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
from .action_file_edit_union_types import FileEditAgentAction
from .action_github_types import (
    CheckGitHubPrCommentAction,
    CheckGitHubPrCreateAction,
    GitHubIssueContextAction,
    GitHubPrCiLogsAction,
    GitHubPrCommentAction,
    GitHubPrContextAction,
    GitHubPrCreateAction,
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
    EnterWorktreeAction,
    ExitWorktreeAction,
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
    JsonRemoveAction,
    JsonSetAction,
)
from .action_notebook_types import (
    NotebookReadAction,
)
from .action_mcp_types import (
    McpCallAction,
    McpReadResourceAction,
    McpResourcesAction,
    McpServersAction,
    McpToolsAction,
)
from .action_memory_types import CheckMemoryWriteAction, MemoryListAction, MemoryReadAction, MemoryWriteAction
from .action_process_union_types import ProcessAgentAction
from .action_project_types import (
    CheckFocusedTestCommandsAction,
    CheckSuggestedChecksAction,
    FinalReviewAction,
    FocusedTestCommandsAction,
    ProjectCommandsAction,
    ProjectAgentsAction,
    ProjectInstructionsAction,
    ProjectSkillsAction,
    ProjectManifestsAction,
    ProjectOverviewAction,
    ProjectTodosAction,
    RelatedTestsAction,
    ReviewChangesAction,
    RunFocusedTestCommandsAction,
    RunSuggestedChecksAction,
    SuggestChecksAction,
    SkillAction,
    ToolSearchAction,
)
from .action_read_types import (
    CheckWriteFileAction,
    CheckWriteFilesAction,
    FileInfoAction,
    FindFilesAction,
    GlobAction,
    ImageInfoAction,
    ViewImageAction,
    ListFilesAction,
    ListTreeAction,
    OutputContextsAction,
    OutputDiagnosticsAction,
    ReadFileAction,
    ReadFileContextAction,
    ReadFileContextsAction,
    ReadFileRangesAction,
    ReadFilesAction,
    RepoMapAction,
    SearchAction,
    SearchContextsAction,
    TailFileAction,
    WriteFileAction,
    WriteFilesAction,
)
from .action_session_types import (
    RunSessionVerificationAction,
    SessionAuditAction,
    SessionCommandsAction,
    SessionFailuresAction,
    SessionFilesAction,
    SessionHandoffAction,
    SessionOutputContextsAction,
    SessionOutputDiagnosticsAction,
    SessionPlanAction,
    SessionSearchAction,
    SessionSummaryAction,
    SessionTranscriptAction,
    SessionVerificationAction,
)
from .action_task_types import TaskCreateAction, TaskGetAction, TaskListAction, TaskUpdateAction
from .action_team_types import TeamCreateAction, TeamDeleteAction
from .action_cron_types import CronCreateAction, CronDeleteAction, CronListAction
from .action_workflow_types import AskUserAction, DelegateTaskAction, EnterPlanModeAction, ExitPlanModeAction, FinishAction, ListAgentsAction, SendMessageAction, TaskOutputAction, TaskStopAction, UpdatePlanAction


# Small union of all supported model action types.
AgentAction: TypeAlias = (
    CheckWriteFileAction
    | WriteFileAction
    | CheckWriteFilesAction
    | WriteFilesAction
    | ListFilesAction
    | ListTreeAction
    | RepoMapAction
    | NotebookReadAction
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
    | ViewImageAction
    | PythonSymbolsAction
    | CodeOutlineAction
    | PythonCheckAction
    | ConfigCheckAction
    | LspQueryAction
    | CheckJsonSetAction
    | JsonSetAction
    | CheckJsonRemoveAction
    | JsonRemoveAction
    | CheckJsonPatchAction
    | JsonPatchAction
    | McpServersAction
    | McpToolsAction
    | McpResourcesAction
    | McpReadResourceAction
    | McpCallAction
    | MemoryListAction
    | MemoryReadAction
    | MemoryWriteAction
    | CheckMemoryWriteAction
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
    | EnterWorktreeAction
    | ExitWorktreeAction
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
    | GitHubIssueContextAction
    | CheckGitHubPrCreateAction
    | GitHubPrCreateAction
    | GitHubPrContextAction
    | GitHubPrCiLogsAction
    | CheckGitHubPrCommentAction
    | GitHubPrCommentAction
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
    | ToolSearchAction
    | RelatedTestsAction
    | FocusedTestCommandsAction
    | CheckFocusedTestCommandsAction
    | RunFocusedTestCommandsAction
    | ProjectManifestsAction
    | ProjectInstructionsAction
    | ProjectSkillsAction
    | ProjectAgentsAction
    | SkillAction
    | ProjectTodosAction
    | ProjectOverviewAction
    | ProcessAgentAction
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
    | FileEditAgentAction
    | CronCreateAction
    | CronListAction
    | CronDeleteAction
    | TaskCreateAction
    | TaskGetAction
    | TaskListAction
    | TaskUpdateAction
    | TeamCreateAction
    | TeamDeleteAction
    | UpdatePlanAction
    | EnterPlanModeAction
    | ExitPlanModeAction
    | AskUserAction
    | DelegateTaskAction
    | ListAgentsAction
    | SendMessageAction
    | TaskOutputAction
    | TaskStopAction
    | FinishAction
)
