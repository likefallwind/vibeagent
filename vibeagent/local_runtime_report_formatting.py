from __future__ import annotations

from .process_report_helpers import format_structured_command_output_analysis_lines


def indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def format_command_check_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        "Command check:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  command: {report.get('command') or ''}",
        f"  cwd: {report.get('cwd') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  cwdOk: {'yes' if bool(report.get('cwdOk')) else 'no'}",
        f"  blocked: {'yes' if bool(report.get('blocked')) else 'no'}",
        f"  executableAvailable: {'yes' if bool(report.get('executableAvailable')) else 'no'}",
    ]
    if report.get("blockReason"):
        lines.append(f"  blockReason: {report.get('blockReason')}")
    if report.get("missingTool"):
        lines.append(f"  missingTool: {report.get('missingTool')}")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_run_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    analysis = report.get("analysis") if isinstance(report.get("analysis"), dict) else {}
    lines = [
        "Run:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  command: {report.get('command') or ''}",
        f"  cwd: {report.get('cwd') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  clean: {'yes' if bool(report.get('clean')) else 'no'}",
        f"  exitCode: {report.get('exitCode') if report.get('exitCode') is not None else '.'}",
        f"  timedOut: {'yes' if bool(report.get('timedOut')) else 'no'}",
        f"  signal: {report.get('signal') or '.'}",
        f"  timeoutMs: {report.get('timeoutMs', 0)}",
        f"  durationMs: {report.get('durationMs', 0)}",
        f"  sandboxed: {'yes' if bool(report.get('sandboxed')) else 'no'}",
        f"  maxOutputChars: {report.get('maxOutputChars', 0)}",
        f"  stdoutTruncated: {'yes' if bool(report.get('stdoutTruncated')) else 'no'}",
        f"  stderrTruncated: {'yes' if bool(report.get('stderrTruncated')) else 'no'}",
    ]
    stdout = str(report.get("stdout") or "")
    stderr = str(report.get("stderr") or "")
    if stdout:
        lines.append("  stdout:")
        lines.append(indent_block(stdout.rstrip(), spaces=4))
    else:
        lines.append("  stdout: none")
    if stderr:
        lines.append("  stderr:")
        lines.append(indent_block(stderr.rstrip(), spaces=4))
    else:
        lines.append("  stderr: none")
    lines.extend(format_structured_command_output_analysis_lines(analysis, spaces=2))
    return "\n".join(lines)


def format_run_sequence_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    results = [item for item in report.get("results", []) if isinstance(item, dict)] if isinstance(report.get("results"), list) else []
    lines = [
        "Run sequence:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  clean: {'yes' if bool(report.get('clean')) else 'no'}",
        f"  commands: {int(commands.get('shown', len(results)) or 0)}/{int(commands.get('total', len(results)) or 0)}",
        f"  stopOnFailure: {'yes' if bool(report.get('stopOnFailure')) else 'no'}",
        f"  stoppedEarly: {'yes' if bool(report.get('stoppedEarly')) else 'no'}",
        f"  durationMs: {report.get('durationMs', 0)}",
        f"  message: {message}",
    ]
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
                lines.append(indent_block(stdout.rstrip(), spaces=8))
            else:
                lines.append("      stdout: none")
            if stderr:
                lines.append("      stderr:")
                lines.append(indent_block(stderr.rstrip(), spaces=8))
            else:
                lines.append("      stderr: none")
            lines.extend(format_structured_command_output_analysis_lines(analysis, spaces=6))
    else:
        lines.append("  results: none")
    return "\n".join(lines)


def format_command_output_diagnostic_lines(result: object, spaces: int) -> list[str]:
    diagnostics = list(getattr(result, "output_diagnostics", []) or [])
    total = int(getattr(result, "output_diagnostic_total", 0) or 0)
    truncated = bool(getattr(result, "output_diagnostics_truncated", False))
    if not diagnostics and total == 0:
        return []

    prefix = " " * spaces
    child_prefix = " " * (spaces + 2)
    lines = [
        f"{prefix}outputDiagnostics: {len(diagnostics)}/{total}",
        f"{prefix}outputDiagnosticsTruncated: {'yes' if truncated else 'no'}",
    ]
    if diagnostics:
        lines.append(f"{prefix}diagnostics:")
        for diagnostic in diagnostics:
            location = ""
            if diagnostic.path:
                location = f" {diagnostic.path}:{diagnostic.line if diagnostic.line is not None else '?'}"
                if diagnostic.column is not None:
                    location += f":{diagnostic.column}"
            lines.append(
                f"{child_prefix}- {diagnostic.severity} outputLine={diagnostic.output_line}{location}: {diagnostic.text}"
            )
    return lines


def format_command_output_context_lines(result: object, spaces: int) -> list[str]:
    contexts = list(getattr(result, "output_contexts", []) or [])
    total_refs = int(getattr(result, "output_context_total_refs", 0) or 0)
    truncated = bool(getattr(result, "output_contexts_truncated", False))
    if not contexts and total_refs == 0:
        return []

    prefix = " " * spaces
    child_prefix = " " * (spaces + 2)
    lines = [
        f"{prefix}outputContexts: {len(contexts)}/{total_refs}",
        f"{prefix}outputContextsTruncated: {'yes' if truncated else 'no'}",
    ]
    if contexts:
        lines.append(f"{prefix}contexts:")
        for context in contexts:
            lines.append(
                f"{child_prefix}- {context.path}:{context.line}"
                f"{':' + str(context.column) if context.column is not None else ''}"
                f" [{context.raw}] ok={'yes' if context.ok else 'no'}"
            )
            if context.content:
                lines.append(indent_block(context.content.rstrip(), spaces=spaces + 4))
            else:
                lines.append(f"{' ' * (spaces + 4)}{context.message}")
    return lines


def format_check_run_sequence_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    checks = [item for item in report.get("checks", []) if isinstance(item, dict)] if isinstance(report.get("checks"), list) else []
    lines = [
        "Check run sequence:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  commands: {int(commands.get('shown', len(checks)) or 0)}/{int(commands.get('total', len(checks)) or 0)}",
        f"  message: {message}",
    ]
    if checks:
        lines.append("  checks:")
        for position, check in enumerate(checks, start=1):
            index = check.get("index", position)
            lines.extend(
                [
                    f"    - index: {index}",
                    f"      command: {check.get('command') or ''}",
                    f"      cwd: {check.get('cwd') or '.'}",
                    f"      ok: {'yes' if bool(check.get('ok')) else 'no'}",
                    f"      cwdOk: {'yes' if bool(check.get('cwdOk')) else 'no'}",
                    f"      blocked: {'yes' if bool(check.get('blocked')) else 'no'}",
                    f"      executableAvailable: {'yes' if bool(check.get('executableAvailable')) else 'no'}",
                ]
            )
            if check.get("blockReason"):
                lines.append(f"      blockReason: {check.get('blockReason')}")
            if check.get("missingTool"):
                lines.append(f"      missingTool: {check.get('missingTool')}")
            lines.append(f"      message: {check.get('message') or ''}")
    else:
        lines.append("  checks: none")
    return "\n".join(lines)


def format_check_start_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        "Check start:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  command: {report.get('command') or ''}",
        f"  cwd: {report.get('cwd') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  cwdOk: {'yes' if bool(report.get('cwdOk')) else 'no'}",
        f"  blocked: {'yes' if bool(report.get('blocked')) else 'no'}",
        f"  executableAvailable: {'yes' if bool(report.get('executableAvailable')) else 'no'}",
    ]
    if report.get("blockReason"):
        lines.append(f"  blockReason: {report.get('blockReason')}")
    if report.get("missingTool"):
        lines.append(f"  missingTool: {report.get('missingTool')}")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_start_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    return "\n".join(
        [
            "Start:",
            f"  projectRoot: {report.get('projectRoot') or '.'}",
            f"  command: {report.get('command') or ''}",
            f"  cwd: {report.get('cwd') or '.'}",
            f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
            f"  processId: {report.get('processId') or '.'}",
            f"  pid: {report.get('pid') if report.get('pid') is not None else '.'}",
            f"  stdoutPath: {report.get('stdoutPath') or '.'}",
            f"  stderrPath: {report.get('stderrPath') or '.'}",
            f"  sandboxed: {'yes' if bool(report.get('sandboxed')) else 'no'}",
            f"  message: {message}",
        ]
    )
