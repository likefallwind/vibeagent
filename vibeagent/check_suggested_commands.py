from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .check_limit_parsing import (
    CHECK_SUGGESTED_CHECKS_USAGE,
    RUN_SUGGESTED_CHECKS_USAGE,
    parse_suggested_checks_limit,
)
from .check_report_helpers import (
    format_structured_command_checks,
    indent_block as _indent_block,
    serialize_not_run_suggested_checks,
    serialize_suggested_check,
)
from .local_runtime_commands import (
    command_results_clean,
    format_structured_command_output_analysis_lines,
    serialize_command_check,
    serialize_command_result,
    sum_command_result_duration_ms,
    validate_run_output_context_options,
)
from .runner_report_helpers import format_selected_not_run_command_lines, selected_not_run_command_items
from .types import CheckSuggestedChecksAction, RunSuggestedChecksAction
from .workspace_core import create_local_workspace


def _usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def _check_suggested_checks_failure_report(root: Path, message: str, *, selected_max: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "suggestedChecks": {"shown": 0, "total": 0, "commands": []},
        "commands": {"shown": 0, "total": 0, "max": selected_max},
        "truncated": False,
        "checks": [],
        "message": message,
    }


def _run_suggested_checks_failure_report(
    root: Path,
    message: str,
    *,
    selected_max: int,
    stop_on_failure: bool,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "suggestedChecks": {"shown": 0, "total": 0, "commands": []},
        "commands": {"shown": 0, "total": 0, "max": selected_max},
        "ran": 0,
        "skippedUnavailable": 0,
        "truncated": False,
        "stopOnFailure": stop_on_failure,
        "stoppedEarly": False,
        "selectedCommandsNotRun": {"count": 0, "commands": []},
        "results": [],
        "message": message,
    }


def get_check_suggested_checks_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_checks: int = 10,
) -> str:
    return format_check_suggested_checks_report_text(get_check_suggested_checks_report(project_root, argument, max_checks=max_checks))


def get_check_suggested_checks_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_checks: int = 10,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        selected_max = parse_suggested_checks_limit(argument, max_checks)
    except ValueError as error:
        return _check_suggested_checks_failure_report(
            root,
            _usage_error(CHECK_SUGGESTED_CHECKS_USAGE, error),
            selected_max=max_checks,
        )

    workspace = create_local_workspace(root, "local-check-suggested-checks")
    observation = execute_action(
        workspace,
        CheckSuggestedChecksAction(type="check_suggested_checks", max_commands=selected_max),
    )
    if observation.kind != "check_suggested_checks":
        return _check_suggested_checks_failure_report(
            root,
            f"Unexpected observation: {observation.kind}",
            selected_max=selected_max,
        )

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "suggestedChecks": {
            "shown": len(observation.suggested_checks),
            "total": observation.total,
            "commands": [serialize_suggested_check(check, index=index) for index, check in enumerate(observation.suggested_checks, start=1)],
        },
        "commands": {"shown": len(observation.checks), "total": observation.total, "max": observation.max_commands},
        "truncated": observation.truncated,
        "checks": [serialize_command_check(check, index=index) for index, check in enumerate(observation.checks, start=1)],
        "message": observation.message,
    }


def format_check_suggested_checks_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message

    suggested = report.get("suggestedChecks") if isinstance(report.get("suggestedChecks"), dict) else {}
    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    checks = [item for item in report.get("checks", []) if isinstance(item, dict)] if isinstance(report.get("checks"), list) else []
    lines = [
        "Check suggested checks:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  commands: {int(commands.get('shown', len(checks)) or 0)}/{int(commands.get('total', len(checks)) or 0)}",
        f"  suggestedChecks: {int(suggested.get('shown', 0) or 0)}/{int(suggested.get('total', 0) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    lines.extend(format_structured_command_checks(checks, spaces=2))
    return "\n".join(lines)


def get_run_suggested_checks_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_checks: int = 10,
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
    return format_run_suggested_checks_report_text(
        get_run_suggested_checks_report(
            project_root,
            argument,
            max_checks=max_checks,
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


def get_run_suggested_checks_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_checks: int = 10,
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

    def failure(message: str, selected_max: int = max_checks) -> dict[str, object]:
        return _run_suggested_checks_failure_report(
            root,
            message,
            selected_max=selected_max,
            stop_on_failure=stop_on_failure,
        )

    try:
        selected_max = parse_suggested_checks_limit(argument, max_checks)
    except ValueError as error:
        return failure(_usage_error(RUN_SUGGESTED_CHECKS_USAGE, error))
    if timeout_ms < 100:
        return failure(_usage_error(RUN_SUGGESTED_CHECKS_USAGE, "timeout_ms must be at least 100."), selected_max)
    if timeout_ms > 600_000:
        return failure(_usage_error(RUN_SUGGESTED_CHECKS_USAGE, "timeout_ms must be at most 600000."), selected_max)
    if max_output_chars < 1_000:
        return failure(_usage_error(RUN_SUGGESTED_CHECKS_USAGE, "max_output_chars must be at least 1000."), selected_max)
    if max_output_chars > 50_000:
        return failure(_usage_error(RUN_SUGGESTED_CHECKS_USAGE, "max_output_chars must be at most 50000."), selected_max)
    output_context_error = validate_run_output_context_options(
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
        usage=RUN_SUGGESTED_CHECKS_USAGE,
    )
    if output_context_error:
        return failure(output_context_error, selected_max)

    workspace = create_local_workspace(root, "local-run-suggested-checks")
    observation = execute_action(
        workspace,
        RunSuggestedChecksAction(
            type="run_suggested_checks",
            max_commands=selected_max,
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
    if observation.kind != "run_suggested_checks":
        return failure(f"Unexpected observation: {observation.kind}", selected_max)

    suggested_checks = list(observation.suggested_checks)
    results = list(observation.results)

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "clean": observation.ok and command_results_clean(results),
        "suggestedChecks": {
            "shown": len(suggested_checks),
            "total": observation.total,
            "commands": [serialize_suggested_check(check, index=index) for index, check in enumerate(suggested_checks, start=1)],
        },
        "commands": {"shown": len(suggested_checks), "total": observation.total, "max": observation.max_commands},
        "ran": len(results),
        "skippedUnavailable": observation.skipped_unavailable,
        "truncated": observation.truncated,
        "stopOnFailure": stop_on_failure,
        "stoppedEarly": observation.stopped_early,
        "selectedCommandsNotRun": serialize_not_run_suggested_checks(
            suggested_checks,
            ran_count=len(results),
            stopped_early=observation.stopped_early,
        ),
        "durationMs": sum_command_result_duration_ms(results),
        "results": [serialize_command_result(result, index=index) for index, result in enumerate(results, start=1)],
        "message": observation.message,
    }


def format_run_suggested_checks_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    suggested = report.get("suggestedChecks") if isinstance(report.get("suggestedChecks"), dict) else {}
    suggested_items = (
        [item for item in suggested.get("commands", []) if isinstance(item, dict)]
        if isinstance(suggested.get("commands"), list)
        else []
    )
    results = [item for item in report.get("results", []) if isinstance(item, dict)] if isinstance(report.get("results"), list) else []
    lines = [
        "Run suggested checks:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  clean: {'yes' if bool(report.get('clean')) else 'no'}",
        f"  suggestedChecks: {int(suggested.get('shown', 0) or 0)}/{int(suggested.get('total', 0) or 0)}",
        f"  ran: {int(report.get('ran', len(results)) or 0)}",
        f"  skippedUnavailable: {int(report.get('skippedUnavailable', 0) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  stopOnFailure: {'yes' if bool(report.get('stopOnFailure')) else 'no'}",
        f"  stoppedEarly: {'yes' if bool(report.get('stoppedEarly')) else 'no'}",
        f"  durationMs: {report.get('durationMs', 0)}",
        f"  message: {message}",
    ]
    if suggested_items:
        lines.append("  suggestedChecks:")
        for check in suggested_items:
            lines.extend(
                [
                    f"    - command: {check.get('command') or ''}",
                    f"      cwd: {check.get('cwd') or '.'}",
                    f"      source: {check.get('source') or ''}",
                    f"      available: {'yes' if bool(check.get('available')) else 'no'}",
                    f"      missingTool: {check.get('missingTool') or 'none'}",
                    f"      reason: {check.get('reason') or ''}",
                ]
            )
    else:
        lines.append("  suggestedChecks: none")
    lines.extend(
        format_selected_not_run_command_lines(
            selected_not_run_command_items(
                report,
                item_key="commands",
                fallback_items=suggested_items,
                results=results,
            )
        )
    )
    if results:
        lines.append("  results:")
        for position, result in enumerate(results, start=1):
            index = result.get("index", position)
            analysis = result.get("analysis") if isinstance(result.get("analysis"), dict) else {}
            lines.extend(
                [
                    f"    - index: {index}",
                    f"      command: {result.get('command') or ''}",
                    f"      cwd: {result.get('cwd') or '.'}",
                    f"      ok: {'yes' if bool(result.get('ok')) else 'no'}",
                    f"      clean: {'yes' if bool(result.get('clean')) else 'no'}",
                    f"      exitCode: {result.get('exitCode') if result.get('exitCode') is not None else '.'}",
                    f"      timedOut: {'yes' if bool(result.get('timedOut')) else 'no'}",
                    f"      signal: {result.get('signal') or '.'}",
                    f"      timeoutMs: {result.get('timeoutMs', 0)}",
                    f"      durationMs: {result.get('durationMs', 0)}",
                    f"      sandboxed: {'yes' if bool(result.get('sandboxed')) else 'no'}",
                    f"      maxOutputChars: {result.get('maxOutputChars', 0)}",
                    f"      stdoutTruncated: {'yes' if bool(result.get('stdoutTruncated')) else 'no'}",
                    f"      stderrTruncated: {'yes' if bool(result.get('stderrTruncated')) else 'no'}",
                ]
            )
            stdout = str(result.get("stdout") or "")
            stderr = str(result.get("stderr") or "")
            if stdout:
                lines.append("      stdout:")
                lines.append(_indent_block(stdout.rstrip(), spaces=8))
            else:
                lines.append("      stdout: none")
            if stderr:
                lines.append("      stderr:")
                lines.append(_indent_block(stderr.rstrip(), spaces=8))
            else:
                lines.append("      stderr: none")
            lines.extend(format_structured_command_output_analysis_lines(analysis, spaces=6))
    else:
        lines.append("  results: none")
    return "\n".join(lines)
