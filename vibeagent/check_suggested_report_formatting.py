from __future__ import annotations

from .check_report_helpers import format_structured_command_checks, indent_block as _indent_block
from .local_runtime_report_formatting import format_command_output_artifact_lines
from .local_runtime_commands import format_structured_command_output_analysis_lines
from .runner_report_helpers import format_selected_not_run_command_lines, selected_not_run_command_items


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
            lines.extend(format_command_output_artifact_lines(result, spaces=6))
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
