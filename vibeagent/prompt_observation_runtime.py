from __future__ import annotations

from .prompt_observation_output import (
    format_command_output_contexts,
    format_command_output_diagnostics,
)
from .prompt_observation_utils import truncate


def format_runtime_observation(index: int, observation: object) -> str | None:
    if observation.kind in {"command_check", "check_start_command"}:
        return "\n".join(
            [
                f"{index}. {observation.kind}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"command: {observation.command}",
                f"cwd: {observation.cwd}",
                f"cwdOk: {str(observation.cwd_ok).lower()}",
                f"blocked: {str(observation.blocked).lower()}",
                f"blockReason: {observation.block_reason or 'none'}",
                f"executableAvailable: {str(observation.executable_available).lower()}",
                f"missingTool: {observation.missing_tool or 'none'}",
            ]
        )

    if observation.kind == "check_run_commands":
        parts = [
            f"{index}. check_run_commands: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
        ]
        for check in observation.checks:
            parts.extend(
                [
                    f"command: {check.command}",
                    f"cwd: {check.cwd}",
                    f"ok: {str(check.ok).lower()} cwdOk={str(check.cwd_ok).lower()} blocked={str(check.blocked).lower()} executableAvailable={str(check.executable_available).lower()}",
                    f"blockReason: {check.block_reason or 'none'} missingTool={check.missing_tool or 'none'} message={check.message}",
                ]
            )
        return "\n".join(parts)

    if observation.kind == "port_check":
        return "\n".join(
            [
                f"{index}. port_check {observation.host}:{observation.port}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"reachable: {str(observation.reachable).lower()}",
                f"timeoutMs: {observation.timeout_ms}",
                f"error: {observation.error or 'none'}",
            ]
        )

    if observation.kind == "http_check":
        parts = [
            f"{index}. http_check {observation.url}: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
            f"reachable: {str(observation.reachable).lower()}",
            f"status: {observation.status if observation.status is not None else 'none'}",
            f"reason: {observation.reason or 'none'}",
            f"finalUrl: {observation.final_url or 'none'}",
            f"timeoutMs: {observation.timeout_ms}",
            f"matched: {str(observation.matched).lower()}",
            f"matchedPattern: {observation.matched_pattern or 'none'}",
            f"bodyTruncated: {str(observation.body_truncated).lower()}",
            f"maxBodyChars: {observation.max_body_chars}",
            f"error: {observation.error or 'none'}",
        ]
        if observation.body:
            parts.append(f"body:\n{observation.body}")
        return "\n".join(parts)

    if observation.kind == "http_fetch":
        parts = [
            f"{index}. http_fetch {observation.url}: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
            f"reachable: {str(observation.reachable).lower()}",
            f"status: {observation.status if observation.status is not None else 'none'}",
            f"reason: {observation.reason or 'none'}",
            f"contentType: {observation.content_type or 'none'}",
            f"finalUrl: {observation.final_url or 'none'}",
            f"timeoutMs: {observation.timeout_ms}",
            f"bodyTruncated: {str(observation.body_truncated).lower()}",
            f"maxBodyChars: {observation.max_body_chars}",
            f"error: {observation.error or 'none'}",
        ]
        if observation.body:
            parts.append(f"body:\n{observation.body}")
        return "\n".join(parts)

    if observation.kind == "web_fetch":
        parts = [
            f"{index}. web_fetch {observation.url}: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
            f"status: {observation.status if observation.status is not None else 'none'}",
            f"contentType: {observation.content_type or 'none'}",
            f"title: {observation.title or 'none'}",
            f"finalUrl: {observation.final_url or 'none'}",
            f"textTruncated: {str(observation.text_truncated).lower()}",
            f"maxTextChars: {observation.max_text_chars}",
            f"error: {observation.error or 'none'}",
        ]
        if observation.prompt:
            parts.append(f"prompt: {observation.prompt}")
        if observation.text:
            parts.append(f"text:\n{observation.text}")
        return "\n".join(parts)

    if observation.kind == "environment_info":
        parts = [
            (
                f"{index}. environment_info: {observation.message} "
                f"ok={str(observation.ok).lower()} "
                f"projectRoot={observation.project_root} "
                f"python={observation.python_version} "
                f"platform={observation.platform} "
                f"gitRepo={str(observation.is_git_repo).lower()}"
            ),
            f"pythonExecutable: {observation.python_executable or 'unknown'}",
        ]
        for tool in observation.tools:
            parts.append(
                (
                    f"tool: {tool.name} available={str(tool.available).lower()} "
                    f"path={tool.path or '.'} version={tool.version or '.'} message={tool.message}"
                )
            )
        return "\n".join(parts)

    if observation.kind == "start_command":
        return "\n".join(
            [
                f"{index}. start_command: {observation.message}",
                f"processId: {observation.process_id or 'none'}",
                f"pid: {observation.pid or 'none'}",
                f"command: {observation.command}",
                f"cwd: {observation.cwd}",
                f"stdoutPath: {observation.stdout_path or 'none'}",
                f"stderrPath: {observation.stderr_path or 'none'}",
            ]
        )

    if observation.kind == "read_process":
        return "\n".join(
            [
                f"{index}. read_process {observation.process_id}: {observation.message}",
                f"pid: {observation.pid or 'none'}",
                f"running: {str(observation.running).lower()}",
                f"exitCode: {observation.exit_code}",
                f"signal: {observation.signal or 'none'}",
                f"maxOutputChars: {observation.max_output_chars}",
                f"stdout:\n{truncate(observation.stdout)}",
                f"stderr:\n{truncate(observation.stderr)}",
                format_command_output_diagnostics(observation),
                format_command_output_contexts(observation),
            ]
        )

    if observation.kind == "process_output_contexts":
        parts = [
            f"{index}. process_output_contexts {observation.process_id}: {observation.message}",
            f"pid: {observation.pid or 'none'}",
            f"ok: {str(observation.ok).lower()}",
            f"running: {str(observation.running).lower()}",
            f"contexts: {len(observation.contexts)}/{observation.total_refs}",
            f"truncated: {str(observation.truncated).lower()}",
            f"stdoutChars: {observation.stdout_chars}",
            f"stderrChars: {observation.stderr_chars}",
            f"maxOutputChars: {observation.max_output_chars}",
        ]
        for item in observation.contexts:
            column = f":{item.column}" if item.column is not None else ""
            parts.append(
                (
                    f"context: {item.path}:{item.line}{column} raw={item.raw!r} "
                    f"ok={str(item.ok).lower()} range={item.start_line}:{item.end_line} "
                    f"contextLines={item.context_lines} message={item.message}"
                )
            )
            if item.ok:
                parts.append(f"content:\n{truncate(item.content)}")
        return "\n".join(parts)

    if observation.kind == "process_output_diagnostics":
        parts = [
            f"{index}. process_output_diagnostics {observation.process_id}: {observation.message}",
            f"pid: {observation.pid or 'none'}",
            f"ok: {str(observation.ok).lower()}",
            f"running: {str(observation.running).lower()}",
            f"diagnostics: {len(observation.diagnostics)}/{observation.total_diagnostics}",
            f"contexts: {len(observation.contexts)}/{observation.total_refs}",
            f"diagnosticsTruncated: {str(observation.diagnostics_truncated).lower()}",
            f"contextsTruncated: {str(observation.contexts_truncated).lower()}",
            f"stdoutChars: {observation.stdout_chars}",
            f"stderrChars: {observation.stderr_chars}",
            f"maxOutputChars: {observation.max_output_chars}",
        ]
        for diagnostic in observation.diagnostics:
            location = ""
            if diagnostic.path:
                location = f" location={diagnostic.path}:{diagnostic.line if diagnostic.line is not None else '?'}"
                if diagnostic.column is not None:
                    location += f":{diagnostic.column}"
            parts.append(
                (
                    f"diagnostic: severity={diagnostic.severity} outputLine={diagnostic.output_line}"
                    f"{location} raw={diagnostic.raw!r} text={diagnostic.text}"
                )
            )
        for item in observation.contexts:
            column = f":{item.column}" if item.column is not None else ""
            parts.append(
                (
                    f"context: {item.path}:{item.line}{column} raw={item.raw!r} "
                    f"ok={str(item.ok).lower()} range={item.start_line}:{item.end_line} "
                    f"contextLines={item.context_lines} message={item.message}"
                )
            )
            if item.ok:
                parts.append(f"content:\n{truncate(item.content)}")
        return "\n".join(parts)

    if observation.kind == "wait_process":
        return "\n".join(
            [
                f"{index}. wait_process {observation.process_id}: {observation.message}",
                f"pid: {observation.pid or 'none'}",
                f"running: {str(observation.running).lower()}",
                f"timedOut: {str(observation.timed_out).lower()}",
                f"matched: {str(observation.matched).lower()}",
                f"matchedStream: {observation.matched_stream or 'none'}",
                f"matchedPattern: {observation.matched_pattern or 'none'}",
                f"timeoutMs: {observation.timeout_ms}",
                f"exitCode: {observation.exit_code}",
                f"signal: {observation.signal or 'none'}",
                f"maxOutputChars: {observation.max_output_chars}",
                f"stdout:\n{truncate(observation.stdout)}",
                f"stderr:\n{truncate(observation.stderr)}",
                format_command_output_diagnostics(observation),
                format_command_output_contexts(observation),
            ]
        )

    if observation.kind in {"check_write_process", "write_process"}:
        return "\n".join(
            [
                f"{index}. {observation.kind} {observation.process_id}: {observation.message}",
                f"pid: {observation.pid or 'none'}",
                f"ok: {str(observation.ok).lower()}",
                f"running: {str(observation.running).lower()}",
                f"cwd: {observation.cwd or 'none'}",
                f"contentChars: {observation.content_chars}",
                f"command: {observation.command or 'none'}",
            ]
        )

    if observation.kind == "list_processes":
        process_lines = [
            (
                f"- {process.process_id} pid={process.pid} cwd={process.cwd} running={str(process.running).lower()} "
                f"exitCode={process.exit_code} signal={process.signal or 'none'} command={process.command}"
            )
            for process in observation.processes
        ]
        return "\n".join([f"{index}. list_processes: {observation.message}", *process_lines])

    if observation.kind == "check_stop_all_processes":
        process_lines = [
            (
                f"- {process.process_id} pid={process.pid} cwd={process.cwd} running={str(process.running).lower()} "
                f"exitCode={process.exit_code} signal={process.signal or 'none'} command={process.command}"
            )
            for process in observation.processes
        ]
        return "\n".join(
            [
                f"{index}. check_stop_all_processes: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"runningCount: {observation.running_count}",
                *process_lines,
            ]
        )

    if observation.kind == "check_stop_process":
        return "\n".join(
            [
                f"{index}. check_stop_process {observation.process_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"pid: {observation.pid or 'none'}",
                f"running: {str(observation.running).lower()}",
                f"exitCode: {observation.exit_code}",
                f"signal: {observation.signal or 'none'}",
                f"cwd: {observation.cwd or 'none'}",
                f"command: {observation.command or 'none'}",
            ]
        )

    if observation.kind == "stop_all_processes":
        stopped_lines = [
            (
                f"- {process.process_id} pid={process.pid} cwd={process.cwd} ok={str(process.ok).lower()} "
                f"exitCode={process.exit_code} signal={process.signal or 'none'} command={process.command}"
            )
            for process in observation.stopped
        ]
        return "\n".join(
            [
                f"{index}. stop_all_processes: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                *stopped_lines,
            ]
        )

    if observation.kind == "stop_process":
        return "\n".join(
            [
                f"{index}. stop_process {observation.process_id}: {observation.message}",
                f"pid: {observation.pid or 'none'}",
                f"exitCode: {observation.exit_code}",
                f"signal: {observation.signal or 'none'}",
            ]
        )

    if observation.kind in {"run_commands", "run_suggested_checks", "run_focused_test_commands"}:
        return _format_multi_command_observation(index, observation)

    if observation.kind == "run_command":
        result = observation.result
        return "\n".join(
            [
                f"{index}. run_command: {result.command}",
                f"cwd: {result.cwd}",
                f"exitCode: {result.exit_code}",
                f"timedOut: {str(result.timed_out).lower()}",
                f"timeoutMs: {result.timeout_ms}",
                f"durationMs: {result.duration_ms}",
                f"maxOutputChars: {result.max_output_chars}",
                f"stdoutTruncated: {str(result.stdout_truncated).lower()}",
                f"stderrTruncated: {str(result.stderr_truncated).lower()}",
                f"signal: {result.signal or 'none'}",
                f"stdout:\n{truncate(result.stdout)}",
                f"stderr:\n{truncate(result.stderr)}",
                format_command_output_diagnostics(result),
                format_command_output_contexts(result),
            ]
        )

    return None


def _not_run_multi_command_labels(observation: object) -> list[str]:
    if observation.kind == "run_suggested_checks":
        commands = getattr(observation, "suggested_checks", [])
    elif observation.kind == "run_focused_test_commands":
        commands = getattr(observation, "focused_commands", [])
    else:
        return []
    results = getattr(observation, "results", [])
    if not getattr(observation, "stopped_early", False) or not isinstance(commands, list) or not isinstance(results, list):
        return []

    labels: list[str] = []
    for command in commands[len(results) :]:
        value = str(getattr(command, "command", "") or "").strip()
        cwd = str(getattr(command, "cwd", ".") or ".").strip() or "."
        if value:
            labels.append(_format_not_run_command_label(command, value=value, cwd=cwd))
    return labels


def _format_not_run_command_label(command: object, *, value: str, cwd: str) -> str:
    source = str(getattr(command, "source", "") or "").strip() or "."
    reason = str(getattr(command, "reason", "") or "").strip() or "."
    available = str(bool(getattr(command, "available", True))).lower()
    missing_tool = str(getattr(command, "missing_tool", "") or "none").strip() or "none"
    return (
        f"{value} (cwd: {cwd}) "
        f"source={source} available={available} missingTool={missing_tool} reason={reason}"
    )


def _format_multi_command_observation(index: int, observation: object) -> str:
    parts = [
        f"{index}. {observation.kind}: {observation.message}",
        f"ok: {str(observation.ok).lower()}",
    ]
    if observation.kind == "run_suggested_checks":
        parts.extend(
            [
                f"suggested: {len(observation.suggested_checks)}/{observation.total}",
                f"truncated: {str(observation.truncated).lower()}",
                f"skippedUnavailable: {observation.skipped_unavailable}",
            ]
        )
    elif observation.kind == "run_focused_test_commands":
        parts.extend(
            [
                f"focused: {len(observation.focused_commands)}/{observation.total}",
                f"truncated: {str(observation.truncated).lower()}",
                f"skippedUnavailable: {observation.skipped_unavailable}",
            ]
        )
        if observation.target_paths:
            parts.append("target_paths:\n" + "\n".join(observation.target_paths[:120]))
    parts.append(f"stoppedEarly: {str(observation.stopped_early).lower()}")
    not_run = _not_run_multi_command_labels(observation)
    if not_run:
        parts.append(f"selectedCommandsNotRun: {len(not_run)}")
        parts.extend(f"notRun: {label}" for label in not_run[:20])
    for result in observation.results:
        parts.extend(
            [
                f"command: {result.command}",
                f"cwd: {result.cwd}",
                f"exitCode: {result.exit_code}",
                f"timedOut: {str(result.timed_out).lower()}",
                f"timeoutMs: {result.timeout_ms}",
                f"durationMs: {result.duration_ms}",
                f"maxOutputChars: {result.max_output_chars}",
                f"stdoutTruncated: {str(result.stdout_truncated).lower()} stderrTruncated={str(result.stderr_truncated).lower()} signal={result.signal or 'none'}",
                f"stdout:\n{truncate(result.stdout)}",
                f"stderr:\n{truncate(result.stderr)}",
                format_command_output_diagnostics(result),
                format_command_output_contexts(result),
            ]
        )
    return "\n".join(parts)


__all__ = ["format_runtime_observation"]
