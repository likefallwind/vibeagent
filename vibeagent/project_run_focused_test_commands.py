from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .check_report_helpers import serialize_not_run_focused_test_commands
from .local_runtime_commands import (
    command_results_clean,
    serialize_command_result,
    sum_command_result_duration_ms,
)
from .project_focused_test_reports import empty_run_focused_test_commands_report, serialize_focused_test_command_items, usage_message
from .project_focused_test_validation import parse_related_tests_argument, validate_run_focused_test_options
from .project_test_formatting import format_run_focused_test_commands_report_text
from .types import RunFocusedTestCommandsAction
from .workspace_core import create_local_workspace

RUN_FOCUSED_TESTS_USAGE = "Usage: /run-focused-tests [path...]"


def get_run_focused_test_commands_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
    max_commands: int = 10,
    timeout_ms: int = 30_000,
    max_output_chars: int = 12_000,
    stop_on_failure: bool = True,
    extract_output_contexts: bool = False,
    extract_output_diagnostics: bool = False,
    context_lines: int = 5,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    return format_run_focused_test_commands_report_text(
        get_run_focused_test_commands_report(
            project_root,
            argument,
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
            max_bytes_per_context=max_bytes_per_context,
        )
    )


def get_run_focused_test_commands_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
    max_commands: int = 10,
    timeout_ms: int = 30_000,
    max_output_chars: int = 12_000,
    stop_on_failure: bool = True,
    extract_output_contexts: bool = False,
    extract_output_diagnostics: bool = False,
    context_lines: int = 5,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str) -> dict[str, object]:
        return empty_run_focused_test_commands_report(
            str(root),
            message,
            max_commands=max_commands,
            stop_on_failure=stop_on_failure,
        )

    try:
        paths = parse_related_tests_argument(argument)
    except ValueError as error:
        return failure(usage_message(RUN_FOCUSED_TESTS_USAGE, error))
    options_error = validate_run_focused_test_options(
        usage=RUN_FOCUSED_TESTS_USAGE,
        timeout_ms=timeout_ms,
        max_output_chars=max_output_chars,
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
    )
    if options_error:
        return failure(options_error)

    workspace = create_local_workspace(root, "local-run-focused-tests")
    observation = execute_action(
        workspace,
        RunFocusedTestCommandsAction(
            type="run_focused_test_commands",
            paths=paths,
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
            max_bytes_per_context=max_bytes_per_context,
        ),
        command_timeout_ms=timeout_ms,
    )
    if observation.kind != "run_focused_test_commands":
        return failure(f"Unexpected observation: {observation.kind}")

    focused_commands = list(observation.focused_commands)
    results = list(observation.results)

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "clean": observation.ok and command_results_clean(results),
        "targetPaths": list(observation.target_paths),
        "relatedTests": {"total": observation.related_tests_total},
        "focusedCommands": {
            "shown": len(focused_commands),
            "total": observation.total,
            "max": observation.max_commands,
            "items": serialize_focused_test_command_items(focused_commands),
        },
        "ran": len(results),
        "skippedUnavailable": observation.skipped_unavailable,
        "truncated": observation.truncated,
        "stopOnFailure": stop_on_failure,
        "stoppedEarly": observation.stopped_early,
        "selectedCommandsNotRun": serialize_not_run_focused_test_commands(
            focused_commands,
            ran_count=len(results),
            stopped_early=observation.stopped_early,
        ),
        "durationMs": sum_command_result_duration_ms(results),
        "results": [serialize_command_result(result, index=index) for index, result in enumerate(results, start=1)],
        "message": observation.message,
    }
