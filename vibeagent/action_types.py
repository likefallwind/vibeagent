from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias


PlanItemStatus: TypeAlias = Literal["pending", "in_progress", "completed"]


@dataclass(frozen=True)
class WriteFileAction:
    type: Literal["write_file"]
    path: str
    content: str


@dataclass(frozen=True)
class CheckWriteFileAction:
    type: Literal["check_write_file"]
    path: str
    content: str


@dataclass(frozen=True)
class WriteFileItem:
    path: str
    content: str


@dataclass(frozen=True)
class WriteFilesAction:
    type: Literal["write_files"]
    files: list[WriteFileItem]


@dataclass(frozen=True)
class CheckWriteFilesAction:
    type: Literal["check_write_files"]
    files: list[WriteFileItem]


@dataclass(frozen=True)
class ListFilesAction:
    type: Literal["list_files"]
    path: str | None = None


@dataclass(frozen=True)
class ListTreeAction:
    type: Literal["list_tree"]
    path: str | None = None
    max_depth: int = 3
    max_entries: int = 200


@dataclass(frozen=True)
class RepoMapAction:
    type: Literal["repo_map"]
    path: str | None = None
    max_depth: int = 3
    max_files: int = 80
    max_symbols: int = 120


@dataclass(frozen=True)
class ReadFileAction:
    type: Literal["read_file"]
    path: str
    start_line: int | None = None
    line_count: int | None = None
    max_bytes: int = 20_000
    show_line_numbers: bool = False


@dataclass(frozen=True)
class ReadFileContextAction:
    type: Literal["read_file_context"]
    path: str
    line: int
    context_lines: int = 20
    max_bytes: int = 20_000


@dataclass(frozen=True)
class ReadFileContextItem:
    path: str
    line: int
    context_lines: int = 20


@dataclass(frozen=True)
class ReadFileContextsAction:
    type: Literal["read_file_contexts"]
    contexts: list[ReadFileContextItem]
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class OutputContextsAction:
    type: Literal["output_contexts"]
    text: str
    context_lines: int = 5
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class OutputDiagnosticsAction:
    type: Literal["output_diagnostics"]
    text: str
    context_lines: int = 2
    max_diagnostics: int = 50
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class TailFileAction:
    type: Literal["tail_file"]
    path: str
    line_count: int = 80
    max_bytes: int = 20_000


@dataclass(frozen=True)
class ReadFilesAction:
    type: Literal["read_files"]
    paths: list[str]
    max_bytes_per_file: int = 20_000
    show_line_numbers: bool = False


@dataclass(frozen=True)
class ReadFileRangeItem:
    path: str
    start_line: int
    line_count: int = 120


@dataclass(frozen=True)
class ReadFileRangesAction:
    type: Literal["read_file_ranges"]
    ranges: list[ReadFileRangeItem]
    max_bytes_per_range: int = 20_000


@dataclass(frozen=True)
class FileInfoAction:
    type: Literal["file_info"]
    paths: list[str]


@dataclass(frozen=True)
class ImageInfoAction:
    type: Literal["image_info"]
    paths: list[str]


@dataclass(frozen=True)
class PythonSymbolsAction:
    type: Literal["python_symbols"]
    paths: list[str]


@dataclass(frozen=True)
class CodeOutlineAction:
    type: Literal["code_outline"]
    paths: list[str]
    max_symbols: int = 200


@dataclass(frozen=True)
class PythonCheckAction:
    type: Literal["python_check"]
    path: str | None = None
    max_files: int = 200


@dataclass(frozen=True)
class ConfigCheckAction:
    type: Literal["config_check"]
    path: str | None = None
    max_files: int = 200


@dataclass(frozen=True)
class JsonSetAction:
    type: Literal["json_set"]
    path: str
    pointer: str
    value: Any
    create_missing: bool = False


@dataclass(frozen=True)
class CheckJsonSetAction:
    type: Literal["check_json_set"]
    path: str
    pointer: str
    value: Any
    create_missing: bool = False


@dataclass(frozen=True)
class JsonRemoveAction:
    type: Literal["json_remove"]
    path: str
    pointer: str


@dataclass(frozen=True)
class CheckJsonRemoveAction:
    type: Literal["check_json_remove"]
    path: str
    pointer: str


@dataclass(frozen=True)
class JsonPatchOperation:
    op: Literal["add", "replace", "remove"]
    path: str
    value: Any = None


@dataclass(frozen=True)
class JsonPatchAction:
    type: Literal["json_patch"]
    path: str
    operations: list[JsonPatchOperation]


@dataclass(frozen=True)
class CheckJsonPatchAction:
    type: Literal["check_json_patch"]
    path: str
    operations: list[JsonPatchOperation]


@dataclass(frozen=True)
class PythonDependenciesAction:
    type: Literal["python_dependencies"]
    path: str | None = None
    max_files: int = 100
    max_imports: int = 500


@dataclass(frozen=True)
class CodeDependenciesAction:
    type: Literal["code_dependencies"]
    path: str | None = None
    max_files: int = 100
    max_imports: int = 500


@dataclass(frozen=True)
class CodeReferencesAction:
    type: Literal["code_references"]
    symbol: str
    path: str | None = None
    max_matches: int = 200


@dataclass(frozen=True)
class CodeReferenceContextsAction:
    type: Literal["code_reference_contexts"]
    symbol: str
    path: str | None = None
    max_matches: int = 50
    context_lines: int = 3
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class CodeDefinitionsAction:
    type: Literal["code_definitions"]
    symbol: str
    path: str | None = None
    max_matches: int = 50
    max_lines: int = 80


@dataclass(frozen=True)
class CodeRenamePreviewAction:
    type: Literal["code_rename_preview"]
    symbol: str
    new_name: str
    path: str | None = None
    max_files: int = 100
    max_replacements: int = 500


@dataclass(frozen=True)
class CodeRenameAction:
    type: Literal["code_rename"]
    symbol: str
    new_name: str
    path: str | None = None
    max_files: int = 100
    max_replacements: int = 2000


@dataclass(frozen=True)
class PythonDefinitionsAction:
    type: Literal["python_definitions"]
    symbol: str
    path: str | None = None
    max_matches: int = 50
    max_lines: int = 120


@dataclass(frozen=True)
class ReplacePythonDefinitionAction:
    type: Literal["replace_python_definition"]
    symbol: str
    content: str
    path: str | None = None


@dataclass(frozen=True)
class CheckReplacePythonDefinitionAction:
    type: Literal["check_replace_python_definition"]
    symbol: str
    content: str
    path: str | None = None


@dataclass(frozen=True)
class PythonCallsAction:
    type: Literal["python_calls"]
    symbol: str
    path: str | None = None
    max_matches: int = 200


@dataclass(frozen=True)
class PythonCallGraphAction:
    type: Literal["python_call_graph"]
    path: str | None = None
    max_files: int = 100
    max_edges: int = 500


@dataclass(frozen=True)
class PythonReferencesAction:
    type: Literal["python_references"]
    symbol: str
    path: str | None = None
    max_matches: int = 200


@dataclass(frozen=True)
class PythonReferenceContextsAction:
    type: Literal["python_reference_contexts"]
    symbol: str
    path: str | None = None
    max_matches: int = 50
    context_lines: int = 3
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class PythonRenamePreviewAction:
    type: Literal["python_rename_preview"]
    symbol: str
    new_name: str
    path: str | None = None
    max_files: int = 100
    max_replacements: int = 500


@dataclass(frozen=True)
class PythonRenameAction:
    type: Literal["python_rename"]
    symbol: str
    new_name: str
    path: str | None = None
    max_files: int = 100
    max_replacements: int = 2000


@dataclass(frozen=True)
class SearchAction:
    type: Literal["search"]
    query: str
    path: str | None = None
    regex: bool = False
    case_sensitive: bool = True
    max_matches: int = 80
    context_lines: int = 0


@dataclass(frozen=True)
class SearchContextsAction:
    type: Literal["search_contexts"]
    query: str
    path: str | None = None
    regex: bool = False
    case_sensitive: bool = True
    max_matches: int = 20
    context_lines: int = 3
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class FindFilesAction:
    type: Literal["find_files"]
    query: str
    path: str | None = None
    regex: bool = False
    case_sensitive: bool = False
    include_dirs: bool = False
    max_matches: int = 100


@dataclass(frozen=True)
class GlobAction:
    type: Literal["glob"]
    pattern: str
    max_matches: int = 200
    include_dirs: bool = False


@dataclass(frozen=True)
class GitStatusAction:
    type: Literal["git_status"]


@dataclass(frozen=True)
class GitConflictsAction:
    type: Literal["git_conflicts"]
    path: str | None = None
    max_markers: int = 200
    max_files: int = 5000


@dataclass(frozen=True)
class GitInfoAction:
    type: Literal["git_info"]


@dataclass(frozen=True)
class GitChangesAction:
    type: Literal["git_changes"]


@dataclass(frozen=True)
class GitBranchesAction:
    type: Literal["git_branches"]
    max_branches: int = 100


@dataclass(frozen=True)
class CheckGitFetchAction:
    type: Literal["check_git_fetch"]
    remote: str | None = None


@dataclass(frozen=True)
class GitFetchAction:
    type: Literal["git_fetch"]
    remote: str | None = None


@dataclass(frozen=True)
class CheckGitPullAction:
    type: Literal["check_git_pull"]


@dataclass(frozen=True)
class GitPullAction:
    type: Literal["git_pull"]


@dataclass(frozen=True)
class CheckGitPushAction:
    type: Literal["check_git_push"]


@dataclass(frozen=True)
class GitPushAction:
    type: Literal["git_push"]


@dataclass(frozen=True)
class CheckGitRestoreAction:
    type: Literal["check_git_restore"]
    paths: list[str]


@dataclass(frozen=True)
class GitRestoreAction:
    type: Literal["git_restore"]
    paths: list[str]


@dataclass(frozen=True)
class GitStashesAction:
    type: Literal["git_stashes"]
    max_entries: int = 20


@dataclass(frozen=True)
class CheckGitStashAction:
    type: Literal["check_git_stash"]
    message: str | None = None
    include_untracked: bool = False


@dataclass(frozen=True)
class GitStashAction:
    type: Literal["git_stash"]
    message: str | None = None
    include_untracked: bool = False


@dataclass(frozen=True)
class CheckGitStashApplyAction:
    type: Literal["check_git_stash_apply"]
    stash_ref: str


@dataclass(frozen=True)
class GitStashApplyAction:
    type: Literal["git_stash_apply"]
    stash_ref: str


@dataclass(frozen=True)
class CheckGitStashDropAction:
    type: Literal["check_git_stash_drop"]
    stash_ref: str


@dataclass(frozen=True)
class GitStashDropAction:
    type: Literal["git_stash_drop"]
    stash_ref: str


@dataclass(frozen=True)
class GitSwitchAction:
    type: Literal["git_switch"]
    branch: str
    create: bool = False


@dataclass(frozen=True)
class CheckGitSwitchAction:
    type: Literal["check_git_switch"]
    branch: str
    create: bool = False


@dataclass(frozen=True)
class GitStageAction:
    type: Literal["git_stage"]
    paths: list[str]


@dataclass(frozen=True)
class CheckGitStageAction:
    type: Literal["check_git_stage"]
    paths: list[str]


@dataclass(frozen=True)
class GitUnstageAction:
    type: Literal["git_unstage"]
    paths: list[str]


@dataclass(frozen=True)
class CheckGitUnstageAction:
    type: Literal["check_git_unstage"]
    paths: list[str]


@dataclass(frozen=True)
class GitCommitAction:
    type: Literal["git_commit"]
    message: str


@dataclass(frozen=True)
class CheckGitCommitAction:
    type: Literal["check_git_commit"]
    message: str


@dataclass(frozen=True)
class ReviewChangesAction:
    type: Literal["review_changes"]
    max_files: int = 200


@dataclass(frozen=True)
class FinalReviewAction:
    type: Literal["final_review"]
    max_files: int = 200
    max_checks: int = 10


@dataclass(frozen=True)
class SuggestChecksAction:
    type: Literal["suggest_checks"]
    max_commands: int = 20


@dataclass(frozen=True)
class CheckSuggestedChecksAction:
    type: Literal["check_suggested_checks"]
    max_commands: int = 10


@dataclass(frozen=True)
class RunSuggestedChecksAction:
    type: Literal["run_suggested_checks"]
    max_commands: int = 10
    timeout_ms: int | None = None
    max_output_chars: int | None = None
    stop_on_failure: bool = True
    extract_output_contexts: bool = False
    extract_output_diagnostics: bool = False
    context_lines: int = 5
    max_diagnostics: int = 50
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class ProjectCommandsAction:
    type: Literal["project_commands"]
    max_commands: int = 100
    max_files: int = 30


@dataclass(frozen=True)
class RelatedTestsAction:
    type: Literal["related_tests"]
    paths: list[str] | None = None
    max_paths: int = 100
    max_candidates: int = 200


@dataclass(frozen=True)
class FocusedTestCommandsAction:
    type: Literal["focused_test_commands"]
    paths: list[str] | None = None
    max_paths: int = 100
    max_candidates: int = 200
    max_commands: int = 50


@dataclass(frozen=True)
class CheckFocusedTestCommandsAction:
    type: Literal["check_focused_test_commands"]
    paths: list[str] | None = None
    max_paths: int = 100
    max_candidates: int = 200
    max_commands: int = 10


@dataclass(frozen=True)
class RunFocusedTestCommandsAction:
    type: Literal["run_focused_test_commands"]
    paths: list[str] | None = None
    max_paths: int = 100
    max_candidates: int = 200
    max_commands: int = 10
    timeout_ms: int | None = None
    max_output_chars: int | None = None
    stop_on_failure: bool = True
    extract_output_contexts: bool = False
    extract_output_diagnostics: bool = False
    context_lines: int = 5
    max_diagnostics: int = 50
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class ProjectManifestsAction:
    type: Literal["project_manifests"]
    max_files: int = 30
    max_items: int = 500


@dataclass(frozen=True)
class ProjectInstructionsAction:
    type: Literal["project_instructions"]
    max_files: int = 20
    max_bytes: int = 12_000


@dataclass(frozen=True)
class ProjectTodosAction:
    type: Literal["project_todos"]
    path: str | None = None
    max_items: int = 100
    max_files: int = 1000


@dataclass(frozen=True)
class ProjectOverviewAction:
    type: Literal["project_overview"]
    max_files: int = 80
    max_commands: int = 20
    max_checks: int = 10
    max_manifests: int = 10


@dataclass(frozen=True)
class CommandCheckAction:
    type: Literal["command_check"]
    command: str
    cwd: str | None = None


@dataclass(frozen=True)
class RunCommandItem:
    command: str
    timeout_ms: int | None = None
    cwd: str | None = None
    max_output_chars: int | None = None
    extract_output_contexts: bool = False
    extract_output_diagnostics: bool = False
    context_lines: int = 5
    max_diagnostics: int = 50
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class CheckRunCommandsAction:
    type: Literal["check_run_commands"]
    commands: list[RunCommandItem]


@dataclass(frozen=True)
class CheckStartCommandAction:
    type: Literal["check_start_command"]
    command: str
    cwd: str | None = None


@dataclass(frozen=True)
class PortCheckAction:
    type: Literal["port_check"]
    port: int
    host: str = "127.0.0.1"
    timeout_ms: int | None = None


@dataclass(frozen=True)
class HttpCheckAction:
    type: Literal["http_check"]
    url: str
    timeout_ms: int | None = None
    max_body_chars: int | None = None
    contains: str | None = None
    regex: bool = False


@dataclass(frozen=True)
class HttpFetchAction:
    type: Literal["http_fetch"]
    url: str
    timeout_ms: int | None = None
    max_body_chars: int | None = None


@dataclass(frozen=True)
class EnvironmentInfoAction:
    type: Literal["environment_info"]


@dataclass(frozen=True)
class GitDiffAction:
    type: Literal["git_diff"]
    path: str | None = None
    staged: bool = False
    max_output_chars: int = 12000


@dataclass(frozen=True)
class GitDiffHunksAction:
    type: Literal["git_diff_hunks"]
    path: str | None = None
    staged: bool = False
    max_hunks: int = 80
    max_lines_per_hunk: int = 80


@dataclass(frozen=True)
class GitDiffContextsAction:
    type: Literal["git_diff_contexts"]
    path: str | None = None
    staged: bool = False
    context_lines: int = 5
    max_hunks: int = 80
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class GitLogAction:
    type: Literal["git_log"]
    max_count: int = 5
    path: str | None = None


@dataclass(frozen=True)
class GitShowAction:
    type: Literal["git_show"]
    rev: str = "HEAD"
    path: str | None = None
    max_output_chars: int = 12000


@dataclass(frozen=True)
class GitBlameAction:
    type: Literal["git_blame"]
    path: str
    start_line: int | None = None
    line_count: int | None = None
    max_output_chars: int = 12000


@dataclass(frozen=True)
class SessionSummaryAction:
    type: Literal["session_summary"]
    run_id: str | None = None
    recent_limit: int = 5


@dataclass(frozen=True)
class SessionPlanAction:
    type: Literal["session_plan"]
    run_id: str | None = None


@dataclass(frozen=True)
class SessionTranscriptAction:
    type: Literal["session_transcript"]
    run_id: str | None = None
    max_events: int = 80
    max_text: int = 500


@dataclass(frozen=True)
class SessionSearchAction:
    type: Literal["session_search"]
    query: str
    run_id: str | None = None
    max_matches: int = 20
    max_text: int = 500
    case_sensitive: bool = False


@dataclass(frozen=True)
class SessionCommandsAction:
    type: Literal["session_commands"]
    run_id: str | None = None
    max_commands: int = 20
    max_output_chars: int = 2_000


@dataclass(frozen=True)
class SessionOutputContextsAction:
    type: Literal["session_output_contexts"]
    run_id: str | None = None
    max_commands: int = 20
    max_output_chars: int = 20_000
    context_lines: int = 5
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class SessionOutputDiagnosticsAction:
    type: Literal["session_output_diagnostics"]
    run_id: str | None = None
    max_commands: int = 20
    max_output_chars: int = 20_000
    context_lines: int = 2
    max_diagnostics: int = 50
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class SessionFilesAction:
    type: Literal["session_files"]
    run_id: str | None = None
    max_files: int = 100


@dataclass(frozen=True)
class SessionFailuresAction:
    type: Literal["session_failures"]
    run_id: str | None = None
    max_failures: int = 50
    max_text: int = 500


@dataclass(frozen=True)
class SessionVerificationAction:
    type: Literal["session_verification"]
    run_id: str | None = None
    max_checks: int = 50


@dataclass(frozen=True)
class SessionAuditAction:
    type: Literal["session_audit"]
    run_id: str | None = None
    max_failures: int = 10
    max_files: int = 20
    max_commands: int = 10
    max_checks: int = 50
    max_text: int = 300


@dataclass(frozen=True)
class SessionHandoffAction:
    type: Literal["session_handoff"]
    run_id: str | None = None
    max_failures: int = 20
    max_files: int = 50
    max_commands: int = 10
    max_checks: int = 50
    max_output_chars: int = 1_000
    max_text: int = 500


@dataclass(frozen=True)
class CheckpointCreateAction:
    type: Literal["checkpoint_create"]
    label: str | None = None


@dataclass(frozen=True)
class CheckpointListAction:
    type: Literal["checkpoint_list"]
    max_entries: int = 20


@dataclass(frozen=True)
class CheckpointShowAction:
    type: Literal["checkpoint_show"]
    checkpoint_id: str


@dataclass(frozen=True)
class CheckpointDiffAction:
    type: Literal["checkpoint_diff"]
    checkpoint_id: str
    max_chars: int = 40_000


@dataclass(frozen=True)
class CheckpointStatusAction:
    type: Literal["checkpoint_status"]
    checkpoint_id: str


@dataclass(frozen=True)
class CheckCheckpointRestoreAction:
    type: Literal["check_checkpoint_restore"]
    checkpoint_id: str


@dataclass(frozen=True)
class CheckpointRestoreAction:
    type: Literal["checkpoint_restore"]
    checkpoint_id: str


@dataclass(frozen=True)
class CheckCheckpointDeleteAction:
    type: Literal["check_checkpoint_delete"]
    checkpoint_id: str


@dataclass(frozen=True)
class CheckpointDeleteAction:
    type: Literal["checkpoint_delete"]
    checkpoint_id: str


@dataclass(frozen=True)
class CheckCheckpointPruneAction:
    type: Literal["check_checkpoint_prune"]
    keep_last: int


@dataclass(frozen=True)
class CheckpointPruneAction:
    type: Literal["checkpoint_prune"]
    keep_last: int


@dataclass(frozen=True)
class EditFileAction:
    type: Literal["edit_file"]
    path: str
    old: str
    new: str


@dataclass(frozen=True)
class CheckEditFileAction:
    type: Literal["check_edit_file"]
    path: str
    old: str
    new: str


@dataclass(frozen=True)
class EditOperation:
    old: str
    new: str


@dataclass(frozen=True)
class MultiEditAction:
    type: Literal["multi_edit_file"]
    path: str
    edits: list[EditOperation]


@dataclass(frozen=True)
class CheckMultiEditAction:
    type: Literal["check_multi_edit_file"]
    path: str
    edits: list[EditOperation]


@dataclass(frozen=True)
class ReplaceLinesAction:
    type: Literal["replace_lines"]
    path: str
    start_line: int
    end_line: int
    content: str


@dataclass(frozen=True)
class CheckReplaceLinesAction:
    type: Literal["check_replace_lines"]
    path: str
    start_line: int
    end_line: int
    content: str


@dataclass(frozen=True)
class InsertLinesAction:
    type: Literal["insert_lines"]
    path: str
    line: int
    content: str


@dataclass(frozen=True)
class CheckInsertLinesAction:
    type: Literal["check_insert_lines"]
    path: str
    line: int
    content: str


@dataclass(frozen=True)
class AppendFileAction:
    type: Literal["append_file"]
    path: str
    content: str


@dataclass(frozen=True)
class CheckAppendFileAction:
    type: Literal["check_append_file"]
    path: str
    content: str


@dataclass(frozen=True)
class RegexReplaceAction:
    type: Literal["regex_replace"]
    path: str
    pattern: str
    replacement: str
    count: int = 0
    case_sensitive: bool = True
    multiline: bool = False
    max_replacements: int = 100


@dataclass(frozen=True)
class CheckRegexReplaceAction:
    type: Literal["check_regex_replace"]
    path: str
    pattern: str
    replacement: str
    count: int = 0
    case_sensitive: bool = True
    multiline: bool = False
    max_replacements: int = 100


@dataclass(frozen=True)
class CheckPatchAction:
    type: Literal["check_patch"]
    path: str
    patch: str


@dataclass(frozen=True)
class CheckPatchesAction:
    type: Literal["check_patches"]
    patch: str


@dataclass(frozen=True)
class PatchFileAction:
    type: Literal["patch_file"]
    path: str
    patch: str


@dataclass(frozen=True)
class PatchFilesAction:
    type: Literal["patch_files"]
    patch: str


@dataclass(frozen=True)
class DeleteFileAction:
    type: Literal["delete_file"]
    path: str


@dataclass(frozen=True)
class CheckDeleteFileAction:
    type: Literal["check_delete_file"]
    path: str


@dataclass(frozen=True)
class DeleteFilesAction:
    type: Literal["delete_files"]
    paths: list[str]


@dataclass(frozen=True)
class CheckDeleteFilesAction:
    type: Literal["check_delete_files"]
    paths: list[str]


@dataclass(frozen=True)
class MoveFileTransfer:
    source: str
    destination: str


@dataclass(frozen=True)
class MoveFileAction:
    type: Literal["move_file"]
    source: str
    destination: str


@dataclass(frozen=True)
class CheckMoveFileAction:
    type: Literal["check_move_file"]
    source: str
    destination: str


@dataclass(frozen=True)
class MoveFilesAction:
    type: Literal["move_files"]
    transfers: list[MoveFileTransfer]


@dataclass(frozen=True)
class CheckMoveFilesAction:
    type: Literal["check_move_files"]
    transfers: list[MoveFileTransfer]


@dataclass(frozen=True)
class CopyFileAction:
    type: Literal["copy_file"]
    source: str
    destination: str


@dataclass(frozen=True)
class CheckCopyFileAction:
    type: Literal["check_copy_file"]
    source: str
    destination: str


@dataclass(frozen=True)
class CopyFilesAction:
    type: Literal["copy_files"]
    transfers: list[MoveFileTransfer]


@dataclass(frozen=True)
class CheckCopyFilesAction:
    type: Literal["check_copy_files"]
    transfers: list[MoveFileTransfer]


@dataclass(frozen=True)
class MoveDirectoryAction:
    type: Literal["move_dir"]
    source: str
    destination: str


@dataclass(frozen=True)
class CheckMoveDirectoryAction:
    type: Literal["check_move_dir"]
    source: str
    destination: str


@dataclass(frozen=True)
class DirectoryTransfer:
    source: str
    destination: str


@dataclass(frozen=True)
class MoveDirectoriesAction:
    type: Literal["move_dirs"]
    transfers: list[DirectoryTransfer]


@dataclass(frozen=True)
class CheckMoveDirectoriesAction:
    type: Literal["check_move_dirs"]
    transfers: list[DirectoryTransfer]


@dataclass(frozen=True)
class CopyDirectoryAction:
    type: Literal["copy_dir"]
    source: str
    destination: str


@dataclass(frozen=True)
class CheckCopyDirectoryAction:
    type: Literal["check_copy_dir"]
    source: str
    destination: str


@dataclass(frozen=True)
class CopyDirectoriesAction:
    type: Literal["copy_dirs"]
    transfers: list[DirectoryTransfer]


@dataclass(frozen=True)
class CheckCopyDirectoriesAction:
    type: Literal["check_copy_dirs"]
    transfers: list[DirectoryTransfer]


@dataclass(frozen=True)
class CreateDirectoryAction:
    type: Literal["create_dir"]
    path: str


@dataclass(frozen=True)
class CheckCreateDirectoryAction:
    type: Literal["check_create_dir"]
    path: str


@dataclass(frozen=True)
class CreateDirectoriesAction:
    type: Literal["create_dirs"]
    paths: list[str]


@dataclass(frozen=True)
class CheckCreateDirectoriesAction:
    type: Literal["check_create_dirs"]
    paths: list[str]


@dataclass(frozen=True)
class DeleteEmptyDirectoryAction:
    type: Literal["delete_empty_dir"]
    path: str


@dataclass(frozen=True)
class CheckDeleteEmptyDirectoryAction:
    type: Literal["check_delete_empty_dir"]
    path: str


@dataclass(frozen=True)
class DeleteEmptyDirectoriesAction:
    type: Literal["delete_empty_dirs"]
    paths: list[str]


@dataclass(frozen=True)
class CheckDeleteEmptyDirectoriesAction:
    type: Literal["check_delete_empty_dirs"]
    paths: list[str]


@dataclass(frozen=True)
class SetExecutableAction:
    type: Literal["set_executable"]
    path: str
    executable: bool = True


@dataclass(frozen=True)
class CheckSetExecutableAction:
    type: Literal["check_set_executable"]
    path: str
    executable: bool = True


@dataclass(frozen=True)
class RunCommandAction:
    type: Literal["run_command"]
    command: str
    timeout_ms: int | None = None
    cwd: str | None = None
    max_output_chars: int | None = None
    extract_output_contexts: bool = False
    extract_output_diagnostics: bool = False
    context_lines: int = 5
    max_diagnostics: int = 50
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class RunCommandsAction:
    type: Literal["run_commands"]
    commands: list[RunCommandItem]
    stop_on_failure: bool = True


@dataclass(frozen=True)
class StartCommandAction:
    type: Literal["start_command"]
    command: str
    cwd: str | None = None


@dataclass(frozen=True)
class ReadProcessAction:
    type: Literal["read_process"]
    process_id: str
    max_output_chars: int | None = None


@dataclass(frozen=True)
class ProcessOutputContextsAction:
    type: Literal["process_output_contexts"]
    process_id: str
    max_output_chars: int = 20_000
    context_lines: int = 5
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class ProcessOutputDiagnosticsAction:
    type: Literal["process_output_diagnostics"]
    process_id: str
    max_output_chars: int = 20_000
    context_lines: int = 2
    max_diagnostics: int = 50
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class WaitProcessAction:
    type: Literal["wait_process"]
    process_id: str
    timeout_ms: int | None = None
    stdout_contains: str | None = None
    stderr_contains: str | None = None
    regex: bool = False
    max_output_chars: int | None = None


@dataclass(frozen=True)
class CheckWriteProcessAction:
    type: Literal["check_write_process"]
    process_id: str
    content: str


@dataclass(frozen=True)
class WriteProcessAction:
    type: Literal["write_process"]
    process_id: str
    content: str


@dataclass(frozen=True)
class ListProcessesAction:
    type: Literal["list_processes"]


@dataclass(frozen=True)
class CheckStopAllProcessesAction:
    type: Literal["check_stop_all_processes"]


@dataclass(frozen=True)
class StopProcessAction:
    type: Literal["stop_process"]
    process_id: str


@dataclass(frozen=True)
class StopAllProcessesAction:
    type: Literal["stop_all_processes"]


@dataclass(frozen=True)
class CheckStopProcessAction:
    type: Literal["check_stop_process"]
    process_id: str


@dataclass(frozen=True)
class PlanItem:
    step: str
    status: PlanItemStatus


@dataclass(frozen=True)
class UpdatePlanAction:
    type: Literal["update_plan"]
    plan: list[PlanItem]
    explanation: str | None = None


@dataclass(frozen=True)
class FinishAction:
    type: Literal["finish"]
    message: str


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
