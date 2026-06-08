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
class AssistantResponse:
    # Provider-neutral blocks:
    # - {"type": "text", "text": "..."}
    # - {"type": "tool_call", "id": "...", "name": "...", "input": {...}}
    content: list[ContentBlock]
    raw: dict[str, Any]


class ChatClient(Protocol):
    # Protocol so MiniMaxClient and any future providers can plug into the same agent loop.
    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> AssistantResponse:
        ...


@dataclass(frozen=True)
class WriteFileAction:
    type: Literal["write_file"]
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


@dataclass(frozen=True)
class ReadFilesAction:
    type: Literal["read_files"]
    paths: list[str]


@dataclass(frozen=True)
class ReadFileRangeItem:
    path: str
    start_line: int
    line_count: int = 120


@dataclass(frozen=True)
class ReadFileRangesAction:
    type: Literal["read_file_ranges"]
    ranges: list[ReadFileRangeItem]


@dataclass(frozen=True)
class FileInfoAction:
    type: Literal["file_info"]
    paths: list[str]


@dataclass(frozen=True)
class PythonSymbolsAction:
    type: Literal["python_symbols"]
    paths: list[str]


@dataclass(frozen=True)
class PythonCheckAction:
    type: Literal["python_check"]
    path: str | None = None
    max_files: int = 200


@dataclass(frozen=True)
class PythonDependenciesAction:
    type: Literal["python_dependencies"]
    path: str | None = None
    max_files: int = 100
    max_imports: int = 500


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
class SearchAction:
    type: Literal["search"]
    query: str
    path: str | None = None
    regex: bool = False
    case_sensitive: bool = True
    max_matches: int = 80
    context_lines: int = 0


@dataclass(frozen=True)
class GlobAction:
    type: Literal["glob"]
    pattern: str
    max_matches: int = 200


@dataclass(frozen=True)
class GitStatusAction:
    type: Literal["git_status"]


@dataclass(frozen=True)
class GitChangesAction:
    type: Literal["git_changes"]


@dataclass(frozen=True)
class ReviewChangesAction:
    type: Literal["review_changes"]
    max_files: int = 200


@dataclass(frozen=True)
class SuggestChecksAction:
    type: Literal["suggest_checks"]
    max_commands: int = 20


@dataclass(frozen=True)
class GitDiffAction:
    type: Literal["git_diff"]
    path: str | None = None
    staged: bool = False
    max_output_chars: int = 12000


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
class EditFileAction:
    type: Literal["edit_file"]
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
class ReplaceLinesAction:
    type: Literal["replace_lines"]
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
class MoveFileAction:
    type: Literal["move_file"]
    source: str
    destination: str


@dataclass(frozen=True)
class RunCommandAction:
    type: Literal["run_command"]
    command: str
    timeout_ms: int | None = None
    cwd: str | None = None
    max_output_chars: int | None = None


@dataclass(frozen=True)
class StartCommandAction:
    type: Literal["start_command"]
    command: str
    cwd: str | None = None


@dataclass(frozen=True)
class ReadProcessAction:
    type: Literal["read_process"]
    process_id: str


@dataclass(frozen=True)
class ListProcessesAction:
    type: Literal["list_processes"]


@dataclass(frozen=True)
class StopProcessAction:
    type: Literal["stop_process"]
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
    WriteFileAction
    | WriteFilesAction
    | ListFilesAction
    | ListTreeAction
    | RepoMapAction
    | ReadFileAction
    | ReadFilesAction
    | ReadFileRangesAction
    | FileInfoAction
    | PythonSymbolsAction
    | PythonCheckAction
    | PythonDependenciesAction
    | PythonDefinitionsAction
    | ReplacePythonDefinitionAction
    | PythonCallsAction
    | PythonCallGraphAction
    | PythonReferencesAction
    | SearchAction
    | GlobAction
    | GitStatusAction
    | GitChangesAction
    | ReviewChangesAction
    | SuggestChecksAction
    | GitDiffAction
    | GitLogAction
    | GitShowAction
    | GitBlameAction
    | SessionSummaryAction
    | EditFileAction
    | MultiEditAction
    | ReplaceLinesAction
    | InsertLinesAction
    | CheckPatchAction
    | CheckPatchesAction
    | PatchFileAction
    | PatchFilesAction
    | DeleteFileAction
    | MoveFileAction
    | RunCommandAction
    | StartCommandAction
    | ReadProcessAction
    | ListProcessesAction
    | StopProcessAction
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
        "patch_file",
        "patch_files",
        "delete_file",
        "move_file",
        "run_command",
        "start_command",
    ]
    target: str
    risk: str


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
class WriteFileResult:
    path: str
    ok: bool
    message: str


@dataclass(frozen=True)
class WriteFilesObservation:
    kind: Literal["write_files"]
    files: list[WriteFileResult]
    ok: bool
    message: str


@dataclass(frozen=True)
class RunCommandObservation:
    kind: Literal["run_command"]
    result: CommandResult


@dataclass(frozen=True)
class StartCommandObservation:
    kind: Literal["start_command"]
    process_id: str
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
    ok: bool
    running: bool
    exit_code: int | None
    signal: str | None
    stdout: str
    stderr: str
    message: str


@dataclass(frozen=True)
class ProcessInfo:
    process_id: str
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
class StopProcessObservation:
    kind: Literal["stop_process"]
    process_id: str
    ok: bool
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


@dataclass(frozen=True)
class ReadFileResult:
    path: str
    ok: bool
    content: str
    message: str


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
class PythonSymbol:
    name: str
    kind: Literal["class", "function", "async_function"]
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
class SearchObservation:
    kind: Literal["search"]
    query: str
    matches: list[str]
    message: str
    path: str | None = None
    regex: bool = False
    case_sensitive: bool = True
    context_lines: int = 0


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
class ReviewChangesObservation:
    kind: Literal["review_changes"]
    ok: bool
    changes_ok: bool
    diff_check_ok: bool
    staged_diff_check_ok: bool
    python_ok: bool
    files: list[GitChangeFile]
    total_files: int
    python: list[PythonCheckResult]
    python_total: int
    python_truncated: bool
    diff_check: str
    staged_diff_check: str
    status: str
    message: str


@dataclass(frozen=True)
class SuggestedCheck:
    command: str
    cwd: str
    source: str
    reason: str


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
class MultiEditObservation:
    kind: Literal["multi_edit_file"]
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
class ReplaceLinesObservation:
    kind: Literal["replace_lines"]
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
class MoveFileObservation:
    kind: Literal["move_file"]
    source: str
    destination: str
    ok: bool
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
    WriteFileObservation
    | WriteFilesObservation
    | ListFilesObservation
    | ListTreeObservation
    | RepoMapObservation
    | ReadFileObservation
    | ReadFilesObservation
    | ReadFileRangesObservation
    | FileInfoObservation
    | PythonSymbolsObservation
    | PythonCheckObservation
    | PythonDependenciesObservation
    | PythonDefinitionsObservation
    | PythonCallsObservation
    | PythonCallGraphObservation
    | PythonReferencesObservation
    | SearchObservation
    | GlobObservation
    | GitStatusObservation
    | GitChangesObservation
    | ReviewChangesObservation
    | SuggestChecksObservation
    | GitDiffObservation
    | GitLogObservation
    | GitShowObservation
    | GitBlameObservation
    | SessionSummaryObservation
    | EditFileObservation
    | MultiEditObservation
    | ReplacePythonDefinitionObservation
    | ReplaceLinesObservation
    | InsertLinesObservation
    | CheckPatchObservation
    | CheckPatchesObservation
    | PatchFileObservation
    | PatchFilesObservation
    | DeleteFileObservation
    | MoveFileObservation
    | RunCommandObservation
    | StartCommandObservation
    | ReadProcessObservation
    | ListProcessesObservation
    | StopProcessObservation
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
    "checking python",
    "reading python dependencies",
    "reading python definitions",
    "reading python calls",
    "reading python call graph",
    "reading python references",
    "searching",
    "globbing",
    "checking git status",
    "reading git changes",
    "reviewing changes",
    "suggesting checks",
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
    "moving file",
    "writing file",
    "writing files",
    "running command",
    "starting command",
    "reading process",
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
