from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any, Literal, Protocol, TypeAlias


ContentBlock: TypeAlias = dict[str, Any]
MessageContent: TypeAlias = str | list[ContentBlock]
ToolSpec: TypeAlias = dict[str, Any]
TaskStatus: TypeAlias = Literal["pending", "running", "completed", "failed", "denied"]
PlanItemStatus: TypeAlias = Literal["pending", "in_progress", "completed"]
ApprovalPolicy: TypeAlias = Literal["ask", "allow", "deny"]


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: MessageContent


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cache_creation_tokens: int | None = None
    cache_read_tokens: int | None = None


@dataclass(frozen=True)
class AssistantResponse:
    # Provider-neutral blocks:
    # - {"type": "text", "text": "..."}
    # - {"type": "tool_call", "id": "...", "name": "...", "input": {...}}
    content: list[ContentBlock]
    raw: dict[str, Any]
    usage: ModelUsage | None = None


class ChatClient(Protocol):
    # Protocol so MiniMaxClient and any future providers can plug into the same agent loop.
    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_ms: int = 120_000,
    ) -> AssistantResponse:
        ...


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
class GlobAction:
    type: Literal["glob"]
    pattern: str
    max_matches: int = 200


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


@dataclass(frozen=True)
class CommandResult:
    command: str
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    signal: str | None
    timeout_ms: int = 30_000
    cwd: str = "."
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    max_output_chars: int = 12_000
    output_contexts: list[OutputContextResult] = field(default_factory=list)
    output_context_total_refs: int = 0
    output_contexts_truncated: bool = False
    output_diagnostics: list[OutputDiagnostic] = field(default_factory=list)
    output_diagnostic_total: int = 0
    output_diagnostics_truncated: bool = False


@dataclass
class TaskStep:
    id: int
    label: str
    action_type: str
    target: str
    status: TaskStatus = "pending"
    message: str | None = None


@dataclass(frozen=True)
class ApprovalRequest:
    action_type: Literal[
        "write_file",
        "write_files",
        "edit_file",
        "multi_edit_file",
        "replace_lines",
        "insert_lines",
        "append_file",
        "regex_replace",
        "json_set",
        "json_remove",
        "json_patch",
        "patch_file",
        "patch_files",
        "delete_file",
        "delete_files",
        "move_file",
        "move_files",
        "copy_file",
        "copy_files",
        "move_dir",
        "move_dirs",
        "copy_dir",
        "copy_dirs",
        "create_dir",
        "create_dirs",
        "delete_empty_dir",
        "delete_empty_dirs",
        "set_executable",
        "git_stage",
        "git_unstage",
        "git_commit",
        "git_fetch",
        "git_pull",
        "git_push",
        "git_restore",
        "git_stash",
        "git_stash_apply",
        "git_stash_drop",
        "run_command",
        "run_commands",
        "run_suggested_checks",
        "start_command",
    ]
    target: str
    risk: str
    preview: str | None = None


@dataclass(frozen=True)
class ApprovalDecision:
    approved: bool
    message: str = ""


@dataclass(frozen=True)
class WriteFileObservation:
    kind: Literal["write_file"]
    path: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckWriteFileObservation:
    kind: Literal["check_write_file"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class WriteFileResult:
    path: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckWriteFileResult:
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class WriteFilesObservation:
    kind: Literal["write_files"]
    files: list[WriteFileResult]
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckWriteFilesObservation:
    kind: Literal["check_write_files"]
    files: list[CheckWriteFileResult]
    ok: bool
    message: str


@dataclass(frozen=True)
class RunCommandObservation:
    kind: Literal["run_command"]
    result: CommandResult


@dataclass(frozen=True)
class RunCommandsObservation:
    kind: Literal["run_commands"]
    results: list[CommandResult]
    ok: bool
    stopped_early: bool
    message: str


@dataclass(frozen=True)
class CheckRunCommandsObservation:
    kind: Literal["check_run_commands"]
    ok: bool
    checks: list[CommandCheckObservation]
    message: str


@dataclass(frozen=True)
class StartCommandObservation:
    kind: Literal["start_command"]
    process_id: str
    pid: int | None
    command: str
    cwd: str
    ok: bool
    message: str
    stdout_path: str
    stderr_path: str


@dataclass(frozen=True)
class ReadProcessObservation:
    kind: Literal["read_process"]
    process_id: str
    pid: int | None
    ok: bool
    running: bool
    exit_code: int | None
    signal: str | None
    stdout: str
    stderr: str
    max_output_chars: int
    message: str
    output_contexts: list[OutputContextResult] = field(default_factory=list)
    output_context_total_refs: int = 0
    output_contexts_truncated: bool = False
    output_diagnostics: list[OutputDiagnostic] = field(default_factory=list)
    output_diagnostic_total: int = 0
    output_diagnostics_truncated: bool = False


@dataclass(frozen=True)
class ProcessOutputContextsObservation:
    kind: Literal["process_output_contexts"]
    process_id: str
    pid: int | None
    ok: bool
    running: bool
    exit_code: int | None
    signal: str | None
    contexts: list[OutputContextResult]
    total_refs: int
    truncated: bool
    stdout_chars: int
    stderr_chars: int
    max_output_chars: int
    message: str


@dataclass(frozen=True)
class ProcessOutputDiagnosticsObservation:
    kind: Literal["process_output_diagnostics"]
    process_id: str
    pid: int | None
    ok: bool
    running: bool
    exit_code: int | None
    signal: str | None
    diagnostics: list[OutputDiagnostic]
    contexts: list[OutputContextResult]
    total_diagnostics: int
    total_refs: int
    diagnostics_truncated: bool
    contexts_truncated: bool
    stdout_chars: int
    stderr_chars: int
    max_output_chars: int
    message: str


@dataclass(frozen=True)
class WaitProcessObservation:
    kind: Literal["wait_process"]
    process_id: str
    pid: int | None
    ok: bool
    running: bool
    timed_out: bool
    matched: bool
    matched_stream: str | None
    matched_pattern: str | None
    timeout_ms: int
    exit_code: int | None
    signal: str | None
    stdout: str
    stderr: str
    max_output_chars: int
    message: str
    output_contexts: list[OutputContextResult] = field(default_factory=list)
    output_context_total_refs: int = 0
    output_contexts_truncated: bool = False
    output_diagnostics: list[OutputDiagnostic] = field(default_factory=list)
    output_diagnostic_total: int = 0
    output_diagnostics_truncated: bool = False


@dataclass(frozen=True)
class CheckWriteProcessObservation:
    kind: Literal["check_write_process"]
    process_id: str
    pid: int | None
    ok: bool
    running: bool
    command: str | None
    cwd: str | None
    content_chars: int
    message: str


@dataclass(frozen=True)
class WriteProcessObservation:
    kind: Literal["write_process"]
    process_id: str
    pid: int | None
    ok: bool
    running: bool
    command: str | None
    cwd: str | None
    content_chars: int
    message: str


@dataclass(frozen=True)
class ProcessInfo:
    process_id: str
    pid: int
    command: str
    cwd: str
    running: bool
    exit_code: int | None
    signal: str | None


@dataclass(frozen=True)
class ListProcessesObservation:
    kind: Literal["list_processes"]
    processes: list[ProcessInfo]
    message: str


@dataclass(frozen=True)
class CheckStopAllProcessesObservation:
    kind: Literal["check_stop_all_processes"]
    ok: bool
    processes: list[ProcessInfo]
    running_count: int
    message: str


@dataclass(frozen=True)
class StopProcessObservation:
    kind: Literal["stop_process"]
    process_id: str
    pid: int | None
    ok: bool
    exit_code: int | None
    signal: str | None
    message: str


@dataclass(frozen=True)
class StoppedProcessInfo:
    process_id: str
    pid: int
    command: str
    cwd: str
    ok: bool
    exit_code: int | None
    signal: str | None
    message: str


@dataclass(frozen=True)
class StopAllProcessesObservation:
    kind: Literal["stop_all_processes"]
    ok: bool
    stopped: list[StoppedProcessInfo]
    message: str


@dataclass(frozen=True)
class CheckStopProcessObservation:
    kind: Literal["check_stop_process"]
    process_id: str
    pid: int | None
    ok: bool
    command: str | None
    cwd: str | None
    running: bool
    exit_code: int | None
    signal: str | None
    message: str


@dataclass(frozen=True)
class ListFilesObservation:
    kind: Literal["list_files"]
    path: str
    files: list[str]
    total: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class ListTreeObservation:
    kind: Literal["list_tree"]
    path: str
    entries: list[str]
    total: int
    truncated: bool
    max_depth: int
    ok: bool
    message: str


@dataclass(frozen=True)
class ReadFileObservation:
    kind: Literal["read_file"]
    path: str
    content: str
    message: str
    start_line: int | None = None
    line_count: int | None = None
    truncated: bool = False
    total_bytes: int | None = None
    max_bytes: int = 20_000


@dataclass(frozen=True)
class ReadFileContextObservation:
    kind: Literal["read_file_context"]
    path: str
    ok: bool
    content: str
    message: str
    line: int
    context_lines: int = 20
    start_line: int = 1
    end_line: int = 0
    line_count: int = 0
    total_lines: int | None = None
    target_line_exists: bool = False
    truncated: bool = False
    max_bytes: int = 20_000


@dataclass(frozen=True)
class ReadFileContextResult:
    path: str
    line: int
    context_lines: int
    ok: bool
    content: str
    message: str
    start_line: int = 1
    end_line: int = 0
    line_count: int = 0
    total_lines: int | None = None
    target_line_exists: bool = False
    truncated: bool = False
    max_bytes: int = 20_000


@dataclass(frozen=True)
class ReadFileContextsObservation:
    kind: Literal["read_file_contexts"]
    contexts: list[ReadFileContextResult]
    message: str


@dataclass(frozen=True)
class OutputContextResult:
    path: str
    line: int
    column: int | None
    raw: str
    ok: bool
    content: str
    message: str
    context_lines: int = 5
    start_line: int = 1
    end_line: int = 0
    line_count: int = 0
    total_lines: int | None = None
    target_line_exists: bool = False
    truncated: bool = False
    max_bytes: int = 20_000


@dataclass(frozen=True)
class OutputContextsObservation:
    kind: Literal["output_contexts"]
    contexts: list[OutputContextResult]
    total_refs: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class OutputDiagnostic:
    severity: Literal["error", "warning", "failure", "info"]
    output_line: int
    text: str
    path: str | None = None
    line: int | None = None
    column: int | None = None
    raw: str | None = None


@dataclass(frozen=True)
class OutputDiagnosticsObservation:
    kind: Literal["output_diagnostics"]
    diagnostics: list[OutputDiagnostic]
    contexts: list[OutputContextResult]
    total_diagnostics: int
    total_refs: int
    diagnostics_truncated: bool
    contexts_truncated: bool
    message: str


@dataclass(frozen=True)
class TailFileObservation:
    kind: Literal["tail_file"]
    path: str
    ok: bool
    content: str
    message: str
    start_line: int = 1
    line_count: int = 0
    requested_line_count: int = 80
    total_lines: int | None = None
    truncated: bool = False
    max_bytes: int = 20_000


@dataclass(frozen=True)
class ReadFileResult:
    path: str
    ok: bool
    content: str
    message: str
    truncated: bool = False
    total_bytes: int | None = None
    max_bytes: int = 20_000


@dataclass(frozen=True)
class ReadFilesObservation:
    kind: Literal["read_files"]
    files: list[ReadFileResult]
    message: str


@dataclass(frozen=True)
class ReadFileRangeResult:
    path: str
    start_line: int
    line_count: int
    ok: bool
    content: str
    message: str
    truncated: bool
    total_bytes: int | None
    max_bytes: int


@dataclass(frozen=True)
class ReadFileRangesObservation:
    kind: Literal["read_file_ranges"]
    ranges: list[ReadFileRangeResult]
    message: str


@dataclass(frozen=True)
class FileInfoResult:
    path: str
    ok: bool
    exists: bool
    is_file: bool
    is_dir: bool
    size_bytes: int | None
    line_count: int | None
    is_binary: bool | None
    message: str


@dataclass(frozen=True)
class FileInfoObservation:
    kind: Literal["file_info"]
    files: list[FileInfoResult]
    message: str


@dataclass(frozen=True)
class ImageInfoResult:
    path: str
    ok: bool
    exists: bool
    is_file: bool
    size_bytes: int | None
    format: str | None
    mime_type: str | None
    width: int | None
    height: int | None
    message: str


@dataclass(frozen=True)
class ImageInfoObservation:
    kind: Literal["image_info"]
    images: list[ImageInfoResult]
    message: str


@dataclass(frozen=True)
class PythonSymbol:
    name: str
    kind: Literal["class", "function", "async_function", "type", "impl"]
    line: int
    end_line: int | None
    parent: str | None = None


@dataclass(frozen=True)
class PythonSymbolsResult:
    path: str
    ok: bool
    symbols: list[PythonSymbol]
    imports: list[str]
    message: str


@dataclass(frozen=True)
class PythonSymbolsObservation:
    kind: Literal["python_symbols"]
    files: list[PythonSymbolsResult]
    message: str


@dataclass(frozen=True)
class CodeOutlineResult:
    path: str
    ok: bool
    language: str | None
    symbols: list[PythonSymbol]
    imports: list[str]
    message: str


@dataclass(frozen=True)
class CodeOutlineObservation:
    kind: Literal["code_outline"]
    files: list[CodeOutlineResult]
    message: str


@dataclass(frozen=True)
class PythonCheckResult:
    path: str
    ok: bool
    line: int | None
    column: int | None
    message: str


@dataclass(frozen=True)
class PythonCheckObservation:
    kind: Literal["python_check"]
    path: str | None
    files: list[PythonCheckResult]
    total: int
    truncated: bool
    ok: bool
    message: str


@dataclass(frozen=True)
class ConfigCheckResult:
    path: str
    ok: bool
    format: str
    line: int | None
    column: int | None
    message: str


@dataclass(frozen=True)
class ConfigCheckObservation:
    kind: Literal["config_check"]
    path: str | None
    files: list[ConfigCheckResult]
    total: int
    truncated: bool
    ok: bool
    message: str


@dataclass(frozen=True)
class JsonSetObservation:
    kind: Literal["json_set"]
    path: str
    pointer: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckJsonSetObservation:
    kind: Literal["check_json_set"]
    path: str
    pointer: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class JsonRemoveObservation:
    kind: Literal["json_remove"]
    path: str
    pointer: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckJsonRemoveObservation:
    kind: Literal["check_json_remove"]
    path: str
    pointer: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class JsonPatchObservation:
    kind: Literal["json_patch"]
    path: str
    operation_count: int
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckJsonPatchObservation:
    kind: Literal["check_json_patch"]
    path: str
    operation_count: int
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class PythonImportRef:
    line: int
    kind: Literal["import", "from_import"]
    module: str
    name: str | None
    alias: str | None
    target: str
    local: bool


@dataclass(frozen=True)
class PythonDependenciesResult:
    path: str
    ok: bool
    module: str
    imports: list[PythonImportRef]
    local_modules: list[str]
    external_modules: list[str]
    message: str


@dataclass(frozen=True)
class PythonDependenciesObservation:
    kind: Literal["python_dependencies"]
    path: str | None
    files: list[PythonDependenciesResult]
    total: int
    truncated: bool
    ok: bool
    message: str


@dataclass(frozen=True)
class CodeImportRef:
    line: int
    kind: str
    source: str
    raw: str


@dataclass(frozen=True)
class CodeDependenciesResult:
    path: str
    ok: bool
    language: str
    imports: list[CodeImportRef]
    dependencies: list[str]
    message: str


@dataclass(frozen=True)
class CodeDependenciesObservation:
    kind: Literal["code_dependencies"]
    path: str | None
    files: list[CodeDependenciesResult]
    total: int
    truncated: bool
    ok: bool
    message: str


@dataclass(frozen=True)
class CodeReference:
    path: str
    language: str
    line: int
    column: int
    symbol: str
    context: str


@dataclass(frozen=True)
class CodeReferencesObservation:
    kind: Literal["code_references"]
    symbol: str
    path: str | None
    references: list[CodeReference]
    total: int
    truncated: bool
    ok: bool
    message: str


@dataclass(frozen=True)
class ReferenceContextResult:
    path: str
    line: int
    column: int
    symbol: str
    kind: str
    content: str
    context_lines: int
    start_line: int
    end_line: int
    line_count: int
    total_lines: int | None
    truncated: bool
    max_bytes: int
    language: str | None = None
    matched_line: str = ""


@dataclass(frozen=True)
class CodeReferenceContextsObservation:
    kind: Literal["code_reference_contexts"]
    symbol: str
    path: str | None
    contexts: list[ReferenceContextResult]
    total: int
    truncated: bool
    ok: bool
    message: str
    context_lines: int = 3
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class CodeDefinition:
    path: str
    language: str
    name: str
    kind: str
    line: int
    end_line: int
    content: str
    truncated: bool
    message: str


@dataclass(frozen=True)
class CodeDefinitionsObservation:
    kind: Literal["code_definitions"]
    symbol: str
    path: str | None
    definitions: list[CodeDefinition]
    total: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str


@dataclass(frozen=True)
class CodeRenameReplacement:
    path: str
    line: int
    column: int
    end_column: int
    language: str
    old: str
    new: str
    context: str


@dataclass(frozen=True)
class CodeRenamePreviewFile:
    path: str
    language: str
    replacements: list[CodeRenameReplacement]
    diff: str
    truncated: bool


@dataclass(frozen=True)
class CodeRenamePreviewObservation:
    kind: Literal["code_rename_preview"]
    symbol: str
    new_name: str
    path: str | None
    files: list[CodeRenamePreviewFile]
    total_replacements: int
    total_files: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str


@dataclass(frozen=True)
class CodeRenameObservation:
    kind: Literal["code_rename"]
    symbol: str
    new_name: str
    path: str | None
    files: list[CodeRenamePreviewFile]
    total_replacements: int
    total_files: int
    ok: bool
    errors: list[str]
    message: str
    diff: str


@dataclass(frozen=True)
class PythonDefinition:
    path: str
    name: str
    qualified_name: str
    kind: Literal["class", "function", "async_function"]
    line: int
    end_line: int
    parent: str | None
    content: str
    truncated: bool
    message: str


@dataclass(frozen=True)
class PythonDefinitionsObservation:
    kind: Literal["python_definitions"]
    symbol: str
    path: str | None
    definitions: list[PythonDefinition]
    total: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str


@dataclass(frozen=True)
class PythonCall:
    path: str
    line: int
    column: int
    callee: str
    caller: str | None
    context: str


@dataclass(frozen=True)
class PythonCallsObservation:
    kind: Literal["python_calls"]
    symbol: str
    path: str | None
    calls: list[PythonCall]
    total: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str


@dataclass(frozen=True)
class PythonCallGraphObservation:
    kind: Literal["python_call_graph"]
    path: str | None
    edges: list[PythonCall]
    total: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str


@dataclass(frozen=True)
class RepoMapPythonFile:
    path: str
    ok: bool
    imports: list[str]
    symbols: list[PythonSymbol]
    message: str


@dataclass(frozen=True)
class RepoMapObservation:
    kind: Literal["repo_map"]
    path: str
    tree: list[str]
    files: list[str]
    python_files: list[RepoMapPythonFile]
    code_files: list[CodeOutlineResult]
    total_tree_entries: int
    total_files: int
    truncated: bool
    ok: bool
    message: str


@dataclass(frozen=True)
class PythonReference:
    path: str
    line: int
    column: int
    kind: Literal["definition", "import", "reference"]
    context: str


@dataclass(frozen=True)
class PythonReferencesObservation:
    kind: Literal["python_references"]
    symbol: str
    path: str | None
    references: list[PythonReference]
    total: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str


@dataclass(frozen=True)
class PythonReferenceContextsObservation:
    kind: Literal["python_reference_contexts"]
    symbol: str
    path: str | None
    contexts: list[ReferenceContextResult]
    total: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str
    context_lines: int = 3
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class PythonRenameReplacement:
    path: str
    line: int
    column: int
    end_column: int
    kind: str
    old: str
    new: str
    context: str


@dataclass(frozen=True)
class PythonRenamePreviewFile:
    path: str
    replacements: list[PythonRenameReplacement]
    diff: str
    truncated: bool


@dataclass(frozen=True)
class PythonRenamePreviewObservation:
    kind: Literal["python_rename_preview"]
    symbol: str
    new_name: str
    path: str | None
    files: list[PythonRenamePreviewFile]
    total_replacements: int
    total_files: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str


@dataclass(frozen=True)
class PythonRenameObservation:
    kind: Literal["python_rename"]
    symbol: str
    new_name: str
    path: str | None
    files: list[PythonRenamePreviewFile]
    total_replacements: int
    total_files: int
    ok: bool
    errors: list[str]
    message: str
    diff: str


@dataclass(frozen=True)
class SearchObservation:
    kind: Literal["search"]
    ok: bool
    query: str
    matches: list[str]
    total: int
    truncated: bool
    message: str
    path: str | None = None
    regex: bool = False
    case_sensitive: bool = True
    context_lines: int = 0


@dataclass(frozen=True)
class SearchContextResult:
    path: str
    line: int
    matched_line: str
    content: str
    context_lines: int
    start_line: int
    end_line: int
    line_count: int
    total_lines: int | None
    truncated: bool
    max_bytes: int


@dataclass(frozen=True)
class SearchContextsObservation:
    kind: Literal["search_contexts"]
    ok: bool
    query: str
    contexts: list[SearchContextResult]
    total: int
    truncated: bool
    message: str
    path: str | None = None
    regex: bool = False
    case_sensitive: bool = True
    context_lines: int = 3
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class GlobObservation:
    kind: Literal["glob"]
    pattern: str
    matches: list[str]
    total: int
    truncated: bool
    ok: bool
    message: str


@dataclass(frozen=True)
class GitStatusObservation:
    kind: Literal["git_status"]
    ok: bool
    status: str
    message: str


@dataclass(frozen=True)
class GitConflictStatus:
    path: str
    status: str


@dataclass(frozen=True)
class GitConflictMarker:
    path: str
    line: int
    marker: str
    text: str


@dataclass(frozen=True)
class GitConflictsObservation:
    kind: Literal["git_conflicts"]
    ok: bool
    path: str
    unmerged: list[GitConflictStatus]
    unmerged_total: int
    markers: list[GitConflictMarker]
    markers_total: int
    scanned_files: int
    total_files: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class GitRemote:
    name: str
    url: str
    kind: str


@dataclass(frozen=True)
class GitInfoObservation:
    kind: Literal["git_info"]
    ok: bool
    is_git_repo: bool
    branch: str
    head: str
    upstream: str
    ahead: int
    behind: int
    remotes: list[GitRemote]
    status: str
    message: str


@dataclass(frozen=True)
class GitChangeFile:
    path: str
    status: str
    staged: bool
    unstaged: bool
    untracked: bool
    staged_insertions: int
    staged_deletions: int
    unstaged_insertions: int
    unstaged_deletions: int
    binary: bool


@dataclass(frozen=True)
class GitChangesObservation:
    kind: Literal["git_changes"]
    ok: bool
    files: list[GitChangeFile]
    status: str
    message: str


@dataclass(frozen=True)
class GitBranchInfo:
    name: str
    current: bool


@dataclass(frozen=True)
class GitBranchesObservation:
    kind: Literal["git_branches"]
    ok: bool
    current: str
    branches: list[GitBranchInfo]
    total: int
    truncated: bool
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitFetchObservation:
    kind: Literal["check_git_fetch"]
    ok: bool
    remote: str
    remote_url: str
    branch: str
    upstream: str
    ahead: int
    behind: int
    message: str


@dataclass(frozen=True)
class GitFetchObservation:
    kind: Literal["git_fetch"]
    ok: bool
    remote: str
    remote_url: str
    branch: str
    upstream: str
    ahead_before: int
    behind_before: int
    ahead_after: int
    behind_after: int
    message: str


@dataclass(frozen=True)
class CheckGitPullObservation:
    kind: Literal["check_git_pull"]
    ok: bool
    remote: str
    branch: str
    current: str
    upstream: str
    ahead: int
    behind: int
    worktree_clean: bool
    status: str
    message: str


@dataclass(frozen=True)
class GitPullObservation:
    kind: Literal["git_pull"]
    ok: bool
    remote: str
    branch: str
    current_before: str
    current_after: str
    upstream: str
    ahead_before: int
    behind_before: int
    ahead_after: int
    behind_after: int
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitPushObservation:
    kind: Literal["check_git_push"]
    ok: bool
    remote: str
    branch: str
    current: str
    upstream: str
    ahead: int
    behind: int
    worktree_clean: bool
    status: str
    message: str


@dataclass(frozen=True)
class GitPushObservation:
    kind: Literal["git_push"]
    ok: bool
    remote: str
    branch: str
    current: str
    upstream: str
    ahead_before: int
    behind_before: int
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitRestoreObservation:
    kind: Literal["check_git_restore"]
    ok: bool
    paths: list[str]
    diff: str
    status: str
    message: str


@dataclass(frozen=True)
class GitRestoreObservation:
    kind: Literal["git_restore"]
    ok: bool
    paths: list[str]
    diff: str
    status: str
    message: str


@dataclass(frozen=True)
class GitStashEntry:
    name: str
    summary: str


@dataclass(frozen=True)
class GitStashesObservation:
    kind: Literal["git_stashes"]
    ok: bool
    entries: list[GitStashEntry]
    total: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class CheckGitStashObservation:
    kind: Literal["check_git_stash"]
    ok: bool
    message_text: str
    include_untracked: bool
    status: str
    diff: str
    message: str


@dataclass(frozen=True)
class GitStashObservation:
    kind: Literal["git_stash"]
    ok: bool
    message_text: str
    include_untracked: bool
    stash_ref: str
    status: str
    diff: str
    message: str


@dataclass(frozen=True)
class CheckGitStashApplyObservation:
    kind: Literal["check_git_stash_apply"]
    ok: bool
    stash_ref: str
    worktree_clean: bool
    patch: str
    status: str
    message: str


@dataclass(frozen=True)
class GitStashApplyObservation:
    kind: Literal["git_stash_apply"]
    ok: bool
    stash_ref: str
    patch: str
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitStashDropObservation:
    kind: Literal["check_git_stash_drop"]
    ok: bool
    stash_ref: str
    patch: str
    summary: str
    message: str


@dataclass(frozen=True)
class GitStashDropObservation:
    kind: Literal["git_stash_drop"]
    ok: bool
    stash_ref: str
    patch: str
    summary: str
    remaining_total: int
    message: str


@dataclass(frozen=True)
class GitSwitchObservation:
    kind: Literal["git_switch"]
    ok: bool
    branch: str
    create: bool
    current_before: str
    current_after: str
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitSwitchObservation:
    kind: Literal["check_git_switch"]
    ok: bool
    branch: str
    create: bool
    current_before: str
    branch_exists: bool
    worktree_clean: bool
    status: str
    message: str


@dataclass(frozen=True)
class GitStageObservation:
    kind: Literal["git_stage"]
    ok: bool
    paths: list[str]
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitStageObservation:
    kind: Literal["check_git_stage"]
    ok: bool
    paths: list[str]
    status: str
    message: str


@dataclass(frozen=True)
class GitUnstageObservation:
    kind: Literal["git_unstage"]
    ok: bool
    paths: list[str]
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitUnstageObservation:
    kind: Literal["check_git_unstage"]
    ok: bool
    paths: list[str]
    status: str
    message: str


@dataclass(frozen=True)
class GitCommitObservation:
    kind: Literal["git_commit"]
    ok: bool
    head_before: str
    head_after: str
    status: str
    message: str


@dataclass(frozen=True)
class CheckGitCommitObservation:
    kind: Literal["check_git_commit"]
    ok: bool
    head_before: str
    head_after: str
    status: str
    message: str


@dataclass(frozen=True)
class GitDiffHunk:
    file: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    added: int
    deleted: int
    context: int
    header: str
    lines: list[str]
    lines_truncated: bool


@dataclass(frozen=True)
class UntrackedFilePreview:
    path: str
    size_bytes: int
    is_binary: bool
    content: str
    truncated: bool
    message: str


@dataclass(frozen=True)
class ReviewChangesObservation:
    kind: Literal["review_changes"]
    ok: bool
    changes_ok: bool
    diff_check_ok: bool
    staged_diff_check_ok: bool
    python_ok: bool
    config_ok: bool
    files: list[GitChangeFile]
    total_files: int
    python: list[PythonCheckResult]
    python_total: int
    python_truncated: bool
    config: list[ConfigCheckResult]
    config_total: int
    config_truncated: bool
    suggested_checks: list[SuggestedCheck]
    suggested_checks_total: int
    suggested_checks_truncated: bool
    diff_hunks: list[GitDiffHunk]
    diff_hunks_total: int
    diff_hunks_truncated: bool
    staged_diff_hunks: list[GitDiffHunk]
    staged_diff_hunks_total: int
    staged_diff_hunks_truncated: bool
    untracked_previews: list[UntrackedFilePreview]
    untracked_previews_total: int
    untracked_previews_truncated: bool
    diff_check: str
    staged_diff_check: str
    status: str
    message: str


@dataclass(frozen=True)
class FinalReviewObservation:
    kind: Literal["final_review"]
    ok: bool
    ready: bool
    blocking_issues: list[str]
    warnings: list[str]
    running_processes: list[ProcessInfo]
    files: list[GitChangeFile]
    total_files: int
    suggested_checks: list[SuggestedCheck]
    suggested_checks_total: int
    suggested_checks_truncated: bool
    diff_check: str
    staged_diff_check: str
    status: str
    message: str
    python: list[PythonCheckResult] = field(default_factory=list)
    python_total: int = 0
    python_truncated: bool = False
    config: list[ConfigCheckResult] = field(default_factory=list)
    config_total: int = 0
    config_truncated: bool = False


@dataclass(frozen=True)
class SuggestedCheck:
    command: str
    cwd: str
    source: str
    reason: str
    available: bool = True
    missing_tool: str | None = None


@dataclass(frozen=True)
class SuggestChecksObservation:
    kind: Literal["suggest_checks"]
    ok: bool
    checks: list[SuggestedCheck]
    total: int
    truncated: bool
    changed_files: list[str]
    message: str


@dataclass(frozen=True)
class CheckSuggestedChecksObservation:
    kind: Literal["check_suggested_checks"]
    ok: bool
    checks: list[CommandCheckObservation]
    suggested_checks: list[SuggestedCheck]
    total: int
    truncated: bool
    max_commands: int
    message: str


@dataclass(frozen=True)
class RunSuggestedChecksObservation:
    kind: Literal["run_suggested_checks"]
    ok: bool
    results: list[CommandResult]
    suggested_checks: list[SuggestedCheck]
    total: int
    truncated: bool
    max_commands: int
    stopped_early: bool
    skipped_unavailable: int
    message: str


@dataclass(frozen=True)
class ProjectCommand:
    file: str
    cwd: str
    source: str
    command: str
    detail: str
    available: bool
    missing_tool: str | None = None


@dataclass(frozen=True)
class ProjectCommandsObservation:
    kind: Literal["project_commands"]
    ok: bool
    commands: list[ProjectCommand]
    total: int
    truncated: bool
    total_files: int
    scanned_files: int
    message: str


@dataclass(frozen=True)
class RelatedTestCandidate:
    source_path: str
    test_path: str
    score: int
    reason: str


@dataclass(frozen=True)
class RelatedTestsObservation:
    kind: Literal["related_tests"]
    ok: bool
    target_paths: list[str]
    candidates: list[RelatedTestCandidate]
    total: int
    truncated: bool
    test_files_total: int
    message: str


@dataclass(frozen=True)
class FocusedTestCommand:
    command: str
    cwd: str
    test_path: str
    source: str
    reason: str
    available: bool = True
    missing_tool: str | None = None


@dataclass(frozen=True)
class FocusedTestCommandsObservation:
    kind: Literal["focused_test_commands"]
    ok: bool
    target_paths: list[str]
    commands: list[FocusedTestCommand]
    total: int
    truncated: bool
    related_tests_total: int
    message: str


@dataclass(frozen=True)
class CheckFocusedTestCommandsObservation:
    kind: Literal["check_focused_test_commands"]
    ok: bool
    checks: list[CommandCheckObservation]
    focused_commands: list[FocusedTestCommand]
    target_paths: list[str]
    total: int
    truncated: bool
    max_commands: int
    related_tests_total: int
    message: str


@dataclass(frozen=True)
class RunFocusedTestCommandsObservation:
    kind: Literal["run_focused_test_commands"]
    ok: bool
    results: list[CommandResult]
    focused_commands: list[FocusedTestCommand]
    target_paths: list[str]
    total: int
    truncated: bool
    max_commands: int
    related_tests_total: int
    stopped_early: bool
    skipped_unavailable: int
    message: str


@dataclass(frozen=True)
class ProjectManifestItem:
    group: str
    name: str
    value: str


@dataclass(frozen=True)
class ProjectManifest:
    path: str
    kind: str
    ok: bool
    name: str
    version: str
    items: list[ProjectManifestItem]
    item_count: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class ProjectManifestsObservation:
    kind: Literal["project_manifests"]
    ok: bool
    manifests: list[ProjectManifest]
    total_files: int
    scanned_files: int
    total_items: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class ProjectInstructionSource:
    path: str
    scope: str
    bytes: int
    chars: int
    empty: bool
    included: bool
    message: str


@dataclass(frozen=True)
class ProjectInstructionsObservation:
    kind: Literal["project_instructions"]
    ok: bool
    files: list[ProjectInstructionSource]
    total_files: int
    scanned_files: int
    omitted_files: int
    truncated: bool
    text: str
    message: str


@dataclass(frozen=True)
class ProjectTodo:
    path: str
    line: int
    marker: str
    text: str


@dataclass(frozen=True)
class ProjectTodosObservation:
    kind: Literal["project_todos"]
    ok: bool
    todos: list[ProjectTodo]
    total: int
    truncated: bool
    total_files: int
    scanned_files: int
    path: str
    markers: list[str]
    message: str


@dataclass(frozen=True)
class ProjectOverviewObservation:
    kind: Literal["project_overview"]
    ok: bool
    project_root: str
    is_git_repo: bool
    git_branch: str
    git_head: str
    git_upstream: str
    git_ahead: int
    git_behind: int
    git_status: str
    tree: list[str]
    files: list[str]
    total_tree_entries: int
    total_files: int
    repo_truncated: bool
    commands: list[ProjectCommand]
    commands_total: int
    commands_truncated: bool
    manifests: list[ProjectManifest]
    manifest_files_total: int
    manifests_truncated: bool
    suggested_checks: list[SuggestedCheck]
    suggested_checks_total: int
    suggested_checks_truncated: bool
    tools: list[RuntimeToolInfo]
    message: str


@dataclass(frozen=True)
class CommandCheckObservation:
    kind: Literal["command_check"]
    ok: bool
    command: str
    cwd: str
    cwd_ok: bool
    blocked: bool
    block_reason: str | None
    executable_available: bool
    missing_tool: str | None
    message: str


@dataclass(frozen=True)
class CheckStartCommandObservation:
    kind: Literal["check_start_command"]
    ok: bool
    command: str
    cwd: str
    cwd_ok: bool
    blocked: bool
    block_reason: str | None
    executable_available: bool
    missing_tool: str | None
    message: str


@dataclass(frozen=True)
class PortCheckObservation:
    kind: Literal["port_check"]
    ok: bool
    host: str
    port: int
    timeout_ms: int
    reachable: bool
    error: str | None
    message: str


@dataclass(frozen=True)
class HttpCheckObservation:
    kind: Literal["http_check"]
    ok: bool
    url: str
    final_url: str | None
    status: int | None
    reason: str | None
    timeout_ms: int
    reachable: bool
    matched: bool
    matched_pattern: str | None
    body: str
    body_truncated: bool
    max_body_chars: int
    error: str | None
    message: str


@dataclass(frozen=True)
class HttpFetchObservation:
    kind: Literal["http_fetch"]
    ok: bool
    url: str
    final_url: str | None
    status: int | None
    reason: str | None
    content_type: str | None
    timeout_ms: int
    reachable: bool
    body: str
    body_truncated: bool
    max_body_chars: int
    error: str | None
    message: str


@dataclass(frozen=True)
class RuntimeToolInfo:
    name: str
    available: bool
    path: str | None
    version: str | None
    message: str


@dataclass(frozen=True)
class EnvironmentInfoObservation:
    kind: Literal["environment_info"]
    ok: bool
    project_root: str
    python_version: str
    python_executable: str
    platform: str
    is_git_repo: bool
    tools: list[RuntimeToolInfo]
    message: str


@dataclass(frozen=True)
class GitDiffObservation:
    kind: Literal["git_diff"]
    ok: bool
    diff: str
    path: str | None
    staged: bool
    truncated: bool
    max_output_chars: int
    message: str


@dataclass(frozen=True)
class GitDiffHunksObservation:
    kind: Literal["git_diff_hunks"]
    ok: bool
    hunks: list[GitDiffHunk]
    total_hunks: int
    truncated: bool
    path: str | None
    staged: bool
    message: str


@dataclass(frozen=True)
class GitDiffContext:
    hunk: GitDiffHunk
    context: ReadFileContextResult


@dataclass(frozen=True)
class GitDiffContextsObservation:
    kind: Literal["git_diff_contexts"]
    ok: bool
    contexts: list[GitDiffContext]
    total_hunks: int
    truncated: bool
    path: str | None
    staged: bool
    context_lines: int
    message: str


@dataclass(frozen=True)
class GitLogObservation:
    kind: Literal["git_log"]
    ok: bool
    log: str
    max_count: int
    path: str | None
    message: str


@dataclass(frozen=True)
class GitShowObservation:
    kind: Literal["git_show"]
    ok: bool
    output: str
    rev: str
    path: str | None
    truncated: bool
    max_output_chars: int
    message: str


@dataclass(frozen=True)
class GitBlameObservation:
    kind: Literal["git_blame"]
    ok: bool
    blame: str
    path: str
    start_line: int | None
    line_count: int | None
    truncated: bool
    max_output_chars: int
    message: str


@dataclass(frozen=True)
class EditFileObservation:
    kind: Literal["edit_file"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckEditFileObservation:
    kind: Literal["check_edit_file"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class MultiEditObservation:
    kind: Literal["multi_edit_file"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckMultiEditObservation:
    kind: Literal["check_multi_edit_file"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class ReplacePythonDefinitionObservation:
    kind: Literal["replace_python_definition"]
    symbol: str
    path: str | None
    definition_path: str | None
    qualified_name: str | None
    start_line: int | None
    end_line: int | None
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckReplacePythonDefinitionObservation:
    kind: Literal["check_replace_python_definition"]
    symbol: str
    path: str | None
    definition_path: str | None
    qualified_name: str | None
    start_line: int | None
    end_line: int | None
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class ReplaceLinesObservation:
    kind: Literal["replace_lines"]
    path: str
    start_line: int
    end_line: int
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckReplaceLinesObservation:
    kind: Literal["check_replace_lines"]
    path: str
    start_line: int
    end_line: int
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class InsertLinesObservation:
    kind: Literal["insert_lines"]
    path: str
    line: int
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckInsertLinesObservation:
    kind: Literal["check_insert_lines"]
    path: str
    line: int
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class AppendFileObservation:
    kind: Literal["append_file"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckAppendFileObservation:
    kind: Literal["check_append_file"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class RegexReplaceObservation:
    kind: Literal["regex_replace"]
    path: str
    pattern: str
    count: int
    replacements: int
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckRegexReplaceObservation:
    kind: Literal["check_regex_replace"]
    path: str
    pattern: str
    count: int
    replacements: int
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckPatchObservation:
    kind: Literal["check_patch"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckPatchesObservation:
    kind: Literal["check_patches"]
    files: list[str]
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class PatchFileObservation:
    kind: Literal["patch_file"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class PatchFilesObservation:
    kind: Literal["patch_files"]
    files: list[str]
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class DeleteFileObservation:
    kind: Literal["delete_file"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckDeleteFileObservation:
    kind: Literal["check_delete_file"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class DeleteFilesObservation:
    kind: Literal["delete_files"]
    paths: list[str]
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckDeleteFilesObservation:
    kind: Literal["check_delete_files"]
    paths: list[str]
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class MoveFileObservation:
    kind: Literal["move_file"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckMoveFileObservation:
    kind: Literal["check_move_file"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class MoveFilesObservation:
    kind: Literal["move_files"]
    transfers: list[MoveFileTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckMoveFilesObservation:
    kind: Literal["check_move_files"]
    transfers: list[MoveFileTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class CopyFileObservation:
    kind: Literal["copy_file"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckCopyFileObservation:
    kind: Literal["check_copy_file"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CopyFilesObservation:
    kind: Literal["copy_files"]
    transfers: list[MoveFileTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckCopyFilesObservation:
    kind: Literal["check_copy_files"]
    transfers: list[MoveFileTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class MoveDirectoryObservation:
    kind: Literal["move_dir"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckMoveDirectoryObservation:
    kind: Literal["check_move_dir"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class MoveDirectoriesObservation:
    kind: Literal["move_dirs"]
    transfers: list[DirectoryTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckMoveDirectoriesObservation:
    kind: Literal["check_move_dirs"]
    transfers: list[DirectoryTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class CopyDirectoryObservation:
    kind: Literal["copy_dir"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckCopyDirectoryObservation:
    kind: Literal["check_copy_dir"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CopyDirectoriesObservation:
    kind: Literal["copy_dirs"]
    transfers: list[DirectoryTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckCopyDirectoriesObservation:
    kind: Literal["check_copy_dirs"]
    transfers: list[DirectoryTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class CreateDirectoryObservation:
    kind: Literal["create_dir"]
    path: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckCreateDirectoryObservation:
    kind: Literal["check_create_dir"]
    path: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CreateDirectoriesObservation:
    kind: Literal["create_dirs"]
    paths: list[str]
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckCreateDirectoriesObservation:
    kind: Literal["check_create_dirs"]
    paths: list[str]
    ok: bool
    message: str


@dataclass(frozen=True)
class DeleteEmptyDirectoryObservation:
    kind: Literal["delete_empty_dir"]
    path: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckDeleteEmptyDirectoryObservation:
    kind: Literal["check_delete_empty_dir"]
    path: str
    ok: bool
    message: str


@dataclass(frozen=True)
class DeleteEmptyDirectoriesObservation:
    kind: Literal["delete_empty_dirs"]
    paths: list[str]
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckDeleteEmptyDirectoriesObservation:
    kind: Literal["check_delete_empty_dirs"]
    paths: list[str]
    ok: bool
    message: str


@dataclass(frozen=True)
class SetExecutableObservation:
    kind: Literal["set_executable"]
    path: str
    executable: bool
    ok: bool
    mode_before: str
    mode_after: str
    message: str


@dataclass(frozen=True)
class CheckSetExecutableObservation:
    kind: Literal["check_set_executable"]
    path: str
    executable: bool
    ok: bool
    mode_before: str
    mode_after: str
    message: str


@dataclass(frozen=True)
class SessionSummaryObservation:
    kind: Literal["session_summary"]
    run_id: str
    ok: bool
    summary: str
    recent_sessions: list[str]
    message: str


@dataclass(frozen=True)
class SessionPlanObservation:
    kind: Literal["session_plan"]
    run_id: str
    ok: bool
    plan: str
    message: str


@dataclass(frozen=True)
class SessionTranscriptObservation:
    kind: Literal["session_transcript"]
    run_id: str
    ok: bool
    transcript: str
    message: str


@dataclass(frozen=True)
class SessionSearchObservation:
    kind: Literal["session_search"]
    run_id: str
    ok: bool
    query: str
    matches: str
    total_matches: int
    shown_matches: int
    message: str


@dataclass(frozen=True)
class SessionCommandsObservation:
    kind: Literal["session_commands"]
    run_id: str
    ok: bool
    commands: str
    command_count: int
    shown_commands: int
    message: str


@dataclass(frozen=True)
class SessionOutputContextsObservation:
    kind: Literal["session_output_contexts"]
    run_id: str
    ok: bool
    contexts: list[OutputContextResult]
    command_count: int
    shown_commands: int
    total_refs: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class SessionOutputDiagnosticsObservation:
    kind: Literal["session_output_diagnostics"]
    run_id: str
    ok: bool
    diagnostics: list[OutputDiagnostic]
    contexts: list[OutputContextResult]
    command_count: int
    shown_commands: int
    total_diagnostics: int
    total_refs: int
    diagnostics_truncated: bool
    contexts_truncated: bool
    message: str


@dataclass(frozen=True)
class SessionFilesObservation:
    kind: Literal["session_files"]
    run_id: str
    ok: bool
    files: str
    file_count: int
    shown_files: int
    message: str


@dataclass(frozen=True)
class SessionFailuresObservation:
    kind: Literal["session_failures"]
    run_id: str
    ok: bool
    failures: str
    failure_count: int
    shown_failures: int
    message: str


@dataclass(frozen=True)
class SessionVerificationObservation:
    kind: Literal["session_verification"]
    run_id: str
    ok: bool
    verification: str
    message: str


@dataclass(frozen=True)
class SessionAuditProcess:
    process_id: str
    pid: int | None
    command: str
    cwd: str
    line_number: int


@dataclass(frozen=True)
class SessionAuditObservation:
    kind: Literal["session_audit"]
    run_id: str
    ok: bool
    audit: str
    ready: bool
    blockers: list[str]
    background_processes_started: int
    active_background_processes: list[SessionAuditProcess]
    message: str


@dataclass(frozen=True)
class SessionHandoffObservation:
    kind: Literal["session_handoff"]
    run_id: str
    ok: bool
    handoff: str
    message: str


@dataclass(frozen=True)
class CheckpointInfo:
    checkpoint_id: str
    label: str
    created_at: str
    head: str
    changed_files: int
    staged_files: int
    unstaged_files: int
    untracked_files: int


@dataclass(frozen=True)
class CheckpointCreateObservation:
    kind: Literal["checkpoint_create"]
    ok: bool
    checkpoint: CheckpointInfo | None
    staged_patch_chars: int
    unstaged_patch_chars: int
    message: str


@dataclass(frozen=True)
class CheckpointListObservation:
    kind: Literal["checkpoint_list"]
    ok: bool
    checkpoints: list[CheckpointInfo]
    total: int
    message: str


@dataclass(frozen=True)
class CheckpointShowObservation:
    kind: Literal["checkpoint_show"]
    ok: bool
    checkpoint: CheckpointInfo | None
    project_root: str
    git_status: str
    untracked_saved_files: int
    untracked_skipped_files: int
    saved_untracked_paths: list[str]
    saved_untracked_paths_truncated: bool
    staged_patch_chars: int
    unstaged_patch_chars: int
    message: str


@dataclass(frozen=True)
class CheckpointDiffObservation:
    kind: Literal["checkpoint_diff"]
    ok: bool
    checkpoint_id: str
    label: str
    created_at: str
    staged_patch: str
    staged_patch_chars: int
    staged_patch_truncated: bool
    unstaged_patch: str
    unstaged_patch_chars: int
    unstaged_patch_truncated: bool
    max_chars: int
    message: str


@dataclass(frozen=True)
class CheckpointStatusObservation:
    kind: Literal["checkpoint_status"]
    ok: bool
    checkpoint_id: str
    matches: bool
    status_matches: bool
    staged_patch_matches: bool
    unstaged_patch_matches: bool
    untracked_file_matches: bool
    saved_changed_files: int
    saved_staged_files: int
    saved_unstaged_files: int
    saved_untracked_files: int
    current_changed_files: int
    current_staged_files: int
    current_unstaged_files: int
    current_untracked_files: int
    message: str


@dataclass(frozen=True)
class CheckCheckpointRestoreObservation:
    kind: Literal["check_checkpoint_restore"]
    ok: bool
    checkpoint_id: str
    can_restore: bool
    saved_head: str
    current_head: str
    saved_untracked_files: int
    current_untracked_files: int
    staged_patch_chars: int
    unstaged_patch_chars: int
    message: str


@dataclass(frozen=True)
class CheckpointRestoreObservation:
    kind: Literal["checkpoint_restore"]
    ok: bool
    checkpoint_id: str
    restored: bool
    matches: bool
    saved_head: str
    current_head: str
    saved_untracked_files: int
    current_untracked_files: int
    staged_patch_chars: int
    unstaged_patch_chars: int
    message: str


@dataclass(frozen=True)
class CheckCheckpointDeleteObservation:
    kind: Literal["check_checkpoint_delete"]
    ok: bool
    checkpoint_id: str
    can_delete: bool
    label: str
    created_at: str
    message: str


@dataclass(frozen=True)
class CheckpointDeleteObservation:
    kind: Literal["checkpoint_delete"]
    ok: bool
    checkpoint_id: str
    deleted: bool
    message: str


@dataclass(frozen=True)
class CheckCheckpointPruneObservation:
    kind: Literal["check_checkpoint_prune"]
    ok: bool
    keep_last: int
    total: int
    kept: int
    delete_count: int
    checkpoints: list[CheckpointInfo]
    message: str


@dataclass(frozen=True)
class CheckpointPruneObservation:
    kind: Literal["checkpoint_prune"]
    ok: bool
    keep_last: int
    total: int
    kept: int
    deleted: int
    checkpoints: list[CheckpointInfo]
    message: str


@dataclass(frozen=True)
class FinishObservation:
    kind: Literal["finish"]
    message: str


@dataclass(frozen=True)
class UpdatePlanObservation:
    kind: Literal["update_plan"]
    plan: list[PlanItem] = field(default_factory=list)
    message: str = "Plan updated."


@dataclass(frozen=True)
class ToolErrorObservation:
    kind: Literal["tool_error"]
    tool: str
    message: str


@dataclass(frozen=True)
class ApprovalDeniedObservation:
    kind: Literal["approval_denied"]
    action_type: str
    target: str
    message: str


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

ApprovalHandler: TypeAlias = Callable[[ApprovalRequest], ApprovalDecision]

# Status tokens are constrained to keep logger and callers consistent.
AgentStatus: TypeAlias = Literal[
    "thinking",
    "listing files",
    "listing tree",
    "mapping repo",
    "reading file",
    "reading files",
    "reading file ranges",
    "reading file info",
    "reading python symbols",
    "reading code outline",
    "checking python",
    "checking config",
    "checking json set",
    "setting json",
    "checking json remove",
    "removing json",
    "checking json patch",
    "patching json",
    "reading python dependencies",
    "reading python definitions",
    "reading python calls",
    "reading python call graph",
    "reading python references",
    "previewing python rename",
    "renaming python symbol",
    "searching",
    "globbing",
    "checking git status",
    "reading git branches",
    "checking git fetch",
    "fetching git remote",
    "checking git pull",
    "pulling git upstream",
    "checking git push",
    "pushing git upstream",
    "checking git restore",
    "restoring git paths",
    "reading git stashes",
    "checking git stash",
    "stashing git changes",
    "checking git stash apply",
    "applying git stash",
    "checking git stash drop",
    "dropping git stash",
    "checking git switch",
    "switching git branch",
    "reading git changes",
    "reviewing changes",
    "final reviewing changes",
    "suggesting checks",
    "reading project overview",
    "checking command",
    "checking commands",
    "checking http",
    "reading environment info",
    "reading git diff",
    "reading git log",
    "reading git show",
    "reading git blame",
    "reading session summary",
    "editing file",
    "multi-editing file",
    "replacing python definition",
    "replacing lines",
    "inserting lines",
    "checking patch",
    "checking patches",
    "patching file",
    "patching files",
    "deleting file",
    "checking file deletes",
    "deleting files",
    "moving file",
    "checking file moves",
    "moving files",
    "checking file copies",
    "copying files",
    "checking directory moves",
    "moving directories",
    "checking directory copies",
    "copying directories",
    "checking directory creates",
    "creating directories",
    "checking empty directory deletes",
    "deleting empty directories",
    "writing file",
    "writing files",
    "running command",
    "running commands",
    "starting command",
    "reading process",
    "waiting process",
    "checking process write",
    "writing process",
    "listing processes",
    "stopping process",
    "updating plan",
    "step started",
    "step completed",
    "approval required",
    "approval approved",
    "approval denied",
    "observed success",
    "observed failure",
    "finished",
]

# Logger receives a status plus optional detail for each agent transition.
AgentLogger: TypeAlias = Callable[[AgentStatus, str | None], None]
