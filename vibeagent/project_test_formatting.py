from __future__ import annotations

from .check_report_helpers import format_structured_command_checks
from .process_report_helpers import format_structured_command_output_analysis_lines
from .runner_report_helpers import format_selected_not_run_command_lines, selected_not_run_command_items


def indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def format_related_tests_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    target_paths = [str(item) for item in report.get("targetPaths", [])] if isinstance(report.get("targetPaths"), list) else []
    candidates = report.get("candidates") if isinstance(report.get("candidates"), dict) else {}
    items = [item for item in candidates.get("items", []) if isinstance(item, dict)] if isinstance(candidates.get("items"), list) else []
    lines = [
        "Related tests:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  targetPaths: {len(target_paths)}",
        f"  testFiles: {int(report.get('testFiles', 0) or 0)}",
        f"  candidates: {int(candidates.get('shown', len(items)) or 0)}/{int(candidates.get('total', len(items)) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if target_paths:
        lines.append("  targets:")
        lines.extend(f"    - {path}" for path in target_paths)
    else:
        lines.append("  targets: none")

    if items:
        lines.append("  candidates:")
        for candidate in items:
            lines.extend(
                [
                    f"    - source: {candidate.get('source') or ''}",
                    f"      test: {candidate.get('test') or ''}",
                    f"      score: {candidate.get('score')}",
                    f"      reason: {candidate.get('reason') or ''}",
                ]
            )
    else:
        lines.append("  candidates: none")
    return "\n".join(lines)


def format_focused_test_commands_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    target_paths = [str(item) for item in report.get("targetPaths", [])] if isinstance(report.get("targetPaths"), list) else []
    related_tests = report.get("relatedTests") if isinstance(report.get("relatedTests"), dict) else {}
    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    items = [item for item in commands.get("items", []) if isinstance(item, dict)] if isinstance(commands.get("items"), list) else []
    lines = [
        "Focused test commands:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  targetPaths: {len(target_paths)}",
        f"  relatedTests: {int(related_tests.get('total', 0) or 0)}",
        f"  commands: {int(commands.get('shown', len(items)) or 0)}/{int(commands.get('total', len(items)) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if target_paths:
        lines.append("  targets:")
        lines.extend(f"    - {path}" for path in target_paths)
    else:
        lines.append("  targets: none")

    if items:
        lines.append("  commands:")
        for command in items:
            lines.extend(
                [
                    f"    - command: {command.get('command') or ''}",
                    f"      cwd: {command.get('cwd') or '.'}",
                    f"      test: {command.get('test') or ''}",
                    f"      source: {command.get('source') or ''}",
                    f"      available: {'yes' if bool(command.get('available')) else 'no'}",
                    f"      missingTool: {command.get('missingTool') or 'none'}",
                    f"      reason: {command.get('reason') or ''}",
                ]
            )
    else:
        lines.append("  commands: none")
    return "\n".join(lines)


def format_check_focused_test_commands_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    target_paths = [str(item) for item in report.get("targetPaths", [])] if isinstance(report.get("targetPaths"), list) else []
    related_tests = report.get("relatedTests") if isinstance(report.get("relatedTests"), dict) else {}
    focused = report.get("focusedCommands") if isinstance(report.get("focusedCommands"), dict) else {}
    checks = [item for item in report.get("checks", []) if isinstance(item, dict)] if isinstance(report.get("checks"), list) else []
    lines = [
        "Check focused test commands:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  targetPaths: {len(target_paths)}",
        f"  relatedTests: {int(related_tests.get('total', 0) or 0)}",
        f"  focusedCommands: {int(focused.get('shown', len(checks)) or 0)}/{int(focused.get('total', len(checks)) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    lines.extend(format_structured_command_checks(checks, spaces=2))
    return "\n".join(lines)


def format_run_focused_test_commands_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    target_paths = [str(item) for item in report.get("targetPaths", [])] if isinstance(report.get("targetPaths"), list) else []
    focused = report.get("focusedCommands") if isinstance(report.get("focusedCommands"), dict) else {}
    focused_items = (
        [item for item in focused.get("items", []) if isinstance(item, dict)]
        if isinstance(focused.get("items"), list)
        else []
    )
    results = [item for item in report.get("results", []) if isinstance(item, dict)] if isinstance(report.get("results"), list) else []
    lines = [
        "Run focused test commands:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  clean: {'yes' if bool(report.get('clean')) else 'no'}",
        f"  targetPaths: {len(target_paths)}",
        f"  focusedCommands: {int(focused.get('shown', 0) or 0)}/{int(focused.get('total', 0) or 0)}",
        f"  ran: {int(report.get('ran', len(results)) or 0)}",
        f"  skippedUnavailable: {int(report.get('skippedUnavailable', 0) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  stopOnFailure: {'yes' if bool(report.get('stopOnFailure')) else 'no'}",
        f"  stoppedEarly: {'yes' if bool(report.get('stoppedEarly')) else 'no'}",
        f"  durationMs: {report.get('durationMs', 0)}",
        f"  message: {message}",
    ]
    if target_paths:
        lines.append("  targets:")
        lines.extend(f"    - {path}" for path in target_paths)
    else:
        lines.append("  targets: none")
    if focused_items:
        lines.append("  focusedCommands:")
        for command in focused_items:
            lines.extend(
                [
                    f"    - command: {command.get('command') or ''}",
                    f"      cwd: {command.get('cwd') or '.'}",
                    f"      test: {command.get('test') or ''}",
                    f"      source: {command.get('source') or ''}",
                    f"      available: {'yes' if bool(command.get('available')) else 'no'}",
                    f"      missingTool: {command.get('missingTool') or 'none'}",
                    f"      reason: {command.get('reason') or ''}",
                ]
            )
    else:
        lines.append("  focusedCommands: none")
    lines.extend(
        format_selected_not_run_command_lines(
            selected_not_run_command_items(
                report,
                item_key="items",
                fallback_items=focused_items,
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
                    f"      maxOutputChars: {result.get('maxOutputChars', 0)}",
                    f"      stdoutTruncated: {'yes' if bool(result.get('stdoutTruncated')) else 'no'}",
                    f"      stderrTruncated: {'yes' if bool(result.get('stderrTruncated')) else 'no'}",
                ]
            )
            lines.extend(format_structured_command_output_analysis_lines(analysis, spaces=6))
            stdout = str(result.get("stdout") or "")
            stderr = str(result.get("stderr") or "")
            if stdout:
                lines.append("      stdout:")
                lines.append(indent_block(stdout.rstrip(), spaces=8))
            else:
                lines.append("      stdout: none")
            if stderr:
                lines.append("      stderr:")
                lines.append(indent_block(stderr.rstrip(), spaces=8))
            else:
                lines.append("      stderr: none")
    else:
        lines.append("  results: none")
    return "\n".join(lines)
