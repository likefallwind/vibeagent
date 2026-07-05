from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .local_runtime_commands import (
    command_results_clean,
    format_structured_command_output_analysis_lines,
    serialize_command_check,
    serialize_command_result,
    sum_command_result_duration_ms,
    validate_run_output_context_options,
)
from .types import CheckSuggestedChecksAction, RunSuggestedChecksAction
from .workspace_core import RunWorkspace
from .workspace import suggest_project_checks
from .workflow_commands import format_review_check


def _indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def get_checks_report(project_root: str | Path = ".", max_checks: int = 20) -> dict[str, object]:
    if max_checks < 1:
        raise ValueError("max_checks must be at least 1.")
    if max_checks > 100:
        raise ValueError("max_checks must be at most 100.")
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-checks", session_dir=root / ".vibeagent" / "sessions" / "local-checks")
    suggestions = suggest_project_checks(workspace, max_commands=max_checks)
    checks = [item for item in suggestions["checks"] if isinstance(item, dict)]
    changed_files = [item for item in suggestions["changed_files"] if isinstance(item, str)]
    return {
        "projectRoot": str(root),
        "suggestedChecks": {
            "shown": len(checks),
            "total": suggestions["total"],
            "truncated": bool(suggestions["truncated"]),
            "commands": checks,
        },
        "changedFiles": changed_files,
        "message": suggestions["message"],
    }


def get_checks_text(project_root: str | Path = ".", max_checks: int = 20) -> str:
    return format_checks_report_text(get_checks_report(project_root, max_checks=max_checks))


def format_checks_report_text(report: dict[str, object]) -> str:
    suggested = report.get("suggestedChecks") if isinstance(report.get("suggestedChecks"), dict) else {}
    checks = suggested.get("commands") if isinstance(suggested.get("commands"), list) else []
    changed_files = report.get("changedFiles") if isinstance(report.get("changedFiles"), list) else []
    lines = [
        "Checks:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  suggestedChecks: {int(suggested.get('shown', 0) or 0)}/{int(suggested.get('total', 0) or 0)}",
        f"  changedFiles: {len(changed_files)}",
        f"  truncated: {'yes' if bool(suggested.get('truncated')) else 'no'}",
    ]
    if checks:
        lines.append("  commands:")
        lines.extend(format_review_check(item) for item in checks)
    else:
        lines.append("  commands: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def serialize_suggested_check(check: object, index: int | None = None) -> dict[str, object]:
    item: dict[str, object] = {
        "command": str(getattr(check, "command", "") or ""),
        "cwd": str(getattr(check, "cwd", ".") or "."),
        "source": str(getattr(check, "source", "") or ""),
        "reason": str(getattr(check, "reason", "") or ""),
        "available": bool(getattr(check, "available", False)),
        "missingTool": getattr(check, "missing_tool", None),
    }
    if index is not None:
        item["index"] = index
    return item


def serialize_focused_test_command(command: object, index: int | None = None) -> dict[str, object]:
    item: dict[str, object] = {
        "command": str(getattr(command, "command", "") or ""),
        "cwd": str(getattr(command, "cwd", ".") or "."),
        "test": str(getattr(command, "test_path", "") or ""),
        "source": str(getattr(command, "source", "") or ""),
        "reason": str(getattr(command, "reason", "") or ""),
        "available": bool(getattr(command, "available", False)),
        "missingTool": getattr(command, "missing_tool", None),
    }
    if index is not None:
        item["index"] = index
    return item


def format_structured_command_checks(checks: list[dict[str, object]], spaces: int = 2) -> list[str]:
    if not checks:
        return [f"{' ' * spaces}checks: none"]
    prefix = " " * spaces
    child = " " * (spaces + 2)
    lines = [f"{prefix}checks:"]
    for position, check in enumerate(checks, start=1):
        index = check.get("index", position)
        lines.extend(
            [
                f"{child}- index: {index}",
                f"{child}  command: {check.get('command') or ''}",
                f"{child}  cwd: {check.get('cwd') or '.'}",
                f"{child}  ok: {'yes' if bool(check.get('ok')) else 'no'}",
                f"{child}  cwdOk: {'yes' if bool(check.get('cwdOk')) else 'no'}",
                f"{child}  blocked: {'yes' if bool(check.get('blocked')) else 'no'}",
                f"{child}  executableAvailable: {'yes' if bool(check.get('executableAvailable')) else 'no'}",
            ]
        )
        if check.get("blockReason"):
            lines.append(f"{child}  blockReason: {check.get('blockReason')}")
        if check.get("missingTool"):
            lines.append(f"{child}  missingTool: {check.get('missingTool')}")
        lines.append(f"{child}  message: {check.get('message') or ''}")
    return lines


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
        return {
            "projectRoot": str(root),
            "ok": False,
            "suggestedChecks": {"shown": 0, "total": 0, "commands": []},
            "commands": {"shown": 0, "total": 0, "max": max_checks},
            "truncated": False,
            "checks": [],
            "message": f"Usage: /check-suggested-checks [max|--max-checks N]\nError: {error}",
        }

    workspace = RunWorkspace(root=root, run_id="local-check-suggested-checks", session_dir=root / ".vibeagent" / "sessions" / "local-check-suggested-checks")
    observation = execute_action(
        workspace,
        CheckSuggestedChecksAction(type="check_suggested_checks", max_commands=selected_max),
    )
    if observation.kind != "check_suggested_checks":
        return {
            "projectRoot": str(root),
            "ok": False,
            "suggestedChecks": {"shown": 0, "total": 0, "commands": []},
            "commands": {"shown": 0, "total": 0, "max": selected_max},
            "truncated": False,
            "checks": [],
            "message": f"Unexpected observation: {observation.kind}",
        }

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
            "results": [],
            "message": message,
        }

    try:
        selected_max = parse_suggested_checks_limit(argument, max_checks)
    except ValueError as error:
        return failure(f"Usage: /run-suggested-checks [max]\nError: {error}")
    if timeout_ms < 100:
        return failure("Usage: /run-suggested-checks [max]\nError: timeout_ms must be at least 100.", selected_max)
    if timeout_ms > 600_000:
        return failure("Usage: /run-suggested-checks [max]\nError: timeout_ms must be at most 600000.", selected_max)
    if max_output_chars < 1_000:
        return failure("Usage: /run-suggested-checks [max]\nError: max_output_chars must be at least 1000.", selected_max)
    if max_output_chars > 50_000:
        return failure("Usage: /run-suggested-checks [max]\nError: max_output_chars must be at most 50000.", selected_max)
    output_context_error = validate_run_output_context_options(
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
        usage="Usage: /run-suggested-checks [max]",
    )
    if output_context_error:
        return failure(output_context_error, selected_max)

    workspace = RunWorkspace(root=root, run_id="local-run-suggested-checks", session_dir=root / ".vibeagent" / "sessions" / "local-run-suggested-checks")
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

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "clean": observation.ok and command_results_clean(list(observation.results)),
        "suggestedChecks": {
            "shown": len(observation.suggested_checks),
            "total": observation.total,
            "commands": [serialize_suggested_check(check, index=index) for index, check in enumerate(observation.suggested_checks, start=1)],
        },
        "commands": {"shown": len(observation.suggested_checks), "total": observation.total, "max": observation.max_commands},
        "ran": len(observation.results),
        "skippedUnavailable": observation.skipped_unavailable,
        "truncated": observation.truncated,
        "stopOnFailure": stop_on_failure,
        "stoppedEarly": observation.stopped_early,
        "durationMs": sum_command_result_duration_ms(list(observation.results)),
        "results": [serialize_command_result(result, index=index) for index, result in enumerate(observation.results, start=1)],
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
    not_run = suggested_items[len(results) :] if bool(report.get("stoppedEarly")) else []
    if not_run:
        lines.append(f"  selectedCommandsNotRun: {len(not_run)}")
        for check in not_run:
            lines.append(f"    - command: {check.get('command') or ''}")
            lines.append(f"      cwd: {check.get('cwd') or '.'}")
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


def parse_suggested_checks_limit(argument: str | None = None, default: int = 10) -> int:
    if argument and argument.strip():
        parts = argument.split()
        if len(parts) != 1:
            raise ValueError("expected at most one max command count.")
        try:
            selected = int(parts[0])
        except ValueError as error:
            raise ValueError("max must be an integer.") from error
    else:
        selected = default
    if selected < 1:
        raise ValueError("max must be at least 1.")
    if selected > 10:
        raise ValueError("max must be at most 10.")
    return selected
