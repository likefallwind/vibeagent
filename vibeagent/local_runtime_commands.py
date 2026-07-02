from __future__ import annotations

from pathlib import Path
import shlex
import sys
from urllib.parse import urlparse

from .actions import build_command_check_observation, execute_action as _default_execute_action
from .process_commands import (
    format_structured_command_output_analysis_lines,
    serialize_command_output_analysis,
)
from .types import (
    CheckRunCommandsAction,
    CheckStartCommandAction,
    HttpCheckAction,
    HttpFetchAction,
    PortCheckAction,
    RunCommandAction,
    RunCommandItem,
    RunCommandsAction,
    StartCommandAction,
)
from .workspace_core import RunWorkspace


def _indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def get_command_check_text(project_root: str | Path = ".", command: str | None = None, cwd: str | None = None) -> str:
    return format_command_check_report_text(get_command_check_report(project_root, command, cwd))


def get_command_check_report(project_root: str | Path = ".", command: str | None = None, cwd: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    if command is None or not command.strip():
        return {
            "projectRoot": str(root),
            "command": "",
            "cwd": cwd or ".",
            "ok": False,
            "cwdOk": False,
            "blocked": False,
            "executableAvailable": False,
            "blockReason": None,
            "missingTool": None,
            "message": "Usage: /command <shell command>",
        }
    workspace = RunWorkspace(root=root, run_id="local-command-check", session_dir=root / ".vibeagent" / "sessions" / "local-command-check")
    observation = build_command_check_observation(workspace, command.strip(), cwd)
    return {
        "projectRoot": str(root),
        **serialize_command_check(observation),
    }


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


def get_run_text(
    project_root: str | Path = ".",
    command: str | None = None,
    cwd: str | None = None,
    timeout_ms: int = 30_000,
    max_output_chars: int = 12_000,
    extract_output_contexts: bool = False,
    extract_output_diagnostics: bool = False,
    context_lines: int = 5,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    return format_run_report_text(
        get_run_report(
            project_root,
            command,
            cwd=cwd,
            timeout_ms=timeout_ms,
            max_output_chars=max_output_chars,
            extract_output_contexts=extract_output_contexts,
            extract_output_diagnostics=extract_output_diagnostics,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )
    )


def empty_command_output_analysis() -> dict[str, object]:
    return {
        "diagnostics": {"shown": 0, "total": 0, "items": []},
        "diagnosticsTruncated": False,
        "contexts": {"shown": 0, "totalRefs": 0, "items": []},
        "contextsTruncated": False,
    }


def serialize_command_result(result: object, index: int | None = None) -> dict[str, object]:
    exit_code = getattr(result, "exit_code", None)
    timed_out = bool(getattr(result, "timed_out", False))
    item: dict[str, object] = {
        "command": str(getattr(result, "command", "") or ""),
        "cwd": str(getattr(result, "cwd", ".") or "."),
        "ok": exit_code == 0 and not timed_out,
        "exitCode": exit_code,
        "timedOut": timed_out,
        "signal": getattr(result, "signal", None),
        "timeoutMs": int(getattr(result, "timeout_ms", 0) or 0),
        "maxOutputChars": int(getattr(result, "max_output_chars", 0) or 0),
        "stdout": str(getattr(result, "stdout", "") or ""),
        "stderr": str(getattr(result, "stderr", "") or ""),
        "stdoutTruncated": bool(getattr(result, "stdout_truncated", False)),
        "stderrTruncated": bool(getattr(result, "stderr_truncated", False)),
        "analysis": serialize_command_output_analysis(result),
    }
    if index is not None:
        item["index"] = index
    return item


def get_run_report(
    project_root: str | Path = ".",
    command: str | None = None,
    cwd: str | None = None,
    timeout_ms: int = 30_000,
    max_output_chars: int = 12_000,
    extract_output_contexts: bool = False,
    extract_output_diagnostics: bool = False,
    context_lines: int = 5,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str) -> dict[str, object]:
        return {
            "projectRoot": str(root),
            "ok": False,
            "command": (command or "").strip(),
            "cwd": cwd or ".",
            "exitCode": None,
            "timedOut": False,
            "signal": None,
            "timeoutMs": timeout_ms,
            "maxOutputChars": max_output_chars,
            "stdout": "",
            "stderr": "",
            "stdoutTruncated": False,
            "stderrTruncated": False,
            "analysis": empty_command_output_analysis(),
            "message": message,
        }

    if command is None or not command.strip():
        return failure("Usage: /run <shell command>")
    if timeout_ms < 100:
        return failure("Usage: /run <shell command>\nError: timeout_ms must be at least 100.")
    if timeout_ms > 600_000:
        return failure("Usage: /run <shell command>\nError: timeout_ms must be at most 600000.")
    if max_output_chars < 1_000:
        return failure("Usage: /run <shell command>\nError: max_output_chars must be at least 1000.")
    if max_output_chars > 50_000:
        return failure("Usage: /run <shell command>\nError: max_output_chars must be at most 50000.")
    output_context_error = validate_run_output_context_options(
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
        usage="Usage: /run <shell command>",
    )
    if output_context_error:
        return failure(output_context_error)

    workspace = RunWorkspace(root=root, run_id="local-run", session_dir=root / ".vibeagent" / "sessions" / "local-run")
    observation = _execute_action(
        workspace,
        RunCommandAction(
            type="run_command",
            command=command.strip(),
            timeout_ms=timeout_ms,
            cwd=cwd,
            max_output_chars=max_output_chars,
            extract_output_contexts=extract_output_contexts,
            extract_output_diagnostics=extract_output_diagnostics,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        ),
        command_timeout_ms=timeout_ms,
    )
    if observation.kind != "run_command":
        return failure(f"Unexpected observation: {observation.kind}")
    result = observation.result
    ok = result.exit_code == 0 and not result.timed_out
    return {
        "projectRoot": str(root),
        **serialize_command_result(result),
        "message": "Command completed." if ok else "Command failed.",
    }


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
        f"  exitCode: {report.get('exitCode') if report.get('exitCode') is not None else '.'}",
        f"  timedOut: {'yes' if bool(report.get('timedOut')) else 'no'}",
        f"  signal: {report.get('signal') or '.'}",
        f"  timeoutMs: {report.get('timeoutMs', 0)}",
        f"  maxOutputChars: {report.get('maxOutputChars', 0)}",
        f"  stdoutTruncated: {'yes' if bool(report.get('stdoutTruncated')) else 'no'}",
        f"  stderrTruncated: {'yes' if bool(report.get('stderrTruncated')) else 'no'}",
    ]
    stdout = str(report.get("stdout") or "")
    stderr = str(report.get("stderr") or "")
    if stdout:
        lines.append("  stdout:")
        lines.append(_indent_block(stdout.rstrip(), spaces=4))
    else:
        lines.append("  stdout: none")
    if stderr:
        lines.append("  stderr:")
        lines.append(_indent_block(stderr.rstrip(), spaces=4))
    else:
        lines.append("  stderr: none")
    lines.extend(format_structured_command_output_analysis_lines(analysis, spaces=2))
    return "\n".join(lines)


def get_run_sequence_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    commands: list[str] | None = None,
    cwd: str | None = None,
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
    return format_run_sequence_report_text(
        get_run_sequence_report(
            project_root,
            argument,
            commands=commands,
            cwd=cwd,
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


def get_run_sequence_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    commands: list[str] | None = None,
    cwd: str | None = None,
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

    def failure(message: str, selected_commands: list[str] | None = None) -> dict[str, object]:
        selected = list(selected_commands or [])
        return {
            "projectRoot": str(root),
            "ok": False,
            "commands": {"shown": 0, "total": len(selected), "requested": selected},
            "stopOnFailure": stop_on_failure,
            "stoppedEarly": False,
            "results": [],
            "message": message,
        }

    try:
        selected_commands = parse_run_sequence_request(argument, commands)
    except ValueError as error:
        return failure(f"Usage: /run-seq <cmd> ;; <cmd>\nError: {error}")
    if timeout_ms < 100:
        return failure("Usage: /run-seq <cmd> ;; <cmd>\nError: timeout_ms must be at least 100.", selected_commands)
    if timeout_ms > 600_000:
        return failure("Usage: /run-seq <cmd> ;; <cmd>\nError: timeout_ms must be at most 600000.", selected_commands)
    if max_output_chars < 1_000:
        return failure("Usage: /run-seq <cmd> ;; <cmd>\nError: max_output_chars must be at least 1000.", selected_commands)
    if max_output_chars > 50_000:
        return failure("Usage: /run-seq <cmd> ;; <cmd>\nError: max_output_chars must be at most 50000.", selected_commands)
    output_context_error = validate_run_output_context_options(
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
        usage="Usage: /run-seq <cmd> ;; <cmd>",
    )
    if output_context_error:
        return failure(output_context_error, selected_commands)

    workspace = RunWorkspace(root=root, run_id="local-run-sequence", session_dir=root / ".vibeagent" / "sessions" / "local-run-sequence")
    observation = _execute_action(
        workspace,
        RunCommandsAction(
            type="run_commands",
            commands=[
                RunCommandItem(
                    command=command,
                    cwd=cwd,
                    timeout_ms=timeout_ms,
                    max_output_chars=max_output_chars,
                    extract_output_contexts=extract_output_contexts,
                    extract_output_diagnostics=extract_output_diagnostics,
                    context_lines=context_lines,
                    max_diagnostics=max_diagnostics,
                    max_contexts=max_contexts,
                    max_bytes_per_context=max_bytes_per_context,
                )
                for command in selected_commands
            ],
            stop_on_failure=stop_on_failure,
        ),
        command_timeout_ms=timeout_ms,
    )
    if observation.kind != "run_commands":
        return failure(f"Unexpected observation: {observation.kind}", selected_commands)

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "commands": {
            "shown": len(observation.results),
            "total": len(selected_commands),
            "requested": selected_commands,
        },
        "stopOnFailure": stop_on_failure,
        "stoppedEarly": observation.stopped_early,
        "results": [serialize_command_result(result, index=index) for index, result in enumerate(observation.results, start=1)],
        "message": observation.message,
    }


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
        f"  commands: {int(commands.get('shown', len(results)) or 0)}/{int(commands.get('total', len(results)) or 0)}",
        f"  stopOnFailure: {'yes' if bool(report.get('stopOnFailure')) else 'no'}",
        f"  stoppedEarly: {'yes' if bool(report.get('stoppedEarly')) else 'no'}",
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
                    f"      exitCode: {result.get('exitCode') if result.get('exitCode') is not None else '.'}",
                    f"      timedOut: {'yes' if bool(result.get('timedOut')) else 'no'}",
                    f"      signal: {result.get('signal') or '.'}",
                    f"      timeoutMs: {result.get('timeoutMs', 0)}",
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


def validate_run_output_context_options(
    *,
    context_lines: int,
    max_diagnostics: int,
    max_contexts: int,
    max_bytes_per_context: int,
    usage: str,
) -> str | None:
    if context_lines < 0:
        return f"{usage}\nError: context_lines must be at least 0."
    if context_lines > 500:
        return f"{usage}\nError: context_lines must be at most 500."
    if max_diagnostics < 1:
        return f"{usage}\nError: max_diagnostics must be at least 1."
    if max_diagnostics > 200:
        return f"{usage}\nError: max_diagnostics must be at most 200."
    if max_contexts < 1:
        return f"{usage}\nError: max_contexts must be at least 1."
    if max_contexts > 100:
        return f"{usage}\nError: max_contexts must be at most 100."
    if max_bytes_per_context < 1_000:
        return f"{usage}\nError: max_bytes_per_context must be at least 1000."
    if max_bytes_per_context > 200_000:
        return f"{usage}\nError: max_bytes_per_context must be at most 200000."
    return None


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
                lines.append(_indent_block(context.content.rstrip(), spaces=spaces + 4))
            else:
                lines.append(f"{' ' * (spaces + 4)}{context.message}")
    return lines


def parse_run_sequence_request(argument: str | None = None, commands: list[str] | None = None) -> list[str]:
    if argument and commands is not None:
        raise ValueError("run-seq argument cannot be combined with explicit commands.")
    if commands is not None:
        selected = [command.strip() for command in commands if command.strip()]
    elif argument and argument.strip():
        selected = [part.strip() for part in argument.split(";;") if part.strip()]
    else:
        selected = []
    if not selected:
        raise ValueError("at least one command is required.")
    if len(selected) > 10:
        raise ValueError("expected at most 10 commands.")
    return selected


def serialize_command_check(check: object, index: int | None = None) -> dict[str, object]:
    item: dict[str, object] = {
        "command": str(getattr(check, "command", "") or ""),
        "cwd": str(getattr(check, "cwd", ".") or "."),
        "ok": bool(getattr(check, "ok", False)),
        "cwdOk": bool(getattr(check, "cwd_ok", False)),
        "blocked": bool(getattr(check, "blocked", False)),
        "executableAvailable": bool(getattr(check, "executable_available", False)),
        "blockReason": getattr(check, "block_reason", None),
        "missingTool": getattr(check, "missing_tool", None),
        "message": str(getattr(check, "message", "") or ""),
    }
    if index is not None:
        item["index"] = index
    return item


def get_check_run_sequence_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    commands: list[str] | None = None,
    cwd: str | None = None,
) -> str:
    return format_check_run_sequence_report_text(
        get_check_run_sequence_report(project_root, argument, commands=commands, cwd=cwd)
    )


def get_check_run_sequence_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    commands: list[str] | None = None,
    cwd: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str, selected_commands: list[str] | None = None) -> dict[str, object]:
        selected = list(selected_commands or [])
        return {
            "projectRoot": str(root),
            "ok": False,
            "commands": {"shown": 0, "total": len(selected), "requested": selected},
            "checks": [],
            "message": message,
        }

    try:
        selected_commands = parse_run_sequence_request(argument, commands)
    except ValueError as error:
        return failure(f"Usage: /check-run-seq <cmd> ;; <cmd>\nError: {error}")

    workspace = RunWorkspace(root=root, run_id="local-check-run-sequence", session_dir=root / ".vibeagent" / "sessions" / "local-check-run-sequence")
    observation = _execute_action(
        workspace,
        CheckRunCommandsAction(
            type="check_run_commands",
            commands=[RunCommandItem(command=command, cwd=cwd) for command in selected_commands],
        ),
    )
    if observation.kind != "check_run_commands":
        return failure(f"Unexpected observation: {observation.kind}", selected_commands)

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "commands": {
            "shown": len(observation.checks),
            "total": len(selected_commands),
            "requested": selected_commands,
        },
        "checks": [serialize_command_check(check, index=index) for index, check in enumerate(observation.checks, start=1)],
        "message": observation.message,
    }


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


def get_check_start_text(project_root: str | Path = ".", command: str | None = None, cwd: str | None = None) -> str:
    return format_check_start_report_text(get_check_start_report(project_root, command, cwd=cwd))


def get_check_start_report(project_root: str | Path = ".", command: str | None = None, cwd: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str) -> dict[str, object]:
        return {
            "projectRoot": str(root),
            "command": (command or "").strip(),
            "cwd": cwd or ".",
            "ok": False,
            "cwdOk": False,
            "blocked": False,
            "executableAvailable": False,
            "blockReason": None,
            "missingTool": None,
            "message": message,
        }

    if command is None or not command.strip():
        return failure("Usage: /check-start <shell command>")
    workspace = RunWorkspace(root=root, run_id="local-check-start", session_dir=root / ".vibeagent" / "sessions" / "local-check-start")
    observation = _execute_action(
        workspace,
        CheckStartCommandAction(type="check_start_command", command=command.strip(), cwd=cwd),
    )
    if observation.kind != "check_start_command":
        return failure(f"Unexpected observation: {observation.kind}")

    return {
        "projectRoot": str(root),
        **serialize_command_check(observation),
    }


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


def get_start_text(project_root: str | Path = ".", command: str | None = None, cwd: str | None = None) -> str:
    return format_start_report_text(get_start_report(project_root, command, cwd=cwd))


def get_start_report(project_root: str | Path = ".", command: str | None = None, cwd: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str) -> dict[str, object]:
        return {
            "projectRoot": str(root),
            "ok": False,
            "command": (command or "").strip(),
            "cwd": cwd or ".",
            "processId": "",
            "pid": None,
            "stdoutPath": "",
            "stderrPath": "",
            "message": message,
        }

    if command is None or not command.strip():
        return failure("Usage: /start <shell command>")

    workspace = RunWorkspace(root=root, run_id="local-start", session_dir=root / ".vibeagent" / "sessions" / "local-start")
    observation = _execute_action(
        workspace,
        StartCommandAction(type="start_command", command=command.strip(), cwd=cwd),
    )
    if observation.kind != "start_command":
        return failure(f"Unexpected observation: {observation.kind}")

    return {
        "projectRoot": str(root),
        "command": observation.command,
        "cwd": observation.cwd,
        "ok": observation.ok,
        "processId": observation.process_id,
        "pid": observation.pid,
        "stdoutPath": observation.stdout_path,
        "stderrPath": observation.stderr_path,
        "message": observation.message,
    }


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
            f"  message: {message}",
        ]
    )


def get_port_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    port: int | None = None,
    host: str = "127.0.0.1",
    timeout_ms: int = 1_000,
) -> str:
    return format_port_report_text(get_port_report(project_root, argument, port, host, timeout_ms))


def get_port_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    port: int | None = None,
    host: str = "127.0.0.1",
    timeout_ms: int = 1_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str, selected_port: int | None = port, selected_host: str = host, selected_timeout: int = timeout_ms) -> dict[str, object]:
        return {
            "projectRoot": str(root),
            "ok": False,
            "host": selected_host,
            "port": selected_port,
            "reachable": False,
            "timeoutMs": selected_timeout,
            "error": None,
            "message": message,
        }

    try:
        selected_port, selected_host, selected_timeout_ms = parse_port_request(argument, port, host, timeout_ms)
    except ValueError as error:
        return failure(f"Usage: /port <port> [host] [timeout-ms]\nError: {error}")
    if selected_timeout_ms < 100:
        return failure("Usage: /port <port> [host] [timeout-ms]\nError: timeout_ms must be at least 100.", selected_port, selected_host, selected_timeout_ms)
    if selected_timeout_ms > 600_000:
        return failure("Usage: /port <port> [host] [timeout-ms]\nError: timeout_ms must be at most 600000.", selected_port, selected_host, selected_timeout_ms)

    workspace = RunWorkspace(root=root, run_id="local-port", session_dir=root / ".vibeagent" / "sessions" / "local-port")
    observation = _execute_action(
        workspace,
        PortCheckAction(type="port_check", port=selected_port, host=selected_host, timeout_ms=selected_timeout_ms),
    )
    if observation.kind != "port_check":
        return failure(f"Unexpected observation: {observation.kind}", selected_port, selected_host, selected_timeout_ms)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "host": observation.host,
        "port": observation.port,
        "reachable": observation.reachable,
        "timeoutMs": observation.timeout_ms,
        "error": observation.error,
        "message": observation.message,
    }


def format_port_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        "Port:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  host: {report.get('host') or ''}",
        f"  port: {report.get('port') if report.get('port') is not None else '.'}",
        f"  reachable: {'yes' if bool(report.get('reachable')) else 'no'}",
        f"  timeoutMs: {int(report.get('timeoutMs', 0) or 0)}",
    ]
    if report.get("error"):
        lines.append(f"  error: {report.get('error')}")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def parse_port_request(
    argument: str | None = None,
    port: int | None = None,
    host: str = "127.0.0.1",
    timeout_ms: int = 1_000,
) -> tuple[int, str, int]:
    selected_port = port
    selected_host = host
    selected_timeout_ms = timeout_ms
    if argument and argument.strip():
        if port is not None:
            raise ValueError("port argument cannot be combined with explicit port.")
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if len(parts) > 3:
            raise ValueError("expected port, optional host, and optional timeout ms.")
        if parts:
            if not parts[0].isdigit():
                raise ValueError(f"invalid port: {parts[0]}")
            selected_port = int(parts[0])
        if len(parts) == 2:
            if parts[1].isdigit():
                selected_timeout_ms = int(parts[1])
            else:
                selected_host = parts[1]
        if len(parts) == 3:
            selected_host = parts[1]
            if not parts[2].isdigit():
                raise ValueError(f"invalid timeout ms: {parts[2]}")
            selected_timeout_ms = int(parts[2])
    if selected_port is None:
        raise ValueError("port is required.")
    if selected_port < 1 or selected_port > 65_535:
        raise ValueError("port must be between 1 and 65535.")
    if not selected_host.strip():
        raise ValueError("host must be a non-empty string.")
    return selected_port, selected_host.strip(), selected_timeout_ms


def get_http_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    url: str | None = None,
    contains: str | None = None,
    timeout_ms: int = 2_000,
    max_body_chars: int = 2_000,
    regex: bool = False,
) -> str:
    return format_http_report_text(get_http_report(project_root, argument, url, contains, timeout_ms, max_body_chars, regex))


def get_http_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    url: str | None = None,
    contains: str | None = None,
    timeout_ms: int = 2_000,
    max_body_chars: int = 2_000,
    regex: bool = False,
) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str, selected_url: str = url or "", selected_contains: str | None = contains) -> dict[str, object]:
        return {
            "projectRoot": str(root),
            "ok": False,
            "url": selected_url,
            "finalUrl": None,
            "status": None,
            "reason": None,
            "reachable": False,
            "matched": False,
            "matchedPattern": selected_contains,
            "timeoutMs": timeout_ms,
            "maxBodyChars": max_body_chars,
            "body": "",
            "bodyTruncated": False,
            "error": None,
            "message": message,
        }

    try:
        selected_url, selected_contains = parse_http_request(argument, url, contains)
    except ValueError as error:
        return failure(f"Usage: /http <url> [contains]\nError: {error}")
    if timeout_ms < 100:
        return failure("Usage: /http <url> [contains]\nError: timeout_ms must be at least 100.", selected_url, selected_contains)
    if timeout_ms > 600_000:
        return failure("Usage: /http <url> [contains]\nError: timeout_ms must be at most 600000.", selected_url, selected_contains)
    if max_body_chars < 0:
        return failure("Usage: /http <url> [contains]\nError: max_body_chars must be non-negative.", selected_url, selected_contains)
    if max_body_chars > 50_000:
        return failure("Usage: /http <url> [contains]\nError: max_body_chars must be at most 50000.", selected_url, selected_contains)

    workspace = RunWorkspace(root=root, run_id="local-http", session_dir=root / ".vibeagent" / "sessions" / "local-http")
    observation = _execute_action(
        workspace,
        HttpCheckAction(
            type="http_check",
            url=selected_url,
            timeout_ms=timeout_ms,
            max_body_chars=max_body_chars,
            contains=selected_contains,
            regex=regex,
        ),
    )
    if observation.kind != "http_check":
        return failure(f"Unexpected observation: {observation.kind}", selected_url, selected_contains)
    return serialize_http_report(root, observation)


def format_http_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        "HTTP:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  url: {report.get('url') or ''}",
        f"  finalUrl: {report.get('finalUrl') or '.'}",
        f"  status: {report.get('status') if report.get('status') is not None else '.'}",
        f"  reason: {report.get('reason') or '.'}",
        f"  reachable: {'yes' if bool(report.get('reachable')) else 'no'}",
        f"  matched: {'yes' if bool(report.get('matched')) else 'no'}",
        f"  matchedPattern: {report.get('matchedPattern') or '.'}",
        f"  timeoutMs: {int(report.get('timeoutMs', 0) or 0)}",
        f"  maxBodyChars: {int(report.get('maxBodyChars', 0) or 0)}",
        f"  bodyTruncated: {'yes' if bool(report.get('bodyTruncated')) else 'no'}",
    ]
    if report.get("error"):
        lines.append(f"  error: {report.get('error')}")
    lines.append(f"  message: {message}")
    body = str(report.get("body") or "")
    if body:
        lines.append("  body:")
        lines.append(_indent_block(body.rstrip(), spaces=4))
    else:
        lines.append("  body: none")
    return "\n".join(lines)


def serialize_http_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok", False)),
        "url": str(getattr(observation, "url", "") or ""),
        "finalUrl": getattr(observation, "final_url", None),
        "status": getattr(observation, "status", None),
        "reason": getattr(observation, "reason", None),
        "reachable": bool(getattr(observation, "reachable", False)),
        "matched": bool(getattr(observation, "matched", False)),
        "matchedPattern": getattr(observation, "matched_pattern", None),
        "timeoutMs": int(getattr(observation, "timeout_ms", 0) or 0),
        "maxBodyChars": int(getattr(observation, "max_body_chars", 0) or 0),
        "body": str(getattr(observation, "body", "") or ""),
        "bodyTruncated": bool(getattr(observation, "body_truncated", False)),
        "error": getattr(observation, "error", None),
        "message": str(getattr(observation, "message", "") or ""),
    }


def get_http_fetch_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    url: str | None = None,
    timeout_ms: int = 5_000,
    max_body_chars: int = 12_000,
) -> str:
    return format_http_fetch_report_text(get_http_fetch_report(project_root, argument, url, timeout_ms, max_body_chars))


def get_http_fetch_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    url: str | None = None,
    timeout_ms: int = 5_000,
    max_body_chars: int = 12_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str, selected_url: str = url or "") -> dict[str, object]:
        return {
            "projectRoot": str(root),
            "ok": False,
            "url": selected_url,
            "finalUrl": None,
            "status": None,
            "reason": None,
            "contentType": None,
            "reachable": False,
            "timeoutMs": timeout_ms,
            "maxBodyChars": max_body_chars,
            "body": "",
            "bodyTruncated": False,
            "error": None,
            "message": message,
        }

    try:
        selected_url = parse_http_fetch_request(argument, url)
    except ValueError as error:
        return failure(f"Usage: /http-fetch <url>\nError: {error}")
    if timeout_ms < 100:
        return failure("Usage: /http-fetch <url>\nError: timeout_ms must be at least 100.", selected_url)
    if timeout_ms > 600_000:
        return failure("Usage: /http-fetch <url>\nError: timeout_ms must be at most 600000.", selected_url)
    if max_body_chars < 1:
        return failure("Usage: /http-fetch <url>\nError: max_body_chars must be at least 1.", selected_url)
    if max_body_chars > 100_000:
        return failure("Usage: /http-fetch <url>\nError: max_body_chars must be at most 100000.", selected_url)

    workspace = RunWorkspace(root=root, run_id="local-http-fetch", session_dir=root / ".vibeagent" / "sessions" / "local-http-fetch")
    observation = _execute_action(
        workspace,
        HttpFetchAction(
            type="http_fetch",
            url=selected_url,
            timeout_ms=timeout_ms,
            max_body_chars=max_body_chars,
        ),
    )
    if observation.kind != "http_fetch":
        return failure(f"Unexpected observation: {observation.kind}", selected_url)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "url": observation.url,
        "finalUrl": observation.final_url,
        "status": observation.status,
        "reason": observation.reason,
        "contentType": observation.content_type,
        "reachable": observation.reachable,
        "timeoutMs": observation.timeout_ms,
        "maxBodyChars": observation.max_body_chars,
        "body": observation.body,
        "bodyTruncated": observation.body_truncated,
        "error": observation.error,
        "message": observation.message,
    }


def format_http_fetch_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        "HTTP fetch:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  url: {report.get('url') or ''}",
        f"  finalUrl: {report.get('finalUrl') or '.'}",
        f"  status: {report.get('status') if report.get('status') is not None else '.'}",
        f"  reason: {report.get('reason') or '.'}",
        f"  contentType: {report.get('contentType') or '.'}",
        f"  reachable: {'yes' if bool(report.get('reachable')) else 'no'}",
        f"  timeoutMs: {int(report.get('timeoutMs', 0) or 0)}",
        f"  maxBodyChars: {int(report.get('maxBodyChars', 0) or 0)}",
        f"  bodyTruncated: {'yes' if bool(report.get('bodyTruncated')) else 'no'}",
    ]
    if report.get("error"):
        lines.append(f"  error: {report.get('error')}")
    lines.append(f"  message: {message}")
    body = str(report.get("body") or "")
    if body:
        lines.append("  body:")
        lines.append(_indent_block(body.rstrip(), spaces=4))
    else:
        lines.append("  body: none")
    return "\n".join(lines)


def parse_http_fetch_request(argument: str | None = None, url: str | None = None) -> str:
    selected_url = url.strip() if url else None
    if argument and argument.strip():
        if url is not None:
            raise ValueError("http-fetch argument cannot be combined with explicit url.")
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if len(parts) > 1:
            raise ValueError("http-fetch accepts only one URL.")
        selected_url = parts[0] if parts else None
    if not selected_url:
        raise ValueError("url is required.")
    parsed = urlparse(selected_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be an http or https URL.")
    return selected_url


def parse_http_request(argument: str | None = None, url: str | None = None, contains: str | None = None) -> tuple[str, str | None]:
    selected_url = url.strip() if url else None
    selected_contains = contains
    if argument and argument.strip():
        if url is not None or contains is not None:
            raise ValueError("http argument cannot be combined with explicit url or contains.")
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if not parts:
            raise ValueError("url is required.")
        selected_url = parts[0]
        selected_contains = " ".join(parts[1:]) if len(parts) > 1 else None
    if not selected_url:
        raise ValueError("url is required.")
    if not (selected_url.startswith("http://") or selected_url.startswith("https://")):
        raise ValueError("url must be an http or https URL.")
    if selected_contains is not None and not selected_contains:
        raise ValueError("contains must be a non-empty string.")
    return selected_url, selected_contains
