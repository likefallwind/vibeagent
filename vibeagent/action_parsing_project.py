from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_nonnegative_int, parse_optional_positive_int
from .types import (
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


PROJECT_ACTION_TYPES = {
    "review_changes",
    "final_review",
    "suggest_checks",
    "check_suggested_checks",
    "run_suggested_checks",
    "project_commands",
    "related_tests",
    "focused_test_commands",
    "check_focused_test_commands",
    "run_focused_test_commands",
    "project_manifests",
    "project_instructions",
    "project_todos",
    "project_overview",
}


def _parse_optional_paths(value: Any, raw: str, action_type: str) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ActionParseError(f"{action_type} action paths must be a list of non-empty strings when provided.", raw)
    return [item.strip() for item in value]


def _parse_output_extraction_options(
    value: dict[str, Any],
    raw: str,
    action_type: str,
) -> tuple[bool, bool, int, int, int]:
    extract_output_contexts = value.get("extract_output_contexts", False)
    if not isinstance(extract_output_contexts, bool):
        raise ActionParseError(f"{action_type} action extract_output_contexts must be a boolean.", raw)
    extract_output_diagnostics = value.get("extract_output_diagnostics", False)
    if not isinstance(extract_output_diagnostics, bool):
        raise ActionParseError(f"{action_type} action extract_output_diagnostics must be a boolean.", raw)
    context_lines = parse_nonnegative_int(value.get("context_lines", 5), "context_lines", raw, maximum=500)
    max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
    max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
    return extract_output_contexts, extract_output_diagnostics, context_lines, max_diagnostics, max_contexts


def _parse_run_limits(value: dict[str, Any], raw: str, action_type: str) -> tuple[int | None, int | None, bool]:
    timeout_ms = parse_optional_positive_int(value.get("timeout_ms"), "timeout_ms", raw, maximum=600_000)
    if timeout_ms is not None and timeout_ms < 100:
        raise ActionParseError("timeout_ms must be at least 100.", raw)
    max_output_chars = parse_optional_positive_int(value.get("max_output_chars"), "max_output_chars", raw, maximum=50_000)
    if max_output_chars is not None and max_output_chars < 1_000:
        raise ActionParseError("max_output_chars must be at least 1000.", raw)
    stop_on_failure = value.get("stop_on_failure", True)
    if not isinstance(stop_on_failure, bool):
        raise ActionParseError(f"{action_type} action stop_on_failure must be a boolean when provided.", raw)
    return timeout_ms, max_output_chars, stop_on_failure


def _parse_max_bytes_per_context(value: dict[str, Any], raw: str) -> int:
    max_bytes_per_context = parse_optional_positive_int(
        value.get("max_bytes_per_context", 20_000),
        "max_bytes_per_context",
        raw,
        maximum=200_000,
    ) or 20_000
    if max_bytes_per_context < 1_000:
        raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
    return max_bytes_per_context


def parse_project_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in PROJECT_ACTION_TYPES:
        return None

    if action_type == "review_changes":
        max_files = parse_optional_positive_int(value.get("max_files", 200), "max_files", raw, maximum=500) or 200
        return ReviewChangesAction(type="review_changes", max_files=max_files)

    if action_type == "final_review":
        max_files = parse_optional_positive_int(value.get("max_files", 200), "max_files", raw, maximum=500) or 200
        max_checks = parse_optional_positive_int(value.get("max_checks", 10), "max_checks", raw, maximum=50) or 10
        return FinalReviewAction(type="final_review", max_files=max_files, max_checks=max_checks)

    if action_type == "suggest_checks":
        max_commands = parse_optional_positive_int(value.get("max_commands", 20), "max_commands", raw, maximum=100) or 20
        return SuggestChecksAction(type="suggest_checks", max_commands=max_commands)

    if action_type == "check_suggested_checks":
        max_commands = parse_optional_positive_int(value.get("max_commands", 10), "max_commands", raw, maximum=10) or 10
        return CheckSuggestedChecksAction(type="check_suggested_checks", max_commands=max_commands)

    if action_type == "run_suggested_checks":
        max_commands = parse_optional_positive_int(value.get("max_commands", 10), "max_commands", raw, maximum=10) or 10
        timeout_ms, max_output_chars, stop_on_failure = _parse_run_limits(value, raw, "run_suggested_checks")
        (
            extract_output_contexts,
            extract_output_diagnostics,
            context_lines,
            max_diagnostics,
            max_contexts,
        ) = _parse_output_extraction_options(value, raw, "run_suggested_checks")
        return RunSuggestedChecksAction(
            type="run_suggested_checks",
            max_commands=max_commands,
            timeout_ms=timeout_ms,
            max_output_chars=max_output_chars,
            stop_on_failure=stop_on_failure,
            extract_output_contexts=extract_output_contexts,
            extract_output_diagnostics=extract_output_diagnostics,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=_parse_max_bytes_per_context(value, raw),
        )

    if action_type == "project_commands":
        max_commands = parse_optional_positive_int(value.get("max_commands", 100), "max_commands", raw, maximum=500) or 100
        max_files = parse_optional_positive_int(value.get("max_files", 30), "max_files", raw, maximum=200) or 30
        return ProjectCommandsAction(type="project_commands", max_commands=max_commands, max_files=max_files)

    if action_type == "related_tests":
        max_paths = parse_optional_positive_int(value.get("max_paths", 100), "max_paths", raw, maximum=500) or 100
        max_candidates = parse_optional_positive_int(value.get("max_candidates", 200), "max_candidates", raw, maximum=1000) or 200
        return RelatedTestsAction(
            type="related_tests",
            paths=_parse_optional_paths(value.get("paths"), raw, "related_tests"),
            max_paths=max_paths,
            max_candidates=max_candidates,
        )

    if action_type == "focused_test_commands":
        max_paths = parse_optional_positive_int(value.get("max_paths", 100), "max_paths", raw, maximum=500) or 100
        max_candidates = parse_optional_positive_int(value.get("max_candidates", 200), "max_candidates", raw, maximum=1000) or 200
        max_commands = parse_optional_positive_int(value.get("max_commands", 50), "max_commands", raw, maximum=500) or 50
        return FocusedTestCommandsAction(
            type="focused_test_commands",
            paths=_parse_optional_paths(value.get("paths"), raw, "focused_test_commands"),
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
        )

    if action_type == "check_focused_test_commands":
        max_paths = parse_optional_positive_int(value.get("max_paths", 100), "max_paths", raw, maximum=500) or 100
        max_candidates = parse_optional_positive_int(value.get("max_candidates", 200), "max_candidates", raw, maximum=1000) or 200
        max_commands = parse_optional_positive_int(value.get("max_commands", 10), "max_commands", raw, maximum=50) or 10
        return CheckFocusedTestCommandsAction(
            type="check_focused_test_commands",
            paths=_parse_optional_paths(value.get("paths"), raw, "check_focused_test_commands"),
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
        )

    if action_type == "run_focused_test_commands":
        max_paths = parse_optional_positive_int(value.get("max_paths", 100), "max_paths", raw, maximum=500) or 100
        max_candidates = parse_optional_positive_int(value.get("max_candidates", 200), "max_candidates", raw, maximum=1000) or 200
        max_commands = parse_optional_positive_int(value.get("max_commands", 10), "max_commands", raw, maximum=50) or 10
        timeout_ms, max_output_chars, stop_on_failure = _parse_run_limits(value, raw, "run_focused_test_commands")
        (
            extract_output_contexts,
            extract_output_diagnostics,
            context_lines,
            max_diagnostics,
            max_contexts,
        ) = _parse_output_extraction_options(value, raw, "run_focused_test_commands")
        return RunFocusedTestCommandsAction(
            type="run_focused_test_commands",
            paths=_parse_optional_paths(value.get("paths"), raw, "run_focused_test_commands"),
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
            timeout_ms=timeout_ms,
            max_output_chars=max_output_chars,
            stop_on_failure=stop_on_failure,
            extract_output_contexts=extract_output_contexts,
            extract_output_diagnostics=extract_output_diagnostics,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=_parse_max_bytes_per_context(value, raw),
        )

    if action_type == "project_manifests":
        max_files = parse_optional_positive_int(value.get("max_files", 30), "max_files", raw, maximum=200) or 30
        max_items = parse_optional_positive_int(value.get("max_items", 500), "max_items", raw, maximum=2000) or 500
        return ProjectManifestsAction(type="project_manifests", max_files=max_files, max_items=max_items)

    if action_type == "project_instructions":
        max_files = parse_optional_positive_int(value.get("max_files", 20), "max_files", raw, maximum=200) or 20
        max_bytes = parse_optional_positive_int(value.get("max_bytes", 12_000), "max_bytes", raw, maximum=50_000) or 12_000
        if max_bytes < 200:
            raise ActionParseError("max_bytes must be at least 200.", raw)
        return ProjectInstructionsAction(type="project_instructions", max_files=max_files, max_bytes=max_bytes)

    if action_type == "project_todos":
        path = value.get("path")
        if path is not None and not isinstance(path, str):
            raise ActionParseError("project_todos action path must be a string when provided.", raw)
        max_items = parse_optional_positive_int(value.get("max_items", 100), "max_items", raw, maximum=500) or 100
        max_files = parse_optional_positive_int(value.get("max_files", 1000), "max_files", raw, maximum=5000) or 1000
        return ProjectTodosAction(
            type="project_todos",
            path=path.strip() if isinstance(path, str) and path.strip() else None,
            max_items=max_items,
            max_files=max_files,
        )

    if action_type == "project_overview":
        max_files = parse_optional_positive_int(value.get("max_files", 80), "max_files", raw, maximum=200) or 80
        max_commands = parse_optional_positive_int(value.get("max_commands", 20), "max_commands", raw, maximum=100) or 20
        max_checks = parse_optional_positive_int(value.get("max_checks", 10), "max_checks", raw, maximum=50) or 10
        max_manifests = parse_optional_positive_int(value.get("max_manifests", 10), "max_manifests", raw, maximum=50) or 10
        return ProjectOverviewAction(
            type="project_overview",
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_manifests=max_manifests,
        )

    raise AssertionError(f"Unhandled project action type: {action_type!r}")
