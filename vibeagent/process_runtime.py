from __future__ import annotations

import json
import os
import re
import shlex
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .command_safety import get_blocked_command_reason
from .types import (
    CheckStopAllProcessesObservation,
    CheckStopProcessObservation,
    CheckWriteProcessObservation,
    CommandResult,
    ListProcessesObservation,
    OutputContextResult,
    OutputDiagnostic,
    ProcessInfo,
    ProcessOutputContextsAction,
    ProcessOutputContextsObservation,
    ProcessOutputDiagnosticsAction,
    ProcessOutputDiagnosticsObservation,
    ReadProcessObservation,
    RunCommandAction,
    RunCommandItem,
    StartCommandObservation,
    StopAllProcessesObservation,
    StopProcessObservation,
    StoppedProcessInfo,
    WaitProcessObservation,
    WriteProcessObservation,
)
from .workspace_core import RunWorkspace
from .workspace_resolve import resolve_command_cwd
from .workspace import read_output_contexts_result, read_output_diagnostics_result


@dataclass
class BackgroundProcess:
    id: str
    command: str
    cwd: str
    process: subprocess.Popen[str]
    stdout_path: Path
    stderr_path: Path
    exit_code_path: Path
    stdout_handle: Any
    stderr_handle: Any


@dataclass(frozen=True)
class PersistentProcessRecord:
    id: str
    command: str
    cwd: str
    pid: int
    stdout_path: Path
    stderr_path: Path
    exit_code_path: Path | None = None
    start_ticks: int | None = None


BACKGROUND_PROCESSES: dict[str, BackgroundProcess] = {}


def output_context_results_from_dicts(items: object) -> list[OutputContextResult]:
    if not isinstance(items, list):
        return []
    results: list[OutputContextResult] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        results.append(
            OutputContextResult(
                path=str(item["path"]),
                line=int(item["line"]),
                column=int(item["column"]) if item["column"] is not None else None,
                raw=str(item["raw"]),
                ok=bool(item["ok"]),
                content=str(item["content"]),
                message=str(item["message"]),
                context_lines=int(item["context_lines"]),
                start_line=int(item["start_line"]),
                end_line=int(item["end_line"]),
                line_count=int(item["line_count"]),
                total_lines=int(item["total_lines"]) if item["total_lines"] is not None else None,
                target_line_exists=bool(item["target_line_exists"]),
                truncated=bool(item["truncated"]),
                max_bytes=int(item["max_bytes"]),
            )
        )
    return results


def output_diagnostics_from_dicts(items: object) -> list[OutputDiagnostic]:
    if not isinstance(items, list):
        return []
    diagnostics: list[OutputDiagnostic] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity") or "info")
        if severity not in {"error", "warning", "failure", "info"}:
            severity = "info"
        diagnostics.append(
            OutputDiagnostic(
                severity=severity,  # type: ignore[arg-type]
                output_line=int(item["output_line"]),
                text=str(item["text"]),
                path=str(item["path"]) if item.get("path") is not None else None,
                line=int(item["line"]) if item.get("line") is not None else None,
                column=int(item["column"]) if item.get("column") is not None else None,
                raw=str(item["raw"]) if item.get("raw") is not None else None,
            )
        )
    return diagnostics


def run_command(
    cwd: str | Path,
    command: str,
    timeout_ms: int = 30_000,
    project_root: str | Path | None = None,
    max_output_chars: int = 12_000,
) -> CommandResult:
    # Run shell command in controlled cwd, capture stdout/stderr, and enforce execution timeout.
    timed_out = False
    process = subprocess.Popen(
        command,
        cwd=Path(cwd),
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=os.name != "nt",
    )

    try:
        stdout, stderr = process.communicate(timeout=timeout_ms / 1000)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process(process)
        stdout, stderr = process.communicate()

    stdout_value, stdout_truncated = truncate_command_output(stdout or "", max_output_chars)
    stderr_value, stderr_truncated = truncate_command_output(stderr or "", max_output_chars)
    return CommandResult(
        command=command,
        exit_code=process.returncode,
        stdout=stdout_value,
        stderr=stderr_value,
        timed_out=timed_out,
        signal=_signal_name(process.returncode) if process.returncode and process.returncode < 0 else None,
        timeout_ms=timeout_ms,
        cwd=relative_cwd(Path(cwd), project_root),
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        max_output_chars=max_output_chars,
    )


def execute_run_command_item(
    workspace: RunWorkspace,
    action: RunCommandAction | RunCommandItem,
    command_timeout_ms: int,
) -> CommandResult:
    timeout_ms = action.timeout_ms or command_timeout_ms
    max_output_chars = action.max_output_chars or 12_000
    blocked = get_blocked_command_reason(action.command)
    if blocked:
        return CommandResult(
            command=action.command,
            exit_code=None,
            stdout="",
            stderr=f"Command blocked: {blocked}",
            timed_out=False,
            signal=None,
            timeout_ms=timeout_ms,
            cwd=action.cwd or ".",
            max_output_chars=max_output_chars,
        )
    try:
        command_cwd = resolve_command_cwd(workspace, action.cwd)
    except ValueError as error:
        return CommandResult(
            command=action.command,
            exit_code=None,
            stdout="",
            stderr=str(error),
            timed_out=False,
            signal=None,
            timeout_ms=timeout_ms,
            cwd=action.cwd or ".",
            max_output_chars=max_output_chars,
        )
    result = run_command(
        command_cwd,
        action.command,
        timeout_ms,
        workspace.root,
        max_output_chars=max_output_chars,
    )
    return attach_output_analysis_to_command_result(workspace, action, result)


def attach_output_analysis_to_command_result(
    workspace: RunWorkspace,
    action: RunCommandAction | RunCommandItem,
    result: CommandResult,
) -> CommandResult:
    auto_extract_diagnostics = (
        not action.extract_output_contexts
        and not action.extract_output_diagnostics
        and command_result_failed(result)
    )
    if not action.extract_output_contexts and not action.extract_output_diagnostics and not auto_extract_diagnostics:
        return result
    text = "\n".join(part for part in [result.stdout, result.stderr] if part)
    if not text.strip():
        return result
    if action.extract_output_diagnostics or auto_extract_diagnostics:
        try:
            diagnostics_result = read_output_diagnostics_result(
                workspace,
                text,
                context_lines=action.context_lines,
                max_diagnostics=action.max_diagnostics,
                max_contexts=action.max_contexts,
                max_bytes_per_context=action.max_bytes_per_context,
            )
        except ValueError:
            return result
        return replace(
            result,
            output_contexts=output_context_results_from_dicts(diagnostics_result["contexts"]),
            output_context_total_refs=int(diagnostics_result["total_refs"]),
            output_contexts_truncated=bool(diagnostics_result["contexts_truncated"]),
            output_diagnostics=output_diagnostics_from_dicts(diagnostics_result["diagnostics"]),
            output_diagnostic_total=int(diagnostics_result["total_diagnostics"]),
            output_diagnostics_truncated=bool(diagnostics_result["diagnostics_truncated"]),
        )
    if action.extract_output_contexts:
        try:
            contexts_result = read_output_contexts_result(
                workspace,
                text,
                context_lines=action.context_lines,
                max_contexts=action.max_contexts,
                max_bytes_per_context=action.max_bytes_per_context,
            )
        except ValueError:
            return result
        return replace(
            result,
            output_contexts=output_context_results_from_dicts(contexts_result["contexts"]),
            output_context_total_refs=int(contexts_result["total_refs"]),
            output_contexts_truncated=bool(contexts_result["truncated"]),
        )


def command_result_failed(result: CommandResult) -> bool:
    if result.timed_out:
        return True
    if result.exit_code is None:
        return True
    return result.exit_code != 0


def attach_output_analysis_to_process_observation(
    workspace: RunWorkspace,
    observation: ReadProcessObservation | WaitProcessObservation,
) -> ReadProcessObservation | WaitProcessObservation:
    if not process_observation_failed(observation):
        return observation
    text = "\n".join(part for part in [observation.stdout, observation.stderr] if part)
    if not text.strip():
        return observation
    try:
        diagnostics_result = read_output_diagnostics_result(
            workspace,
            text,
            context_lines=2,
            max_diagnostics=50,
            max_contexts=20,
            max_bytes_per_context=20_000,
        )
    except ValueError:
        return observation
    return replace(
        observation,
        output_contexts=output_context_results_from_dicts(diagnostics_result["contexts"]),
        output_context_total_refs=int(diagnostics_result["total_refs"]),
        output_contexts_truncated=bool(diagnostics_result["contexts_truncated"]),
        output_diagnostics=output_diagnostics_from_dicts(diagnostics_result["diagnostics"]),
        output_diagnostic_total=int(diagnostics_result["total_diagnostics"]),
        output_diagnostics_truncated=bool(diagnostics_result["diagnostics_truncated"]),
    )


def process_observation_failed(observation: ReadProcessObservation | WaitProcessObservation) -> bool:
    if not observation.ok:
        return False
    if observation.running:
        return False
    if observation.exit_code is None:
        return True
    return observation.exit_code != 0


def start_background_command(workspace: RunWorkspace, command: str, cwd: str | None = None) -> StartCommandObservation:
    blocked = get_blocked_command_reason(command)
    if blocked:
        return StartCommandObservation(
            kind="start_command",
            process_id="",
            pid=None,
            command=command,
            cwd=cwd or ".",
            ok=False,
            message=f"Command blocked: {blocked}",
            stdout_path="",
            stderr_path="",
        )

    try:
        command_cwd = resolve_command_cwd(workspace, cwd)
    except ValueError as error:
        return StartCommandObservation(
            kind="start_command",
            process_id="",
            pid=None,
            command=command,
            cwd=cwd or ".",
            ok=False,
            message=str(error),
            stdout_path="",
            stderr_path="",
        )

    process_id = uuid.uuid4().hex[:12]
    process_dir = workspace.session_dir / "processes"
    process_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = process_dir / f"{process_id}.stdout.log"
    stderr_path = process_dir / f"{process_id}.stderr.log"
    exit_code_path = process_dir / f"{process_id}.exitcode"
    stdout_handle = stdout_path.open("w", encoding="utf-8")
    stderr_handle = stderr_path.open("w", encoding="utf-8")
    try:
        process = subprocess.Popen(
            wrap_background_command(command, exit_code_path),
            cwd=command_cwd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            start_new_session=os.name != "nt",
        )
    except OSError as error:
        stdout_handle.close()
        stderr_handle.close()
        return StartCommandObservation(
            kind="start_command",
            process_id="",
            pid=None,
            command=command,
            cwd=relative_cwd(command_cwd, workspace.root),
            ok=False,
            message=str(error),
            stdout_path=stdout_path.as_posix(),
            stderr_path=stderr_path.as_posix(),
        )

    BACKGROUND_PROCESSES[process_id] = BackgroundProcess(
        id=process_id,
        command=command,
        cwd=relative_cwd(command_cwd, workspace.root),
        process=process,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        exit_code_path=exit_code_path,
        stdout_handle=stdout_handle,
        stderr_handle=stderr_handle,
    )
    write_persistent_process_record(
        workspace,
        PersistentProcessRecord(
            id=process_id,
            command=command,
            cwd=relative_cwd(command_cwd, workspace.root),
            pid=process.pid,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            exit_code_path=exit_code_path,
            start_ticks=read_process_start_ticks(process.pid),
        ),
    )
    return StartCommandObservation(
        kind="start_command",
        process_id=process_id,
        pid=process.pid,
        command=command,
        cwd=relative_cwd(command_cwd, workspace.root),
        ok=True,
        message=f"Started process {process_id}.",
        stdout_path=stdout_path.as_posix(),
        stderr_path=stderr_path.as_posix(),
    )


def wrap_background_command(command: str, exit_code_path: Path) -> str:
    if os.name == "nt":
        escaped_exit_code_path = str(exit_code_path).replace('"', '""')
        quoted_exit_code_path = f'"{escaped_exit_code_path}"'
        return (
            f"{command}\r\n"
            "set __vibeagent_exit_code=%ERRORLEVEL%\r\n"
            f"echo %__vibeagent_exit_code%> {quoted_exit_code_path}\r\n"
            "exit /b %__vibeagent_exit_code%"
        )
    quoted_exit_code_path = shlex.quote(exit_code_path.as_posix())
    return (
        f"{command}\n"
        "__vibeagent_exit_code=$?\n"
        f"printf '%s\\n' \"$__vibeagent_exit_code\" > {quoted_exit_code_path}\n"
        "exit \"$__vibeagent_exit_code\""
    )


def process_registry_dir(root: Path) -> Path:
    return root / ".vibeagent" / "processes"


def process_record_path(root: Path, process_id: str) -> Path | None:
    if not process_id or Path(process_id).name != process_id:
        return None
    return process_registry_dir(root) / f"{process_id}.json"


def write_persistent_process_record(workspace: RunWorkspace, record: PersistentProcessRecord) -> None:
    path = process_record_path(workspace.root, record.id)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": record.id,
        "command": record.command,
        "cwd": record.cwd,
        "pid": record.pid,
        "stdout_path": relative_process_log_path(workspace.root, record.stdout_path),
        "stderr_path": relative_process_log_path(workspace.root, record.stderr_path),
        "exit_code_path": relative_process_log_path(workspace.root, record.exit_code_path) if record.exit_code_path else None,
        "start_ticks": record.start_ticks,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def relative_process_log_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def remove_persistent_process_record(root: Path, process_id: str) -> None:
    path = process_record_path(root, process_id)
    if path is None:
        return
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def read_persistent_process_record(root: Path, process_id: str) -> PersistentProcessRecord | None:
    path = process_record_path(root, process_id)
    if path is None or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return parse_persistent_process_record(root, payload)


def read_persistent_process_records(root: Path) -> list[PersistentProcessRecord]:
    directory = process_registry_dir(root)
    if not directory.is_dir():
        return []
    records: list[PersistentProcessRecord] = []
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        record = parse_persistent_process_record(root, payload)
        if record is not None:
            records.append(record)
    return records


def parse_persistent_process_record(root: Path, payload: object) -> PersistentProcessRecord | None:
    if not isinstance(payload, dict):
        return None
    process_id = payload.get("id")
    command = payload.get("command")
    cwd = payload.get("cwd")
    pid = payload.get("pid")
    stdout_text = payload.get("stdout_path")
    stderr_text = payload.get("stderr_path")
    exit_code_text = payload.get("exit_code_path")
    start_ticks = payload.get("start_ticks")
    if not isinstance(process_id, str) or not process_id.strip() or Path(process_id).name != process_id:
        return None
    if not isinstance(command, str) or not isinstance(cwd, str):
        return None
    if not isinstance(pid, int) or pid <= 0:
        return None
    if not isinstance(stdout_text, str) or not isinstance(stderr_text, str):
        return None
    stdout_path = resolve_process_log_path(root, stdout_text)
    stderr_path = resolve_process_log_path(root, stderr_text)
    if stdout_path is None or stderr_path is None:
        return None
    exit_code_path = resolve_process_log_path(root, exit_code_text) if isinstance(exit_code_text, str) else None
    return PersistentProcessRecord(
        id=process_id,
        command=command,
        cwd=cwd,
        pid=pid,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        exit_code_path=exit_code_path,
        start_ticks=start_ticks if isinstance(start_ticks, int) else None,
    )


def resolve_process_log_path(root: Path, value: str) -> Path | None:
    candidate = Path(value)
    path = candidate if candidate.is_absolute() else root / candidate
    try:
        resolved_root = root.resolve()
        resolved_path = path.resolve()
    except OSError:
        return None
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        return None
    return resolved_path


def read_process_start_ticks(pid: int) -> int | None:
    stat_path = Path("/proc") / str(pid) / "stat"
    try:
        stat = stat_path.read_text(encoding="utf-8")
    except OSError:
        return None
    parts = stat.rsplit(") ", 1)
    if len(parts) != 2:
        return None
    fields = parts[1].split()
    if len(fields) < 20:
        return None
    try:
        return int(fields[19])
    except ValueError:
        return None


def persistent_process_running(record: PersistentProcessRecord) -> bool:
    try:
        os.kill(record.pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    if record.start_ticks is None:
        return True
    return read_process_start_ticks(record.pid) == record.start_ticks


def read_persistent_process_exit_code(record: PersistentProcessRecord) -> int | None:
    if record.exit_code_path is None:
        return None
    try:
        text = record.exit_code_path.read_text(encoding="utf-8").strip().splitlines()[0]
    except (OSError, IndexError):
        return None
    try:
        return int(text)
    except ValueError:
        return None


def process_signal_name(exit_code: int | None) -> str | None:
    if exit_code is None:
        return None
    if exit_code < 0:
        return _signal_name(exit_code)
    if exit_code > 128:
        try:
            return signal.Signals(exit_code - 128).name
        except ValueError:
            return None
    return None


def terminate_persistent_process(record: PersistentProcessRecord) -> None:
    if not persistent_process_running(record):
        return
    if os.name != "nt":
        try:
            os.killpg(record.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        except OSError:
            try:
                os.kill(record.pid, signal.SIGTERM)
            except OSError:
                return
    else:
        try:
            os.kill(record.pid, signal.SIGTERM)
        except OSError:
            return
    deadline = time.monotonic() + 0.5
    while time.monotonic() < deadline:
        if not persistent_process_running(record):
            return
        time.sleep(0.05)
    if os.name != "nt":
        try:
            os.killpg(record.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except OSError:
            try:
                os.kill(record.pid, signal.SIGKILL)
            except OSError:
                return
    else:
        try:
            os.kill(record.pid, signal.SIGKILL)
        except OSError:
            return


def read_background_process(root: Path, process_id: str, max_output_chars: int = 4_000) -> ReadProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            running = persistent_process_running(record)
            exit_code = None if running else read_persistent_process_exit_code(record)
            stdout = read_text_tail(record.stdout_path, max_output_chars)
            stderr = read_text_tail(record.stderr_path, max_output_chars)
            state = "running" if running else "exited or unavailable"
            return ReadProcessObservation(
                kind="read_process",
                process_id=process_id,
                pid=record.pid,
                ok=True,
                running=running,
                exit_code=exit_code,
                signal=process_signal_name(exit_code),
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Process {process_id} is {state}.",
            )
        return ReadProcessObservation(
            kind="read_process",
            process_id=process_id,
            pid=None,
            ok=False,
            running=False,
            exit_code=None,
            signal=None,
            stdout="",
            stderr="",
            max_output_chars=max_output_chars,
            message="Unknown background process id.",
        )

    exit_code = background.process.poll()
    running = exit_code is None
    if not running:
        _close_background_handles(background)
    stdout = read_text_tail(background.stdout_path, max_output_chars)
    stderr = read_text_tail(background.stderr_path, max_output_chars)
    return ReadProcessObservation(
        kind="read_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=True,
        running=running,
        exit_code=exit_code,
        signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
        stdout=stdout,
        stderr=stderr,
        max_output_chars=max_output_chars,
        message=f"Process {process_id} is {'running' if running else 'exited'}.",
    )


def read_background_process_output_contexts(
    workspace: RunWorkspace,
    action: ProcessOutputContextsAction,
) -> ProcessOutputContextsObservation:
    process = read_background_process(
        workspace.root,
        action.process_id,
        max_output_chars=action.max_output_chars,
    )
    if not process.ok:
        return ProcessOutputContextsObservation(
            kind="process_output_contexts",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=False,
            exit_code=process.exit_code,
            signal=process.signal,
            contexts=[],
            total_refs=0,
            truncated=False,
            stdout_chars=0,
            stderr_chars=0,
            max_output_chars=action.max_output_chars,
            message=process.message,
        )

    text = "\n".join(part for part in [process.stdout, process.stderr] if part)
    if not text.strip():
        return ProcessOutputContextsObservation(
            kind="process_output_contexts",
            process_id=action.process_id,
            pid=process.pid,
            ok=True,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            contexts=[],
            total_refs=0,
            truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=f"Process {action.process_id} output contained no file:line references.",
        )

    try:
        result = read_output_contexts_result(
            workspace,
            text,
            context_lines=action.context_lines,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
    except ValueError as error:
        return ProcessOutputContextsObservation(
            kind="process_output_contexts",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            contexts=[],
            total_refs=0,
            truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=str(error),
        )

    contexts = output_context_results_from_dicts(result["contexts"])
    total_refs = int(result["total_refs"])
    return ProcessOutputContextsObservation(
        kind="process_output_contexts",
        process_id=action.process_id,
        pid=process.pid,
        ok=True,
        running=process.running,
        exit_code=process.exit_code,
        signal=process.signal,
        contexts=contexts,
        total_refs=total_refs,
        truncated=bool(result["truncated"]),
        stdout_chars=len(process.stdout),
        stderr_chars=len(process.stderr),
        max_output_chars=action.max_output_chars,
        message=f"Extracted {len(contexts)}/{total_refs} output context(s) from process {action.process_id}.",
    )


def read_background_process_output_diagnostics(
    workspace: RunWorkspace,
    action: ProcessOutputDiagnosticsAction,
) -> ProcessOutputDiagnosticsObservation:
    process = read_background_process(
        workspace.root,
        action.process_id,
        max_output_chars=action.max_output_chars,
    )
    if not process.ok:
        return ProcessOutputDiagnosticsObservation(
            kind="process_output_diagnostics",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=False,
            exit_code=process.exit_code,
            signal=process.signal,
            diagnostics=[],
            contexts=[],
            total_diagnostics=0,
            total_refs=0,
            diagnostics_truncated=False,
            contexts_truncated=False,
            stdout_chars=0,
            stderr_chars=0,
            max_output_chars=action.max_output_chars,
            message=process.message,
        )

    text = "\n".join(part for part in [process.stdout, process.stderr] if part)
    if not text.strip():
        return ProcessOutputDiagnosticsObservation(
            kind="process_output_diagnostics",
            process_id=action.process_id,
            pid=process.pid,
            ok=True,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            diagnostics=[],
            contexts=[],
            total_diagnostics=0,
            total_refs=0,
            diagnostics_truncated=False,
            contexts_truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=f"Process {action.process_id} output contained no diagnostic lines.",
        )

    try:
        result = read_output_diagnostics_result(
            workspace,
            text,
            context_lines=action.context_lines,
            max_diagnostics=action.max_diagnostics,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
    except ValueError as error:
        return ProcessOutputDiagnosticsObservation(
            kind="process_output_diagnostics",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            diagnostics=[],
            contexts=[],
            total_diagnostics=0,
            total_refs=0,
            diagnostics_truncated=False,
            contexts_truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=str(error),
        )

    diagnostics = output_diagnostics_from_dicts(result["diagnostics"])
    contexts = output_context_results_from_dicts(result["contexts"])
    total_diagnostics = int(result["total_diagnostics"])
    total_refs = int(result["total_refs"])
    return ProcessOutputDiagnosticsObservation(
        kind="process_output_diagnostics",
        process_id=action.process_id,
        pid=process.pid,
        ok=True,
        running=process.running,
        exit_code=process.exit_code,
        signal=process.signal,
        diagnostics=diagnostics,
        contexts=contexts,
        total_diagnostics=total_diagnostics,
        total_refs=total_refs,
        diagnostics_truncated=bool(result["diagnostics_truncated"]),
        contexts_truncated=bool(result["contexts_truncated"]),
        stdout_chars=len(process.stdout),
        stderr_chars=len(process.stderr),
        max_output_chars=action.max_output_chars,
        message=(
            f"Extracted {len(diagnostics)}/{total_diagnostics} diagnostic(s) "
            f"and {len(contexts)}/{total_refs} source context(s) from process {action.process_id}."
        ),
    )


def wait_background_process(
    root: Path,
    process_id: str,
    timeout_ms: int = 5_000,
    stdout_contains: str | None = None,
    stderr_contains: str | None = None,
    regex: bool = False,
    max_output_chars: int = 4_000,
) -> WaitProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            return wait_persistent_process(
                record,
                timeout_ms=timeout_ms,
                stdout_contains=stdout_contains,
                stderr_contains=stderr_contains,
                regex=regex,
                max_output_chars=max_output_chars,
            )
        return WaitProcessObservation(
            kind="wait_process",
            process_id=process_id,
            pid=None,
            ok=False,
            running=False,
            timed_out=False,
            matched=False,
            matched_stream=None,
            matched_pattern=None,
            timeout_ms=timeout_ms,
            exit_code=None,
            signal=None,
            stdout="",
            stderr="",
            max_output_chars=max_output_chars,
            message="Unknown background process id.",
        )

    wait_for_output = stdout_contains is not None or stderr_contains is not None
    if wait_for_output:
        return wait_background_process_output(
            background,
            timeout_ms=timeout_ms,
            stdout_contains=stdout_contains,
            stderr_contains=stderr_contains,
            regex=regex,
            max_output_chars=max_output_chars,
        )

    timed_out = False
    try:
        exit_code = background.process.wait(timeout=timeout_ms / 1000)
    except subprocess.TimeoutExpired:
        timed_out = True
        exit_code = background.process.poll()

    running = exit_code is None
    if not running:
        _close_background_handles(background)
    stdout = read_text_tail(background.stdout_path, max_output_chars)
    stderr = read_text_tail(background.stderr_path, max_output_chars)
    state = "still running" if running else "exited"
    timeout_note = " after timeout" if timed_out else ""
    return WaitProcessObservation(
        kind="wait_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=True,
        running=running,
        timed_out=timed_out,
        matched=False,
        matched_stream=None,
        matched_pattern=None,
        timeout_ms=timeout_ms,
        exit_code=exit_code,
        signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
        stdout=stdout,
        stderr=stderr,
        max_output_chars=max_output_chars,
        message=f"Process {process_id} is {state}{timeout_note}.",
    )


def check_write_background_process(root: Path, process_id: str, content: str) -> CheckWriteProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            running = persistent_process_running(record)
            message = (
                f"Cannot write to process {process_id}; stdin is only available in the runtime that started it."
                if running
                else f"Cannot write to process {process_id}; process has exited."
            )
            return CheckWriteProcessObservation(
                kind="check_write_process",
                process_id=process_id,
                pid=record.pid,
                ok=False,
                running=running,
                command=record.command,
                cwd=record.cwd,
                content_chars=len(content),
                message=message,
            )
        return CheckWriteProcessObservation(
            kind="check_write_process",
            process_id=process_id,
            pid=None,
            ok=False,
            running=False,
            command=None,
            cwd=None,
            content_chars=len(content),
            message="Unknown background process id.",
        )

    exit_code = background.process.poll()
    running = exit_code is None
    stdin = background.process.stdin
    writable = running and stdin is not None and not stdin.closed
    if not running:
        _close_background_handles(background)
    message = (
        f"Can write {len(content)} character(s) to process {process_id}."
        if writable
        else f"Cannot write to process {process_id}; stdin is closed or the process has exited."
    )
    return CheckWriteProcessObservation(
        kind="check_write_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=writable,
        running=running,
        command=background.command,
        cwd=background.cwd,
        content_chars=len(content),
        message=message,
    )


def write_background_process(root: Path, process_id: str, content: str) -> WriteProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            running = persistent_process_running(record)
            message = (
                f"Cannot write to process {process_id}; stdin is only available in the runtime that started it."
                if running
                else f"Cannot write to process {process_id}; process has exited."
            )
            return WriteProcessObservation(
                kind="write_process",
                process_id=process_id,
                pid=record.pid,
                ok=False,
                running=running,
                command=record.command,
                cwd=record.cwd,
                content_chars=len(content),
                message=message,
            )
        return WriteProcessObservation(
            kind="write_process",
            process_id=process_id,
            pid=None,
            ok=False,
            running=False,
            command=None,
            cwd=None,
            content_chars=len(content),
            message="Unknown background process id.",
        )

    exit_code = background.process.poll()
    running = exit_code is None
    stdin = background.process.stdin
    if not running:
        _close_background_handles(background)
        return WriteProcessObservation(
            kind="write_process",
            process_id=process_id,
            pid=background.process.pid,
            ok=False,
            running=False,
            command=background.command,
            cwd=background.cwd,
            content_chars=len(content),
            message=f"Cannot write to process {process_id}; process has exited.",
        )
    if stdin is None or stdin.closed:
        return WriteProcessObservation(
            kind="write_process",
            process_id=process_id,
            pid=background.process.pid,
            ok=False,
            running=True,
            command=background.command,
            cwd=background.cwd,
            content_chars=len(content),
            message=f"Cannot write to process {process_id}; stdin is closed.",
        )

    try:
        stdin.write(content)
        stdin.flush()
    except (BrokenPipeError, OSError, ValueError) as error:
        return WriteProcessObservation(
            kind="write_process",
            process_id=process_id,
            pid=background.process.pid,
            ok=False,
            running=background.process.poll() is None,
            command=background.command,
            cwd=background.cwd,
            content_chars=len(content),
            message=f"Failed to write to process {process_id}: {error}.",
        )

    return WriteProcessObservation(
        kind="write_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=True,
        running=background.process.poll() is None,
        command=background.command,
        cwd=background.cwd,
        content_chars=len(content),
        message=f"Wrote {len(content)} character(s) to process {process_id}.",
    )


def wait_persistent_process(
    record: PersistentProcessRecord,
    *,
    timeout_ms: int,
    stdout_contains: str | None,
    stderr_contains: str | None,
    regex: bool,
    max_output_chars: int,
) -> WaitProcessObservation:
    deadline = time.monotonic() + (timeout_ms / 1000)
    wait_for_output = stdout_contains is not None or stderr_contains is not None
    timed_out = False
    while True:
        running = persistent_process_running(record)
        exit_code = None if running else read_persistent_process_exit_code(record)
        stdout = read_text_tail(record.stdout_path, max_output_chars)
        stderr = read_text_tail(record.stderr_path, max_output_chars)
        if wait_for_output:
            try:
                matched, matched_stream, matched_pattern = match_process_output(
                    stdout,
                    stderr,
                    stdout_contains=stdout_contains,
                    stderr_contains=stderr_contains,
                    regex=regex,
                )
            except re.error as error:
                return WaitProcessObservation(
                    kind="wait_process",
                    process_id=record.id,
                    pid=record.pid,
                    ok=False,
                    running=running,
                    timed_out=False,
                    matched=False,
                    matched_stream=None,
                    matched_pattern=None,
                    timeout_ms=timeout_ms,
                    exit_code=exit_code,
                    signal=process_signal_name(exit_code),
                    stdout=stdout,
                    stderr=stderr,
                    max_output_chars=max_output_chars,
                    message=f"Invalid wait_process regex: {error}.",
                )
            if matched:
                return WaitProcessObservation(
                    kind="wait_process",
                    process_id=record.id,
                    pid=record.pid,
                    ok=True,
                    running=running,
                    timed_out=False,
                    matched=True,
                    matched_stream=matched_stream,
                    matched_pattern=matched_pattern,
                    timeout_ms=timeout_ms,
                    exit_code=exit_code,
                    signal=process_signal_name(exit_code),
                    stdout=stdout,
                    stderr=stderr,
                    max_output_chars=max_output_chars,
                    message=f"Process {record.id} matched {matched_stream} output pattern.",
                )
            if not running:
                return WaitProcessObservation(
                    kind="wait_process",
                    process_id=record.id,
                    pid=record.pid,
                    ok=True,
                    running=False,
                    timed_out=False,
                    matched=False,
                    matched_stream=None,
                    matched_pattern=None,
                    timeout_ms=timeout_ms,
                    exit_code=None,
                    signal=None,
                    stdout=stdout,
                    stderr=stderr,
                    max_output_chars=max_output_chars,
                    message=f"Process {record.id} exited before output pattern matched.",
                )
        elif not running:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=record.id,
                pid=record.pid,
                ok=True,
                running=False,
                timed_out=False,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=timeout_ms,
                exit_code=exit_code,
                signal=process_signal_name(exit_code),
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Process {record.id} exited.",
            )

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
        if timed_out:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=record.id,
                pid=record.pid,
                ok=True,
                running=running,
                timed_out=True,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=timeout_ms,
                exit_code=exit_code,
                signal=process_signal_name(exit_code),
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=(
                    f"Process {record.id} is still running after timeout; no output pattern matched."
                    if wait_for_output
                    else f"Process {record.id} is still running after timeout."
                ),
            )
        time.sleep(min(0.1, remaining))


def wait_background_process_output(
    background: BackgroundProcess,
    *,
    timeout_ms: int,
    stdout_contains: str | None,
    stderr_contains: str | None,
    regex: bool,
    max_output_chars: int,
) -> WaitProcessObservation:
    deadline = time.monotonic() + (timeout_ms / 1000)
    while True:
        exit_code = background.process.poll()
        running = exit_code is None
        if not running:
            _close_background_handles(background)
        stdout = read_text_tail(background.stdout_path, max_output_chars)
        stderr = read_text_tail(background.stderr_path, max_output_chars)
        try:
            matched, matched_stream, matched_pattern = match_process_output(
                stdout,
                stderr,
                stdout_contains=stdout_contains,
                stderr_contains=stderr_contains,
                regex=regex,
            )
        except re.error as error:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=background.id,
                pid=background.process.pid,
                ok=False,
                running=running,
                timed_out=False,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=timeout_ms,
                exit_code=exit_code,
                signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Invalid wait_process regex: {error}.",
            )

        if matched:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=background.id,
                pid=background.process.pid,
                ok=True,
                running=running,
                timed_out=False,
                matched=True,
                matched_stream=matched_stream,
                matched_pattern=matched_pattern,
                timeout_ms=timeout_ms,
                exit_code=exit_code,
                signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Process {background.id} matched {matched_stream} output pattern.",
            )

        if not running:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=background.id,
                pid=background.process.pid,
                ok=True,
                running=False,
                timed_out=False,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=timeout_ms,
                exit_code=exit_code,
                signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Process {background.id} exited before output pattern matched.",
            )

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=background.id,
                pid=background.process.pid,
                ok=True,
                running=True,
                timed_out=True,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=timeout_ms,
                exit_code=None,
                signal=None,
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Process {background.id} is still running after timeout; no output pattern matched.",
            )
        time.sleep(min(0.1, remaining))


def match_process_output(
    stdout: str,
    stderr: str,
    *,
    stdout_contains: str | None,
    stderr_contains: str | None,
    regex: bool,
) -> tuple[bool, str | None, str | None]:
    patterns = (("stdout", stdout, stdout_contains), ("stderr", stderr, stderr_contains))
    for stream, text, pattern in patterns:
        if pattern is None:
            continue
        if regex:
            if re.search(pattern, text):
                return True, stream, pattern
        elif pattern in text:
            return True, stream, pattern
    return False, None, None


def list_background_processes(root: Path) -> ListProcessesObservation:
    processes_by_id: dict[str, ProcessInfo] = {}
    for process_id, background in sorted(BACKGROUND_PROCESSES.items()):
        exit_code = background.process.poll()
        running = exit_code is None
        if not running:
            _close_background_handles(background)
        processes_by_id[process_id] = (
            ProcessInfo(
                process_id=process_id,
                pid=background.process.pid,
                command=background.command,
                cwd=background.cwd,
                running=running,
                exit_code=exit_code,
                signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
            )
        )
    for record in read_persistent_process_records(root):
        if record.id in processes_by_id:
            continue
        running = persistent_process_running(record)
        exit_code = None if running else read_persistent_process_exit_code(record)
        processes_by_id[record.id] = ProcessInfo(
            process_id=record.id,
            pid=record.pid,
            command=record.command,
            cwd=record.cwd,
            running=running,
            exit_code=exit_code,
            signal=process_signal_name(exit_code),
        )

    processes = [processes_by_id[process_id] for process_id in sorted(processes_by_id)]
    return ListProcessesObservation(
        kind="list_processes",
        processes=processes,
        message=f"Found {len(processes)} background process(es).",
    )


def check_stop_all_background_processes(root: Path) -> CheckStopAllProcessesObservation:
    listed = list_background_processes(root)
    running_count = sum(1 for process in listed.processes if process.running)
    return CheckStopAllProcessesObservation(
        kind="check_stop_all_processes",
        ok=True,
        processes=listed.processes,
        running_count=running_count,
        message=f"stop_all_processes would stop {len(listed.processes)} background process(es), {running_count} still running.",
    )


def check_stop_background_process(root: Path, process_id: str) -> CheckStopProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            running = persistent_process_running(record)
            exit_code = None if running else read_persistent_process_exit_code(record)
            state = "running and can be stopped" if running else "already exited or unavailable"
            return CheckStopProcessObservation(
                kind="check_stop_process",
                process_id=process_id,
                pid=record.pid,
                ok=True,
                command=record.command,
                cwd=record.cwd,
                running=running,
                exit_code=exit_code,
                signal=process_signal_name(exit_code),
                message=f"Process {process_id} is {state}.",
            )
        return CheckStopProcessObservation(
            kind="check_stop_process",
            process_id=process_id,
            pid=None,
            ok=False,
            command=None,
            cwd=None,
            running=False,
            exit_code=None,
            signal=None,
            message="Unknown background process id.",
        )

    exit_code = background.process.poll()
    running = exit_code is None
    signal = _signal_name(exit_code) if exit_code and exit_code < 0 else None
    state = "running and can be stopped" if running else "already exited"
    return CheckStopProcessObservation(
        kind="check_stop_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=True,
        command=background.command,
        cwd=background.cwd,
        running=running,
        exit_code=exit_code,
        signal=signal,
        message=f"Process {process_id} is {state}.",
    )


def stop_all_background_processes(root: Path) -> StopAllProcessesObservation:
    stopped: list[StoppedProcessInfo] = []
    stopped_ids: set[str] = set()
    for process_id, background in sorted(list(BACKGROUND_PROCESSES.items())):
        if background.process.poll() is None:
            _terminate_process(background.process)
        exit_code = background.process.poll()
        _close_background_handles(background)
        BACKGROUND_PROCESSES.pop(process_id, None)
        remove_persistent_process_record(root, process_id)
        stopped_ids.add(process_id)
        stopped.append(
            StoppedProcessInfo(
                process_id=process_id,
                pid=background.process.pid,
                command=background.command,
                cwd=background.cwd,
                ok=True,
                exit_code=exit_code,
                signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
                message=f"Stopped process {process_id}.",
            )
        )
    for record in read_persistent_process_records(root):
        if record.id in stopped_ids:
            continue
        was_running = persistent_process_running(record)
        if was_running:
            terminate_persistent_process(record)
        exit_code = read_persistent_process_exit_code(record)
        remove_persistent_process_record(root, record.id)
        stopped.append(
            StoppedProcessInfo(
                process_id=record.id,
                pid=record.pid,
                command=record.command,
                cwd=record.cwd,
                ok=True,
                exit_code=exit_code,
                signal=process_signal_name(exit_code),
                message=f"Stopped process {record.id}." if was_running else f"Removed exited process {record.id}.",
            )
        )

    return StopAllProcessesObservation(
        kind="stop_all_processes",
        ok=True,
        stopped=stopped,
        message=f"Stopped {len(stopped)} background process(es).",
    )


def stop_background_process(root: Path, process_id: str) -> StopProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            was_running = persistent_process_running(record)
            if was_running:
                terminate_persistent_process(record)
            exit_code = read_persistent_process_exit_code(record)
            remove_persistent_process_record(root, process_id)
            return StopProcessObservation(
                kind="stop_process",
                process_id=process_id,
                pid=record.pid,
                ok=True,
                exit_code=exit_code,
                signal=process_signal_name(exit_code),
                message=f"Stopped process {process_id}." if was_running else f"Removed exited process {process_id}.",
            )
        return StopProcessObservation(
            kind="stop_process",
            process_id=process_id,
            pid=None,
            ok=False,
            exit_code=None,
            signal=None,
            message="Unknown background process id.",
        )

    if background.process.poll() is None:
        _terminate_process(background.process)
    exit_code = background.process.poll()
    _close_background_handles(background)
    BACKGROUND_PROCESSES.pop(process_id, None)
    remove_persistent_process_record(root, process_id)
    return StopProcessObservation(
        kind="stop_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=True,
        exit_code=exit_code,
        signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
        message=f"Stopped process {process_id}.",
    )


def read_text_tail(path: Path, max_bytes: int = 4_000) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - max_bytes), os.SEEK_SET)
        return handle.read().decode("utf-8", errors="replace")


def relative_cwd(cwd: Path, project_root: str | Path | None) -> str:
    if project_root is None:
        return "."
    try:
        relative = cwd.resolve().relative_to(Path(project_root).resolve())
    except ValueError:
        return cwd.as_posix()
    return relative.as_posix() or "."


def truncate_command_output(value: str, max_chars: int) -> tuple[str, bool]:
    if len(value) <= max_chars:
        return value, False
    marker = f"\n[truncated to {max_chars} chars: showing head and tail]\n"
    if max_chars <= len(marker) + 2:
        return value[:max_chars], True
    keep = max_chars - len(marker)
    head = keep // 2
    tail = keep - head
    return f"{value[:head]}{marker}{value[-tail:]}", True


def _close_background_handles(background: BackgroundProcess) -> None:
    handles = [background.stdout_handle, background.stderr_handle, background.process.stdin]
    for handle in handles:
        if handle is not None and not handle.closed:
            handle.close()


def _terminate_process(process: subprocess.Popen[str]) -> None:
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "nt":
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return


def _signal_name(returncode: int) -> str | None:
    try:
        return signal.Signals(-returncode).name
    except ValueError:
        return None
