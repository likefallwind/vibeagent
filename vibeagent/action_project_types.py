from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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
