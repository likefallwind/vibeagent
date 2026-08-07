from __future__ import annotations

from typing import Any

from .action_parsing_helpers import parse_optional_positive_int
from .action_parsing_project_fields import (
    parse_max_bytes_per_context,
    parse_optional_paths,
    parse_output_extraction_options,
    parse_run_limits,
)
from .types import (
    CheckFocusedTestCommandsAction,
    CheckSuggestedChecksAction,
    FocusedTestCommandsAction,
    RelatedTestsAction,
    RunFocusedTestCommandsAction,
    RunSuggestedChecksAction,
    SuggestChecksAction,
)


PROJECT_TEST_ACTION_TYPES = {
    "suggest_checks",
    "check_suggested_checks",
    "run_suggested_checks",
    "related_tests",
    "focused_test_commands",
    "check_focused_test_commands",
    "run_focused_test_commands",
}


def parse_project_test_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type == "suggest_checks":
        max_commands = parse_optional_positive_int(value.get("max_commands", 20), "max_commands", raw, maximum=100) or 20
        return SuggestChecksAction(type="suggest_checks", max_commands=max_commands)

    if action_type == "check_suggested_checks":
        max_commands = parse_optional_positive_int(value.get("max_commands", 10), "max_commands", raw, maximum=10) or 10
        return CheckSuggestedChecksAction(type="check_suggested_checks", max_commands=max_commands)

    if action_type == "run_suggested_checks":
        max_commands = parse_optional_positive_int(value.get("max_commands", 10), "max_commands", raw, maximum=10) or 10
        timeout_ms, max_output_chars, stop_on_failure = parse_run_limits(value, raw, "run_suggested_checks")
        (
            extract_output_contexts,
            extract_output_diagnostics,
            context_lines,
            max_diagnostics,
            max_contexts,
        ) = parse_output_extraction_options(value, raw, "run_suggested_checks")
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
            max_bytes_per_context=parse_max_bytes_per_context(value, raw),
        )

    if action_type == "related_tests":
        max_paths = parse_optional_positive_int(value.get("max_paths", 100), "max_paths", raw, maximum=500) or 100
        max_candidates = parse_optional_positive_int(value.get("max_candidates", 200), "max_candidates", raw, maximum=1000) or 200
        return RelatedTestsAction(
            type="related_tests",
            paths=parse_optional_paths(value.get("paths"), raw, "related_tests"),
            max_paths=max_paths,
            max_candidates=max_candidates,
        )

    if action_type == "focused_test_commands":
        max_paths = parse_optional_positive_int(value.get("max_paths", 100), "max_paths", raw, maximum=500) or 100
        max_candidates = parse_optional_positive_int(value.get("max_candidates", 200), "max_candidates", raw, maximum=1000) or 200
        max_commands = parse_optional_positive_int(value.get("max_commands", 50), "max_commands", raw, maximum=500) or 50
        return FocusedTestCommandsAction(
            type="focused_test_commands",
            paths=parse_optional_paths(value.get("paths"), raw, "focused_test_commands"),
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
            paths=parse_optional_paths(value.get("paths"), raw, "check_focused_test_commands"),
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
        )

    if action_type == "run_focused_test_commands":
        max_paths = parse_optional_positive_int(value.get("max_paths", 100), "max_paths", raw, maximum=500) or 100
        max_candidates = parse_optional_positive_int(value.get("max_candidates", 200), "max_candidates", raw, maximum=1000) or 200
        max_commands = parse_optional_positive_int(value.get("max_commands", 10), "max_commands", raw, maximum=50) or 10
        timeout_ms, max_output_chars, stop_on_failure = parse_run_limits(value, raw, "run_focused_test_commands")
        (
            extract_output_contexts,
            extract_output_diagnostics,
            context_lines,
            max_diagnostics,
            max_contexts,
        ) = parse_output_extraction_options(value, raw, "run_focused_test_commands")
        return RunFocusedTestCommandsAction(
            type="run_focused_test_commands",
            paths=parse_optional_paths(value.get("paths"), raw, "run_focused_test_commands"),
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
            max_bytes_per_context=parse_max_bytes_per_context(value, raw),
        )

    return None
