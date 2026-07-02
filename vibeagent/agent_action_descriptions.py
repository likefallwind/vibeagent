from __future__ import annotations

from .agent_observation_utils import summarize
from . import types as t


def build_step_label(action: object) -> str:
    if isinstance(action, t.CheckWriteFileAction):
        return f"Check write {action.path}"
    if isinstance(action, t.WriteFileAction):
        return f"Write {action.path}"
    if isinstance(action, t.CheckWriteFilesAction):
        return f"Check write {len(action.files)} files"
    if isinstance(action, t.WriteFilesAction):
        return f"Write {len(action.files)} files"
    if isinstance(action, t.CheckEditFileAction):
        return f"Check edit {action.path}"
    if isinstance(action, t.EditFileAction):
        return f"Edit {action.path}"
    if isinstance(action, t.CheckMultiEditAction):
        return f"Check multi-edit {action.path}"
    if isinstance(action, t.MultiEditAction):
        return f"Multi-edit {action.path}"
    if isinstance(action, t.CheckReplaceLinesAction):
        return f"Check replace lines {action.start_line}-{action.end_line} in {action.path}"
    if isinstance(action, t.ReplaceLinesAction):
        return f"Replace lines {action.start_line}-{action.end_line} in {action.path}"
    if isinstance(action, t.CheckInsertLinesAction):
        return f"Check insert lines before {action.line} in {action.path}"
    if isinstance(action, t.InsertLinesAction):
        return f"Insert lines before {action.line} in {action.path}"
    if isinstance(action, t.CheckAppendFileAction):
        return f"Check append to {action.path}"
    if isinstance(action, t.AppendFileAction):
        return f"Append to {action.path}"
    if isinstance(action, t.RegexReplaceAction):
        return f"Regex replace in {action.path}"
    if isinstance(action, t.CheckRegexReplaceAction):
        return f"Check regex replace in {action.path}"
    if isinstance(action, t.CheckPatchAction):
        return f"Check patch {action.path}"
    if isinstance(action, t.CheckPatchesAction):
        return "Check patches"
    if isinstance(action, t.PatchFileAction):
        return f"Patch {action.path}"
    if isinstance(action, t.PatchFilesAction):
        return "Patch files"
    if isinstance(action, t.CheckDeleteFileAction):
        return f"Check delete {action.path}"
    if isinstance(action, t.DeleteFileAction):
        return f"Delete {action.path}"
    if isinstance(action, t.CheckDeleteFilesAction):
        return f"Check delete {len(action.paths)} file(s)"
    if isinstance(action, t.DeleteFilesAction):
        return f"Delete {len(action.paths)} file(s)"
    if isinstance(action, t.CheckMoveFileAction):
        return f"Check move {action.source}"
    if isinstance(action, t.MoveFileAction):
        return f"Move {action.source}"
    if isinstance(action, t.CheckMoveFilesAction):
        return f"Check move {len(action.transfers)} file(s)"
    if isinstance(action, t.MoveFilesAction):
        return f"Move {len(action.transfers)} file(s)"
    if isinstance(action, t.CheckCopyFileAction):
        return f"Check copy {action.source}"
    if isinstance(action, t.CopyFileAction):
        return f"Copy {action.source}"
    if isinstance(action, t.CheckCopyFilesAction):
        return f"Check copy {len(action.transfers)} file(s)"
    if isinstance(action, t.CopyFilesAction):
        return f"Copy {len(action.transfers)} file(s)"
    if isinstance(action, t.CheckMoveDirectoryAction):
        return f"Check move directory {action.source}"
    if isinstance(action, t.MoveDirectoryAction):
        return f"Move directory {action.source}"
    if isinstance(action, t.CheckMoveDirectoriesAction):
        return f"Check move {len(action.transfers)} directories"
    if isinstance(action, t.MoveDirectoriesAction):
        return f"Move {len(action.transfers)} directories"
    if isinstance(action, t.CheckCopyDirectoryAction):
        return f"Check copy directory {action.source}"
    if isinstance(action, t.CopyDirectoryAction):
        return f"Copy directory {action.source}"
    if isinstance(action, t.CheckCopyDirectoriesAction):
        return f"Check copy {len(action.transfers)} directories"
    if isinstance(action, t.CopyDirectoriesAction):
        return f"Copy {len(action.transfers)} directories"
    if isinstance(action, t.CheckCreateDirectoryAction):
        return f"Check create directory {action.path}"
    if isinstance(action, t.CreateDirectoryAction):
        return f"Create directory {action.path}"
    if isinstance(action, t.CheckCreateDirectoriesAction):
        return f"Check create {len(action.paths)} directories"
    if isinstance(action, t.CreateDirectoriesAction):
        return f"Create {len(action.paths)} directories"
    if isinstance(action, t.CheckDeleteEmptyDirectoryAction):
        return f"Check delete empty directory {action.path}"
    if isinstance(action, t.DeleteEmptyDirectoryAction):
        return f"Delete empty directory {action.path}"
    if isinstance(action, t.CheckDeleteEmptyDirectoriesAction):
        return f"Check delete {len(action.paths)} empty directories"
    if isinstance(action, t.DeleteEmptyDirectoriesAction):
        return f"Delete {len(action.paths)} empty directories"
    if isinstance(action, t.CheckSetExecutableAction):
        state = "executable" if action.executable else "not executable"
        return f"Check set {action.path} {state}"
    if isinstance(action, t.SetExecutableAction):
        state = "executable" if action.executable else "not executable"
        return f"Set {action.path} {state}"
    if isinstance(action, t.RunCommandAction):
        suffix = f" in {action.cwd}" if action.cwd else ""
        return f"Run {summarize(action.command, 80)}{suffix}"
    if isinstance(action, t.StartCommandAction):
        suffix = f" in {action.cwd}" if action.cwd else ""
        return f"Start {summarize(action.command, 80)}{suffix}"
    if isinstance(action, t.ReadProcessAction):
        return f"Read process {action.process_id}"
    if isinstance(action, t.ListProcessesAction):
        return "List background processes"
    if isinstance(action, t.CheckStopAllProcessesAction):
        return "Check stop all background processes"
    if isinstance(action, t.StopProcessAction):
        return f"Stop process {action.process_id}"
    if isinstance(action, t.StopAllProcessesAction):
        return "Stop all background processes"
    if isinstance(action, t.UpdatePlanAction):
        return "Update plan"
    if isinstance(action, t.RepoMapAction):
        return f"Map repo {action.path or '.'}"
    if isinstance(action, t.ReadFileAction):
        return f"Read {action.path}"
    if isinstance(action, t.ReadFileContextAction):
        return f"Read {action.path}:{action.line}"
    if isinstance(action, t.ReadFileContextsAction):
        return f"Read {len(action.contexts)} file contexts"
    if isinstance(action, t.OutputContextsAction):
        return f"Read output contexts from {action.max_contexts} reference(s)"
    if isinstance(action, t.SessionOutputContextsAction):
        return f"Read session output contexts for {action.run_id or 'current session'}"
    if isinstance(action, t.SessionOutputDiagnosticsAction):
        return f"Read session output diagnostics for {action.run_id or 'current session'}"
    if isinstance(action, t.TailFileAction):
        return f"Tail {action.path}"
    if isinstance(action, t.ReadFilesAction):
        return f"Read {len(action.paths)} files"
    if isinstance(action, t.ReadFileRangesAction):
        return f"Read {len(action.ranges)} file ranges"
    if isinstance(action, t.FileInfoAction):
        return f"Inspect {len(action.paths)} paths"
    if isinstance(action, t.ImageInfoAction):
        return f"Inspect {len(action.paths)} images"
    if isinstance(action, t.PythonSymbolsAction):
        return f"Read Python symbols for {len(action.paths)} files"
    if isinstance(action, t.CodeOutlineAction):
        return f"Read code outlines for {len(action.paths)} files"
    if isinstance(action, t.PythonCheckAction):
        return f"Check Python {action.path or '.'}"
    if isinstance(action, t.ConfigCheckAction):
        return f"Check config {action.path or '.'}"
    if isinstance(action, t.CheckJsonSetAction):
        return f"Check JSON set {action.path} {action.pointer}"
    if isinstance(action, t.JsonSetAction):
        return f"Set JSON {action.path} {action.pointer}"
    if isinstance(action, t.CheckJsonRemoveAction):
        return f"Check JSON remove {action.path} {action.pointer}"
    if isinstance(action, t.JsonRemoveAction):
        return f"Remove JSON {action.path} {action.pointer}"
    if isinstance(action, t.CheckJsonPatchAction):
        return f"Check JSON patch {action.path}"
    if isinstance(action, t.JsonPatchAction):
        return f"Patch JSON {action.path}"
    if isinstance(action, t.PythonDependenciesAction):
        return f"Read Python dependencies {action.path or '.'}"
    if isinstance(action, t.CodeDependenciesAction):
        return f"Read code dependencies {action.path or '.'}"
    if isinstance(action, t.CodeReferencesAction):
        return f"Find code references {action.symbol}"
    if isinstance(action, t.CodeReferenceContextsAction):
        return f"Read code reference contexts {action.symbol}"
    if isinstance(action, t.CodeDefinitionsAction):
        return f"Find code definitions {action.symbol}"
    if isinstance(action, t.CodeRenamePreviewAction):
        return f"Preview code rename {action.symbol} to {action.new_name}"
    if isinstance(action, t.CodeRenameAction):
        return f"Rename code symbol {action.symbol} to {action.new_name}"
    if isinstance(action, t.PythonDefinitionsAction):
        return f"Read Python definitions {action.symbol}"
    if isinstance(action, t.CheckReplacePythonDefinitionAction):
        return f"Check replace Python definition {action.symbol}"
    if isinstance(action, t.ReplacePythonDefinitionAction):
        return f"Replace Python definition {action.symbol}"
    if isinstance(action, t.PythonCallsAction):
        return f"Read Python calls {action.symbol}"
    if isinstance(action, t.PythonCallGraphAction):
        return f"Read Python call graph {action.path or '.'}"
    if isinstance(action, t.PythonReferencesAction):
        return f"Find Python references {action.symbol}"
    if isinstance(action, t.PythonReferenceContextsAction):
        return f"Read Python reference contexts {action.symbol}"
    if isinstance(action, t.PythonRenamePreviewAction):
        return f"Preview Python rename {action.symbol} to {action.new_name}"
    if isinstance(action, t.PythonRenameAction):
        return f"Rename Python symbol {action.symbol} to {action.new_name}"
    if isinstance(action, t.SearchAction):
        return f"Search {summarize(action.query, 80)}"
    if isinstance(action, t.SearchContextsAction):
        return f"Search contexts {summarize(action.query, 80)} in {action.path or '.'}"
    if isinstance(action, t.GlobAction):
        return f"Find files {summarize(action.pattern, 80)}"
    if isinstance(action, t.ListTreeAction):
        return f"List tree {action.path or '.'}"
    if isinstance(action, t.GitStatusAction):
        return "Read git status"
    if isinstance(action, t.GitConflictsAction):
        return f"Scan git conflicts {action.path or '.'}"
    if isinstance(action, t.GitDiffContextsAction):
        return f"Read git diff contexts {action.path or '.'}"
    if isinstance(action, t.GitInfoAction):
        return "Read git info"
    if isinstance(action, t.GitChangesAction):
        return "Read git changes"
    if isinstance(action, t.GitBranchesAction):
        return "Read git branches"
    if isinstance(action, t.CheckGitFetchAction):
        return f"Check git fetch {action.remote or 'default remote'}"
    if isinstance(action, t.GitFetchAction):
        return f"Fetch git remote {action.remote or 'default remote'}"
    if isinstance(action, t.CheckGitPullAction):
        return "Check git pull"
    if isinstance(action, t.GitPullAction):
        return "Pull git upstream"
    if isinstance(action, t.CheckGitPushAction):
        return "Check git push"
    if isinstance(action, t.GitPushAction):
        return "Push git upstream"
    if isinstance(action, t.CheckGitRestoreAction):
        return f"Check restore {len(action.paths)} git path(s)"
    if isinstance(action, t.GitRestoreAction):
        return f"Restore {len(action.paths)} git path(s)"
    if isinstance(action, t.GitStashesAction):
        return "Read git stashes"
    if isinstance(action, t.CheckGitStashAction):
        return "Check git stash"
    if isinstance(action, t.GitStashAction):
        return "Stash git changes"
    if isinstance(action, t.CheckGitStashApplyAction):
        return f"Check apply {action.stash_ref}"
    if isinstance(action, t.GitStashApplyAction):
        return f"Apply {action.stash_ref}"
    if isinstance(action, t.CheckGitStashDropAction):
        return f"Check drop {action.stash_ref}"
    if isinstance(action, t.GitStashDropAction):
        return f"Drop {action.stash_ref}"
    if isinstance(action, t.CheckGitSwitchAction):
        return f"Check git switch {action.branch}"
    if isinstance(action, t.GitSwitchAction):
        return f"Switch git branch {action.branch}"
    if isinstance(action, t.CheckGitStageAction):
        return f"Check stage {len(action.paths)} git path(s)"
    if isinstance(action, t.GitStageAction):
        return f"Stage {len(action.paths)} git path(s)"
    if isinstance(action, t.CheckGitUnstageAction):
        return f"Check unstage {len(action.paths)} git path(s)"
    if isinstance(action, t.GitUnstageAction):
        return f"Unstage {len(action.paths)} git path(s)"
    if isinstance(action, t.CheckGitCommitAction):
        return "Check commit staged changes"
    if isinstance(action, t.GitCommitAction):
        return "Commit staged changes"
    if isinstance(action, t.ReviewChangesAction):
        return "Review changes"
    if isinstance(action, t.FinalReviewAction):
        return "Final review"
    if isinstance(action, t.SuggestChecksAction):
        return "Suggest checks"
    if isinstance(action, t.ProjectOverviewAction):
        return "Read project overview"
    if isinstance(action, t.CommandCheckAction):
        return f"Check command {summarize(action.command, 80)}"
    if isinstance(action, t.CheckRunCommandsAction):
        return f"Check {len(action.commands)} commands"
    if isinstance(action, t.CheckStartCommandAction):
        return f"Check start command {summarize(action.command, 80)}"
    if isinstance(action, t.PortCheckAction):
        return f"Check port {action.host}:{action.port}"
    if isinstance(action, t.HttpCheckAction):
        return f"Check HTTP {summarize(action.url, 80)}"
    if isinstance(action, t.HttpFetchAction):
        return f"Fetch HTTP {summarize(action.url, 80)}"
    if isinstance(action, t.CheckStopProcessAction):
        return f"Check stop process {action.process_id}"
    if isinstance(action, t.CheckStopAllProcessesAction):
        return "Check stop all background processes"
    if isinstance(action, t.WaitProcessAction):
        return f"Wait for process {action.process_id}"
    if isinstance(action, t.CheckWriteProcessAction):
        return f"Check process input {action.process_id}"
    if isinstance(action, t.WriteProcessAction):
        return f"Write process input {action.process_id}"
    if isinstance(action, t.EnvironmentInfoAction):
        return "Read environment info"
    if isinstance(action, t.GitDiffAction):
        return f"Read git diff {action.path or '.'}"
    if isinstance(action, t.GitLogAction):
        return f"Read git log {action.path or '.'}"
    if isinstance(action, t.GitShowAction):
        return f"Read git show {action.rev}"
    if isinstance(action, t.GitBlameAction):
        return f"Read git blame {action.path}"
    if isinstance(action, t.SessionSummaryAction):
        return f"Read session summary {action.run_id or 'current'}"
    if isinstance(action, t.SessionPlanAction):
        return f"Read session plan {action.run_id or 'current'}"
    if isinstance(action, t.SessionTranscriptAction):
        return f"Read session transcript {action.run_id or 'current'}"
    if isinstance(action, t.SessionSearchAction):
        return f"Search session {action.run_id or 'current'}"
    if isinstance(action, t.SessionCommandsAction):
        return f"Read session commands {action.run_id or 'current'}"
    if isinstance(action, t.SessionFilesAction):
        return f"Read session files {action.run_id or 'current'}"
    if isinstance(action, t.SessionFailuresAction):
        return f"Read session failures {action.run_id or 'current'}"
    if isinstance(action, t.SessionVerificationAction):
        return f"Read session verification {action.run_id or 'current'}"
    if isinstance(action, t.SessionAuditAction):
        return f"Read session audit {action.run_id or 'current'}"
    if isinstance(action, t.SessionHandoffAction):
        return f"Read session handoff {action.run_id or 'current'}"
    if isinstance(action, t.CheckpointCreateAction):
        return f"Create checkpoint {action.label or ''}".strip()
    if isinstance(action, t.CheckpointListAction):
        return "List checkpoints"
    if isinstance(action, t.CheckpointShowAction):
        return f"Show checkpoint {action.checkpoint_id}"
    if isinstance(action, t.CheckpointDiffAction):
        return f"Read checkpoint diff {action.checkpoint_id}"
    if isinstance(action, t.CheckpointStatusAction):
        return f"Check checkpoint status {action.checkpoint_id}"
    if isinstance(action, t.CheckCheckpointRestoreAction):
        return f"Check checkpoint restore {action.checkpoint_id}"
    if isinstance(action, t.CheckpointRestoreAction):
        return f"Restore checkpoint {action.checkpoint_id}"
    if isinstance(action, t.CheckpointDeleteAction):
        return f"Delete checkpoint {action.checkpoint_id}"
    if isinstance(action, t.CheckCheckpointPruneAction):
        return f"Check checkpoint prune keep {action.keep_last}"
    if isinstance(action, t.CheckpointPruneAction):
        return f"Prune checkpoints keep {action.keep_last}"
    if isinstance(action, t.ListFilesAction):
        return f"List files {action.path or '.'}"
    if getattr(action, "type", None) == "list_files":
        return f"List files {getattr(action, 'path', None) or '.'}"
    if isinstance(action, t.FinishAction):
        return "Finish task"
    return str(getattr(action, "type", "Unknown action"))


def build_action_target(action: object) -> str:
    if isinstance(
        action,
        (
            t.WriteFileAction,
            t.CheckWriteFileAction,
            t.CheckEditFileAction,
            t.EditFileAction,
            t.CheckMultiEditAction,
            t.MultiEditAction,
            t.CheckReplaceLinesAction,
            t.CheckPatchAction,
            t.PatchFileAction,
            t.CheckDeleteFileAction,
            t.DeleteFileAction,
            t.ReadFileAction,
        ),
    ):
        return action.path
    if isinstance(action, (t.CheckDeleteFilesAction, t.DeleteFilesAction)):
        return ", ".join(action.paths)
    if isinstance(action, t.ReplaceLinesAction):
        return f"{action.path}:{action.start_line}-{action.end_line}"
    if isinstance(action, t.CheckInsertLinesAction):
        return f"{action.path}:{action.line}"
    if isinstance(action, t.InsertLinesAction):
        return f"{action.path}:{action.line}"
    if isinstance(action, t.CheckAppendFileAction):
        return action.path
    if isinstance(action, t.AppendFileAction):
        return action.path
    if isinstance(action, t.RegexReplaceAction):
        return action.path
    if isinstance(action, t.CheckRegexReplaceAction):
        return action.path
    if isinstance(action, (t.CheckWriteFilesAction, t.WriteFilesAction)):
        return ", ".join(file.path for file in action.files)
    if isinstance(action, t.ReadFilesAction):
        return ", ".join(action.paths)
    if isinstance(action, t.ReadFileRangesAction):
        return ", ".join(f"{item.path}:{item.start_line}+{item.line_count}" for item in action.ranges)
    if isinstance(action, t.FileInfoAction):
        return ", ".join(action.paths)
    if isinstance(action, t.ImageInfoAction):
        return ", ".join(action.paths)
    if isinstance(action, t.PythonSymbolsAction):
        return ", ".join(action.paths)
    if isinstance(action, t.CodeOutlineAction):
        return ", ".join(action.paths)
    if isinstance(action, t.PythonCheckAction):
        return action.path or "."
    if isinstance(action, t.ConfigCheckAction):
        return action.path or "."
    if isinstance(action, (t.CheckJsonSetAction, t.JsonSetAction, t.CheckJsonRemoveAction, t.JsonRemoveAction)):
        return f"{action.path} {action.pointer}"
    if isinstance(action, (t.CheckJsonPatchAction, t.JsonPatchAction)):
        return f"{action.path} ({len(action.operations)} operations)"
    if isinstance(action, t.PythonDependenciesAction):
        return action.path or "."
    if isinstance(action, t.PythonDefinitionsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, (t.CheckReplacePythonDefinitionAction, t.ReplacePythonDefinitionAction)):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, t.PythonCallsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, t.PythonCallGraphAction):
        return action.path or "."
    if isinstance(action, t.PythonReferencesAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, t.PythonReferenceContextsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, t.PythonRenamePreviewAction):
        return f"{action.symbol} -> {action.new_name} in {action.path or '.'}"
    if isinstance(action, t.PythonRenameAction):
        return f"{action.symbol} -> {action.new_name} in {action.path or '.'}"
    if isinstance(action, t.CheckMultiEditAction):
        return action.path
    if isinstance(action, t.CheckReplaceLinesAction):
        return f"{action.path}:{action.start_line}-{action.end_line}"
    if isinstance(action, (t.CheckPatchesAction, t.PatchFilesAction)):
        return "multiple files"
    if isinstance(action, (t.CheckMoveFileAction, t.MoveFileAction)):
        return f"{action.source} -> {action.destination}"
    if isinstance(action, (t.CheckMoveFilesAction, t.MoveFilesAction)):
        return ", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers)
    if isinstance(action, (t.CheckCopyFileAction, t.CopyFileAction)):
        return f"{action.source} -> {action.destination}"
    if isinstance(action, (t.CheckCopyFilesAction, t.CopyFilesAction)):
        return ", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers)
    if isinstance(action, (t.CheckMoveDirectoryAction, t.MoveDirectoryAction)):
        return f"{action.source} -> {action.destination}"
    if isinstance(action, (t.CheckMoveDirectoriesAction, t.MoveDirectoriesAction)):
        return ", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers)
    if isinstance(action, (t.CheckCopyDirectoryAction, t.CopyDirectoryAction)):
        return f"{action.source} -> {action.destination}"
    if isinstance(action, (t.CheckCopyDirectoriesAction, t.CopyDirectoriesAction)):
        return ", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers)
    if isinstance(action, (t.CheckCreateDirectoryAction, t.CreateDirectoryAction, t.CheckDeleteEmptyDirectoryAction, t.DeleteEmptyDirectoryAction)):
        return action.path
    if isinstance(action, (t.CheckCreateDirectoriesAction, t.CreateDirectoriesAction)):
        return ", ".join(action.paths)
    if isinstance(action, (t.CheckDeleteEmptyDirectoriesAction, t.DeleteEmptyDirectoriesAction)):
        return ", ".join(action.paths)
    if isinstance(action, (t.CheckSetExecutableAction, t.SetExecutableAction)):
        return action.path
    if isinstance(action, t.RunCommandAction):
        return f"{action.command} (cwd: {action.cwd or '.'})"
    if isinstance(action, t.RunCommandsAction):
        return ", ".join(f"{item.command} (cwd: {item.cwd or '.'})" for item in action.commands)
    if isinstance(action, t.StartCommandAction):
        return f"{action.command} (cwd: {action.cwd or '.'})"
    if isinstance(action, (t.ReadProcessAction, t.StopProcessAction)):
        return action.process_id
    if isinstance(action, (t.ListProcessesAction, t.CheckStopAllProcessesAction, t.StopAllProcessesAction)):
        return "background processes"
    if isinstance(action, t.RepoMapAction):
        return action.path or "."
    if isinstance(action, t.SearchAction):
        return action.query
    if isinstance(action, t.SearchContextsAction):
        return f"{action.query} in {action.path or '.'}"
    if isinstance(action, t.FindFilesAction):
        return f"{action.query} in {action.path or '.'}"
    if isinstance(action, t.GlobAction):
        return action.pattern
    if isinstance(action, t.ListTreeAction):
        return action.path or "."
    if isinstance(action, t.GitStatusAction):
        return "git status"
    if isinstance(action, t.GitConflictsAction):
        return action.path or "."
    if isinstance(action, t.GitDiffContextsAction):
        return action.path or "."
    if isinstance(action, t.GitInfoAction):
        return "git info"
    if isinstance(action, t.GitChangesAction):
        return "git changes"
    if isinstance(action, t.GitBranchesAction):
        return "git branches"
    if isinstance(action, (t.CheckGitFetchAction, t.GitFetchAction)):
        return action.remote or "default remote"
    if isinstance(action, (t.CheckGitPullAction, t.GitPullAction)):
        return "current branch upstream"
    if isinstance(action, (t.CheckGitPushAction, t.GitPushAction)):
        return "current branch upstream"
    if isinstance(action, (t.CheckGitRestoreAction, t.GitRestoreAction)):
        return ", ".join(action.paths)
    if isinstance(action, t.GitStashesAction):
        return "git stashes"
    if isinstance(action, (t.CheckGitStashAction, t.GitStashAction)):
        return action.message or "vibeagent stash"
    if isinstance(action, (t.CheckGitStashApplyAction, t.GitStashApplyAction, t.CheckGitStashDropAction, t.GitStashDropAction)):
        return action.stash_ref
    if isinstance(action, (t.CheckGitSwitchAction, t.GitSwitchAction)):
        return f"{action.branch}{' (create)' if action.create else ''}"
    if isinstance(action, t.ReviewChangesAction):
        return "changed files"
    if isinstance(action, t.FinalReviewAction):
        return "final review"
    if isinstance(action, t.SuggestChecksAction):
        return "check commands"
    if isinstance(action, t.ProjectCommandsAction):
        return "project commands"
    if isinstance(action, t.RelatedTestsAction):
        return "related tests"
    if isinstance(action, t.FocusedTestCommandsAction):
        return "focused test commands"
    if isinstance(action, (t.CheckFocusedTestCommandsAction, t.RunFocusedTestCommandsAction)):
        return f"up to {action.max_commands} focused test command(s)"
    if isinstance(action, t.ProjectManifestsAction):
        return "project manifests"
    if isinstance(action, t.ProjectInstructionsAction):
        return "project instructions"
    if isinstance(action, t.ProjectOverviewAction):
        return "project overview"
    if isinstance(action, t.CodeDependenciesAction):
        return action.path or "."
    if isinstance(action, t.CodeReferencesAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, t.CodeReferenceContextsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, t.CodeDefinitionsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, t.CodeRenamePreviewAction):
        return f"{action.symbol} -> {action.new_name} in {action.path or '.'}"
    if isinstance(action, t.CodeRenameAction):
        return f"{action.symbol} -> {action.new_name} in {action.path or '.'}"
    if isinstance(action, t.CommandCheckAction):
        return f"{action.command} (cwd: {action.cwd or '.'})"
    if isinstance(action, t.PortCheckAction):
        return f"{action.host}:{action.port}"
    if isinstance(action, t.HttpCheckAction):
        return action.url
    if isinstance(action, t.HttpFetchAction):
        return action.url
    if isinstance(action, t.EnvironmentInfoAction):
        return "runtime environment"
    if isinstance(action, t.GitDiffAction):
        return action.path or ("staged changes" if action.staged else "working tree")
    if isinstance(action, t.GitDiffHunksAction):
        return action.path or ("staged changes" if action.staged else "working tree")
    if isinstance(action, t.GitLogAction):
        return action.path or f"last {action.max_count} commits"
    if isinstance(action, t.GitShowAction):
        return f"{action.rev}{f' -- {action.path}' if action.path else ''}"
    if isinstance(action, t.GitBlameAction):
        if action.start_line is not None:
            return f"{action.path}:{action.start_line}+{action.line_count or 120}"
        return action.path
    if isinstance(action, (t.CheckGitStageAction, t.GitStageAction, t.CheckGitUnstageAction, t.GitUnstageAction)):
        return ", ".join(action.paths)
    if isinstance(action, (t.CheckGitCommitAction, t.GitCommitAction)):
        return summarize(action.message, 80)
    if isinstance(action, (t.RunCommandAction, t.CheckStartCommandAction, t.StartCommandAction)):
        return f"{action.command} (cwd: {action.cwd or '.'})"
    if isinstance(action, (t.CheckRunCommandsAction, t.RunCommandsAction)):
        return ", ".join(f"{item.command} (cwd: {item.cwd or '.'})" for item in action.commands)
    if isinstance(action, (t.CheckSuggestedChecksAction, t.RunSuggestedChecksAction)):
        return f"up to {action.max_commands} suggested checks"
    if isinstance(action, (t.WaitProcessAction, t.CheckStopProcessAction)):
        return action.process_id
    if isinstance(action, (t.CheckWriteProcessAction, t.WriteProcessAction)):
        return f"{action.process_id} ({len(action.content)} chars)"
    if isinstance(action, t.SessionSummaryAction):
        return action.run_id or "current session"
    if isinstance(action, t.SessionPlanAction):
        return action.run_id or "current session"
    if isinstance(action, t.SessionTranscriptAction):
        return action.run_id or "current session"
    if isinstance(action, (t.SessionVerificationAction, t.SessionAuditAction, t.SessionHandoffAction)):
        return action.run_id or "current session"
    if isinstance(action, t.CheckpointCreateAction):
        return action.label or "checkpoint"
    if isinstance(action, t.CheckpointListAction):
        return "checkpoints"
    if isinstance(action, (t.CheckCheckpointPruneAction, t.CheckpointPruneAction)):
        return f"keep_last={action.keep_last}"
    if isinstance(action, (t.CheckpointShowAction, t.CheckpointDiffAction, t.CheckpointStatusAction, t.CheckCheckpointRestoreAction, t.CheckpointRestoreAction, t.CheckCheckpointDeleteAction, t.CheckpointDeleteAction)):
        return action.checkpoint_id
    if isinstance(action, t.UpdatePlanAction):
        current = next((item.step for item in action.plan if item.status == "in_progress"), None)
        return current or "plan"
    if getattr(action, "type", None) == "list_files":
        return str(getattr(action, "path", None) or ".")
    if isinstance(action, t.FinishAction):
        return "finish"
    return ""


def log_action(logger: t.AgentLogger | None, action: object) -> None:
    if not logger:
        return
    action_type = getattr(action, "type", None)
    if action_type == "list_files":
        logger("listing files", getattr(action, "path", None) or ".")
    elif action_type == "list_tree":
        logger("listing tree", getattr(action, "path", None) or ".")
    elif action_type == "repo_map":
        logger("mapping repo", build_action_target(action))
    elif action_type == "read_file":
        logger("reading file", getattr(action, "path"))
    elif action_type == "read_file_context":
        logger("reading file context", build_action_target(action))
    elif action_type == "read_file_contexts":
        logger("reading file contexts", build_action_target(action))
    elif action_type == "output_contexts":
        logger("reading output contexts", build_action_target(action))
    elif action_type == "tail_file":
        logger("tailing file", getattr(action, "path"))
    elif action_type == "read_files":
        logger("reading files", build_action_target(action))
    elif action_type == "read_file_ranges":
        logger("reading file ranges", build_action_target(action))
    elif action_type == "file_info":
        logger("reading file info", build_action_target(action))
    elif action_type == "image_info":
        logger("reading image info", build_action_target(action))
    elif action_type == "python_symbols":
        logger("reading python symbols", build_action_target(action))
    elif action_type == "code_outline":
        logger("reading code outline", build_action_target(action))
    elif action_type == "python_check":
        logger("checking python", build_action_target(action))
    elif action_type == "config_check":
        logger("checking config", build_action_target(action))
    elif action_type == "python_dependencies":
        logger("reading python dependencies", build_action_target(action))
    elif action_type == "code_dependencies":
        logger("reading code dependencies", build_action_target(action))
    elif action_type == "code_references":
        logger("reading code references", build_action_target(action))
    elif action_type == "code_reference_contexts":
        logger("reading code reference contexts", build_action_target(action))
    elif action_type == "code_definitions":
        logger("reading code definitions", build_action_target(action))
    elif action_type == "code_rename_preview":
        logger("previewing code rename", build_action_target(action))
    elif action_type == "code_rename":
        logger("renaming code symbol", build_action_target(action))
    elif action_type == "python_definitions":
        logger("reading python definitions", build_action_target(action))
    elif action_type == "python_calls":
        logger("reading python calls", build_action_target(action))
    elif action_type == "python_call_graph":
        logger("reading python call graph", build_action_target(action))
    elif action_type == "python_references":
        logger("reading python references", build_action_target(action))
    elif action_type == "python_reference_contexts":
        logger("reading python reference contexts", build_action_target(action))
    elif action_type == "python_rename_preview":
        logger("previewing python rename", build_action_target(action))
    elif action_type == "python_rename":
        logger("renaming python symbol", build_action_target(action))
    elif action_type == "search":
        logger("searching", getattr(action, "query"))
    elif action_type == "search_contexts":
        logger("searching contexts", build_action_target(action))
    elif action_type == "find_files":
        logger("finding files", build_action_target(action))
    elif action_type == "glob":
        logger("globbing", getattr(action, "pattern"))
    elif action_type == "git_status":
        logger("checking git status", None)
    elif action_type == "git_conflicts":
        logger("scanning git conflicts", getattr(action, "path", None) or ".")
    elif action_type == "git_diff_contexts":
        logger("reading git diff contexts", getattr(action, "path", None) or ".")
    elif action_type == "git_info":
        logger("reading git info", None)
    elif action_type == "git_changes":
        logger("reading git changes", None)
    elif action_type == "git_branches":
        logger("reading git branches", None)
    elif action_type == "check_git_fetch":
        logger("checking git fetch", build_action_target(action))
    elif action_type == "git_fetch":
        logger("fetching git remote", build_action_target(action))
    elif action_type == "check_git_pull":
        logger("checking git pull", build_action_target(action))
    elif action_type == "git_pull":
        logger("pulling git upstream", build_action_target(action))
    elif action_type == "check_git_push":
        logger("checking git push", build_action_target(action))
    elif action_type == "git_push":
        logger("pushing git upstream", build_action_target(action))
    elif action_type == "check_git_restore":
        logger("checking git restore", build_action_target(action))
    elif action_type == "git_restore":
        logger("restoring git paths", build_action_target(action))
    elif action_type == "git_stashes":
        logger("reading git stashes", build_action_target(action))
    elif action_type == "check_git_stash":
        logger("checking git stash", build_action_target(action))
    elif action_type == "git_stash":
        logger("stashing git changes", build_action_target(action))
    elif action_type == "check_git_stash_apply":
        logger("checking git stash apply", build_action_target(action))
    elif action_type == "git_stash_apply":
        logger("applying git stash", build_action_target(action))
    elif action_type == "check_git_stash_drop":
        logger("checking git stash drop", build_action_target(action))
    elif action_type == "git_stash_drop":
        logger("dropping git stash", build_action_target(action))
    elif action_type == "check_git_switch":
        logger("checking git switch", build_action_target(action))
    elif action_type == "git_switch":
        logger("switching git branch", build_action_target(action))
    elif action_type == "check_git_stage":
        logger("checking git stage", build_action_target(action))
    elif action_type == "git_stage":
        logger("staging git paths", build_action_target(action))
    elif action_type == "check_git_unstage":
        logger("checking git unstage", build_action_target(action))
    elif action_type == "git_unstage":
        logger("unstaging git paths", build_action_target(action))
    elif action_type == "check_git_commit":
        logger("checking git commit", build_action_target(action))
    elif action_type == "git_commit":
        logger("committing staged changes", build_action_target(action))
    elif action_type == "review_changes":
        logger("reviewing changes", None)
    elif action_type == "final_review":
        logger("final reviewing changes", None)
    elif action_type == "suggest_checks":
        logger("suggesting checks", None)
    elif action_type == "check_suggested_checks":
        logger("checking suggested checks", build_action_target(action))
    elif action_type == "run_suggested_checks":
        logger("running suggested checks", build_action_target(action))
    elif action_type == "project_commands":
        logger("reading project commands", None)
    elif action_type == "related_tests":
        logger("finding related tests", build_action_target(action))
    elif action_type == "focused_test_commands":
        logger("suggesting focused test commands", build_action_target(action))
    elif action_type == "check_focused_test_commands":
        logger("checking focused test commands", build_action_target(action))
    elif action_type == "run_focused_test_commands":
        logger("running focused test commands", build_action_target(action))
    elif action_type == "project_manifests":
        logger("reading project manifests", None)
    elif action_type == "project_instructions":
        logger("reading project instructions", None)
    elif action_type == "project_overview":
        logger("reading project overview", None)
    elif action_type == "command_check":
        logger("checking command", build_action_target(action))
    elif action_type == "check_run_commands":
        logger("checking commands", build_action_target(action))
    elif action_type == "environment_info":
        logger("reading environment info", None)
    elif action_type == "git_diff":
        logger("reading git diff", build_action_target(action))
    elif action_type == "git_diff_hunks":
        logger("reading git diff hunks", build_action_target(action))
    elif action_type == "git_log":
        logger("reading git log", build_action_target(action))
    elif action_type == "git_show":
        logger("reading git show", build_action_target(action))
    elif action_type == "git_blame":
        logger("reading git blame", build_action_target(action))
    elif action_type == "session_summary":
        logger("reading session summary", build_action_target(action))
    elif action_type == "session_plan":
        logger("reading session plan", build_action_target(action))
    elif action_type == "session_transcript":
        logger("reading session transcript", build_action_target(action))
    elif action_type == "session_search":
        logger("searching session", build_action_target(action))
    elif action_type == "session_commands":
        logger("reading session commands", build_action_target(action))
    elif action_type == "session_output_contexts":
        logger("reading session output contexts", build_action_target(action))
    elif action_type == "session_output_diagnostics":
        logger("reading session output diagnostics", build_action_target(action))
    elif action_type == "session_files":
        logger("reading session files", build_action_target(action))
    elif action_type == "session_failures":
        logger("reading session failures", build_action_target(action))
    elif action_type == "session_verification":
        logger("reading session verification", build_action_target(action))
    elif action_type == "session_audit":
        logger("reading session audit", build_action_target(action))
    elif action_type == "session_handoff":
        logger("reading session handoff", build_action_target(action))
    elif action_type == "checkpoint_create":
        logger("creating checkpoint", build_action_target(action))
    elif action_type == "checkpoint_list":
        logger("listing checkpoints", build_action_target(action))
    elif action_type == "checkpoint_show":
        logger("reading checkpoint", build_action_target(action))
    elif action_type == "checkpoint_diff":
        logger("reading checkpoint diff", build_action_target(action))
    elif action_type == "checkpoint_status":
        logger("checking checkpoint status", build_action_target(action))
    elif action_type == "check_checkpoint_restore":
        logger("checking checkpoint restore", build_action_target(action))
    elif action_type == "checkpoint_restore":
        logger("restoring checkpoint", build_action_target(action))
    elif action_type == "check_checkpoint_delete":
        logger("checking checkpoint delete", build_action_target(action))
    elif action_type == "checkpoint_delete":
        logger("deleting checkpoint", build_action_target(action))
    elif action_type == "check_checkpoint_prune":
        logger("checking checkpoint prune", build_action_target(action))
    elif action_type == "checkpoint_prune":
        logger("pruning checkpoints", build_action_target(action))
    elif action_type == "check_edit_file":
        logger("checking file edit", build_action_target(action))
    elif action_type == "edit_file":
        logger("editing file", getattr(action, "path"))
    elif action_type == "check_multi_edit_file":
        logger("checking multi-edit", build_action_target(action))
    elif action_type == "multi_edit_file":
        logger("multi-editing file", getattr(action, "path"))
    elif action_type == "check_replace_python_definition":
        logger("checking python definition replacement", build_action_target(action))
    elif action_type == "replace_python_definition":
        logger("replacing python definition", build_action_target(action))
    elif action_type == "check_replace_lines":
        logger("checking replace lines", build_action_target(action))
    elif action_type == "replace_lines":
        logger("replacing lines", build_action_target(action))
    elif action_type == "check_insert_lines":
        logger("checking insert lines", build_action_target(action))
    elif action_type == "insert_lines":
        logger("inserting lines", build_action_target(action))
    elif action_type == "check_append_file":
        logger("checking append file", build_action_target(action))
    elif action_type == "append_file":
        logger("appending file", build_action_target(action))
    elif action_type == "regex_replace":
        logger("regex replacing", build_action_target(action))
    elif action_type == "check_regex_replace":
        logger("checking regex replace", build_action_target(action))
    elif action_type == "check_json_set":
        logger("checking json set", build_action_target(action))
    elif action_type == "json_set":
        logger("setting json", build_action_target(action))
    elif action_type == "check_json_remove":
        logger("checking json remove", build_action_target(action))
    elif action_type == "json_remove":
        logger("removing json", build_action_target(action))
    elif action_type == "check_json_patch":
        logger("checking json patch", build_action_target(action))
    elif action_type == "json_patch":
        logger("patching json", build_action_target(action))
    elif action_type == "check_patch":
        logger("checking patch", getattr(action, "path"))
    elif action_type == "check_patches":
        logger("checking patches", "multiple files")
    elif action_type == "patch_file":
        logger("patching file", getattr(action, "path"))
    elif action_type == "patch_files":
        logger("patching files", "multiple files")
    elif action_type == "check_delete_file":
        logger("checking delete file", build_action_target(action))
    elif action_type == "delete_file":
        logger("deleting file", getattr(action, "path"))
    elif action_type == "check_delete_files":
        logger("checking file deletes", build_action_target(action))
    elif action_type == "delete_files":
        logger("deleting files", build_action_target(action))
    elif action_type == "check_move_file":
        logger("checking move file", build_action_target(action))
    elif action_type == "move_file":
        logger("moving file", build_action_target(action))
    elif action_type == "check_move_files":
        logger("checking file moves", build_action_target(action))
    elif action_type == "move_files":
        logger("moving files", build_action_target(action))
    elif action_type == "check_copy_file":
        logger("checking copy file", build_action_target(action))
    elif action_type == "copy_file":
        logger("copying file", build_action_target(action))
    elif action_type == "check_copy_files":
        logger("checking file copies", build_action_target(action))
    elif action_type == "copy_files":
        logger("copying files", build_action_target(action))
    elif action_type == "check_move_dir":
        logger("checking move directory", build_action_target(action))
    elif action_type == "move_dir":
        logger("moving directory", build_action_target(action))
    elif action_type == "check_move_dirs":
        logger("checking directory moves", build_action_target(action))
    elif action_type == "move_dirs":
        logger("moving directories", build_action_target(action))
    elif action_type == "check_copy_dir":
        logger("checking copy directory", build_action_target(action))
    elif action_type == "copy_dir":
        logger("copying directory", build_action_target(action))
    elif action_type == "check_copy_dirs":
        logger("checking directory copies", build_action_target(action))
    elif action_type == "copy_dirs":
        logger("copying directories", build_action_target(action))
    elif action_type == "check_create_dir":
        logger("checking create directory", build_action_target(action))
    elif action_type == "create_dir":
        logger("creating directory", build_action_target(action))
    elif action_type == "check_create_dirs":
        logger("checking directory creates", build_action_target(action))
    elif action_type == "create_dirs":
        logger("creating directories", build_action_target(action))
    elif action_type == "check_delete_empty_dir":
        logger("checking delete empty directory", build_action_target(action))
    elif action_type == "delete_empty_dir":
        logger("deleting empty directory", build_action_target(action))
    elif action_type == "check_delete_empty_dirs":
        logger("checking empty directory deletes", build_action_target(action))
    elif action_type == "delete_empty_dirs":
        logger("deleting empty directories", build_action_target(action))
    elif action_type == "check_set_executable":
        logger("checking executable bit", build_action_target(action))
    elif action_type == "set_executable":
        logger("setting executable bit", build_action_target(action))
    elif action_type == "check_write_file":
        logger("checking file write", build_action_target(action))
    elif action_type == "write_file":
        logger("writing file", getattr(action, "path"))
    elif action_type == "check_write_files":
        logger("checking file writes", build_action_target(action))
    elif action_type == "write_files":
        logger("writing files", build_action_target(action))
    elif action_type == "run_command":
        logger("running command", build_action_target(action))
    elif action_type == "run_commands":
        logger("running commands", build_action_target(action))
    elif action_type == "check_start_command":
        logger("checking start command", build_action_target(action))
    elif action_type == "port_check":
        logger("checking port", build_action_target(action))
    elif action_type == "http_check":
        logger("checking http", build_action_target(action))
    elif action_type == "http_fetch":
        logger("fetching http", build_action_target(action))
    elif action_type == "start_command":
        logger("starting command", build_action_target(action))
    elif action_type == "read_process":
        logger("reading process", getattr(action, "process_id"))
    elif action_type == "wait_process":
        logger("waiting process", getattr(action, "process_id"))
    elif action_type == "check_write_process":
        logger("checking process write", build_action_target(action))
    elif action_type == "write_process":
        logger("writing process", build_action_target(action))
    elif action_type == "list_processes":
        logger("listing processes", None)
    elif action_type == "check_stop_all_processes":
        logger("checking stop all processes", None)
    elif action_type == "check_stop_process":
        logger("checking stop process", getattr(action, "process_id"))
    elif action_type == "stop_all_processes":
        logger("stopping all processes", None)
    elif action_type == "stop_process":
        logger("stopping process", getattr(action, "process_id"))
    elif action_type == "update_plan":
        logger("updating plan", build_action_target(action))
