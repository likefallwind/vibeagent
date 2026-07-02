from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .observation_process_types import CommandCheckObservation, CommandResult
from .observation_runtime_types import RuntimeToolInfo


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
