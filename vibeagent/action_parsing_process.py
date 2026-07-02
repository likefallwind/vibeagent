from __future__ import annotations

from typing import Any

from .action_parsing_helpers import (
    ActionParseError,
    parse_nonnegative_int,
    parse_optional_positive_int,
    parse_run_command_items,
)
from .types import (
    CheckStartCommandAction,
    CheckStopAllProcessesAction,
    CheckStopProcessAction,
    CheckWriteProcessAction,
    ListProcessesAction,
    ProcessOutputContextsAction,
    ProcessOutputDiagnosticsAction,
    ReadProcessAction,
    RunCommandAction,
    RunCommandsAction,
    StartCommandAction,
    StopAllProcessesAction,
    StopProcessAction,
    WaitProcessAction,
    WriteProcessAction,
)


PROCESS_ACTION_TYPES = {
    "run_command",
    "run_commands",
    "check_start_command",
    "start_command",
    "read_process",
    "process_output_contexts",
    "process_output_diagnostics",
    "wait_process",
    "check_write_process",
    "write_process",
    "list_processes",
    "check_stop_all_processes",
    "check_stop_process",
    "stop_all_processes",
    "stop_process",
}


def _parse_command(value: Any, raw: str, action_type: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty command.", raw)
    return value


def _parse_process_id(value: Any, raw: str, action_type: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty process_id.", raw)
    return value


def _parse_timeout_ms(value: Any, raw: str) -> int | None:
    timeout_ms = parse_optional_positive_int(value, "timeout_ms", raw, maximum=600_000)
    if timeout_ms is not None and timeout_ms < 100:
        raise ActionParseError("timeout_ms must be at least 100.", raw)
    return timeout_ms


def _parse_optional_command_output_chars(value: Any, raw: str) -> int | None:
    max_output_chars = parse_optional_positive_int(value, "max_output_chars", raw, maximum=50_000)
    if max_output_chars is not None and max_output_chars < 1_000:
        raise ActionParseError("max_output_chars must be at least 1000.", raw)
    return max_output_chars


def _parse_bounded_output_chars(value: Any, raw: str, maximum: int) -> int:
    if not isinstance(value, int):
        raise ActionParseError("max_output_chars must be an integer.", raw)
    if value < 0:
        raise ActionParseError("max_output_chars must be at least 0.", raw)
    if value > maximum:
        raise ActionParseError(f"max_output_chars must be at most {maximum}.", raw)
    return value


def _parse_output_context_options(
    value: dict[str, Any],
    raw: str,
    default_context_lines: int,
) -> tuple[int, int, int]:
    context_lines = parse_nonnegative_int(value.get("context_lines", default_context_lines), "context_lines", raw, maximum=500)
    max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
    max_bytes_per_context = parse_optional_positive_int(
        value.get("max_bytes_per_context", 20_000),
        "max_bytes_per_context",
        raw,
        maximum=200_000,
    ) or 20_000
    if max_bytes_per_context < 1000:
        raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
    return context_lines, max_contexts, max_bytes_per_context


def parse_process_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in PROCESS_ACTION_TYPES:
        return None

    if action_type == "run_command":
        command = _parse_command(value.get("command"), raw, "run_command")
        cwd = value.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise ActionParseError("run_command action cwd must be a string when provided.", raw)
        extract_output_contexts = value.get("extract_output_contexts", False)
        if not isinstance(extract_output_contexts, bool):
            raise ActionParseError("run_command action extract_output_contexts must be a boolean.", raw)
        extract_output_diagnostics = value.get("extract_output_diagnostics", False)
        if not isinstance(extract_output_diagnostics, bool):
            raise ActionParseError("run_command action extract_output_diagnostics must be a boolean.", raw)
        context_lines, max_contexts, max_bytes_per_context = _parse_output_context_options(
            value,
            raw,
            default_context_lines=5,
        )
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
        return RunCommandAction(
            type="run_command",
            command=command,
            timeout_ms=_parse_timeout_ms(value.get("timeout_ms"), raw),
            cwd=cwd,
            max_output_chars=_parse_optional_command_output_chars(value.get("max_output_chars"), raw),
            extract_output_contexts=extract_output_contexts,
            extract_output_diagnostics=extract_output_diagnostics,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "run_commands":
        stop_on_failure = value.get("stop_on_failure", True)
        if not isinstance(stop_on_failure, bool):
            raise ActionParseError("run_commands action stop_on_failure must be a boolean when provided.", raw)
        return RunCommandsAction(
            type="run_commands",
            commands=parse_run_command_items(value.get("commands"), raw, "run_commands"),
            stop_on_failure=stop_on_failure,
        )

    if action_type == "check_start_command":
        command = _parse_command(value.get("command"), raw, "check_start_command")
        cwd = value.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise ActionParseError("check_start_command action cwd must be a string when provided.", raw)
        return CheckStartCommandAction(type="check_start_command", command=command, cwd=cwd)

    if action_type == "start_command":
        command = _parse_command(value.get("command"), raw, "start_command")
        cwd = value.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise ActionParseError("start_command action cwd must be a string when provided.", raw)
        return StartCommandAction(type="start_command", command=command, cwd=cwd)

    if action_type == "read_process":
        return ReadProcessAction(
            type="read_process",
            process_id=_parse_process_id(value.get("process_id"), raw, "read_process"),
            max_output_chars=_parse_optional_command_output_chars(value.get("max_output_chars"), raw),
        )

    if action_type == "process_output_contexts":
        context_lines, max_contexts, max_bytes_per_context = _parse_output_context_options(
            value,
            raw,
            default_context_lines=5,
        )
        return ProcessOutputContextsAction(
            type="process_output_contexts",
            process_id=_parse_process_id(value.get("process_id"), raw, "process_output_contexts"),
            max_output_chars=_parse_bounded_output_chars(value.get("max_output_chars", 20_000), raw, maximum=50_000),
            context_lines=context_lines,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "process_output_diagnostics":
        context_lines, max_contexts, max_bytes_per_context = _parse_output_context_options(
            value,
            raw,
            default_context_lines=2,
        )
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
        return ProcessOutputDiagnosticsAction(
            type="process_output_diagnostics",
            process_id=_parse_process_id(value.get("process_id"), raw, "process_output_diagnostics"),
            max_output_chars=_parse_bounded_output_chars(value.get("max_output_chars", 20_000), raw, maximum=50_000),
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "wait_process":
        process_id = _parse_process_id(value.get("process_id"), raw, "wait_process")
        stdout_contains = value.get("stdout_contains")
        stderr_contains = value.get("stderr_contains")
        regex = value.get("regex", False)
        if stdout_contains is not None and (not isinstance(stdout_contains, str) or not stdout_contains.strip()):
            raise ActionParseError("wait_process action stdout_contains must be a non-empty string when provided.", raw)
        if stderr_contains is not None and (not isinstance(stderr_contains, str) or not stderr_contains.strip()):
            raise ActionParseError("wait_process action stderr_contains must be a non-empty string when provided.", raw)
        if not isinstance(regex, bool):
            raise ActionParseError("wait_process action regex must be a boolean when provided.", raw)
        return WaitProcessAction(
            type="wait_process",
            process_id=process_id,
            timeout_ms=_parse_timeout_ms(value.get("timeout_ms"), raw),
            stdout_contains=stdout_contains,
            stderr_contains=stderr_contains,
            regex=regex,
            max_output_chars=_parse_optional_command_output_chars(value.get("max_output_chars"), raw),
        )

    if action_type == "check_write_process":
        process_id = _parse_process_id(value.get("process_id"), raw, "check_write_process")
        content = value.get("content")
        if not isinstance(content, str) or content == "":
            raise ActionParseError("check_write_process action requires non-empty content.", raw)
        return CheckWriteProcessAction(type="check_write_process", process_id=process_id, content=content)

    if action_type == "write_process":
        process_id = _parse_process_id(value.get("process_id"), raw, "write_process")
        content = value.get("content")
        if not isinstance(content, str) or content == "":
            raise ActionParseError("write_process action requires non-empty content.", raw)
        return WriteProcessAction(type="write_process", process_id=process_id, content=content)

    if action_type == "list_processes":
        return ListProcessesAction(type="list_processes")

    if action_type == "check_stop_all_processes":
        return CheckStopAllProcessesAction(type="check_stop_all_processes")

    if action_type == "check_stop_process":
        return CheckStopProcessAction(
            type="check_stop_process",
            process_id=_parse_process_id(value.get("process_id"), raw, "check_stop_process"),
        )

    if action_type == "stop_all_processes":
        return StopAllProcessesAction(type="stop_all_processes")

    if action_type == "stop_process":
        return StopProcessAction(
            type="stop_process",
            process_id=_parse_process_id(value.get("process_id"), raw, "stop_process"),
        )

    raise AssertionError(f"Unhandled process action type: {action_type!r}")
