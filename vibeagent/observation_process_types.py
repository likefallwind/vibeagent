from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .action_process_types import RunCommandItem
from .observation_read_types import OutputContextResult, OutputDiagnostic


@dataclass(frozen=True)
class CommandResult:
    command: str
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    signal: str | None
    timeout_ms: int = 30_000
    cwd: str = "."
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    max_output_chars: int = 12_000
    duration_ms: int = 0
    sandboxed: bool = False
    sandbox_warning: str | None = None
    output_contexts: list[OutputContextResult] = field(default_factory=list)
    output_context_total_refs: int = 0
    output_contexts_truncated: bool = False
    output_diagnostics: list[OutputDiagnostic] = field(default_factory=list)
    output_diagnostic_total: int = 0
    output_diagnostics_truncated: bool = False


@dataclass(frozen=True)
class RunCommandObservation:
    kind: Literal["run_command"]
    result: CommandResult


@dataclass(frozen=True)
class RunCommandsObservation:
    kind: Literal["run_commands"]
    results: list[CommandResult]
    ok: bool
    stopped_early: bool
    message: str


@dataclass(frozen=True)
class CommandCheckObservation:
    kind: Literal["command_check"]
    ok: bool
    command: str
    cwd: str
    cwd_ok: bool
    blocked: bool
    block_reason: str | None
    executable_available: bool
    missing_tool: str | None
    message: str


@dataclass(frozen=True)
class CheckRunCommandsObservation:
    kind: Literal["check_run_commands"]
    ok: bool
    checks: list[CommandCheckObservation]
    message: str
    commands: list[RunCommandItem] | None = None


@dataclass(frozen=True)
class StartCommandObservation:
    kind: Literal["start_command"]
    process_id: str
    pid: int | None
    command: str
    cwd: str
    ok: bool
    message: str
    stdout_path: str
    stderr_path: str
    sandboxed: bool = False
    sandbox_warning: str | None = None


@dataclass(frozen=True)
class ReadProcessObservation:
    kind: Literal["read_process"]
    process_id: str
    pid: int | None
    ok: bool
    running: bool
    exit_code: int | None
    signal: str | None
    stdout: str
    stderr: str
    max_output_chars: int
    message: str
    output_contexts: list[OutputContextResult] = field(default_factory=list)
    output_context_total_refs: int = 0
    output_contexts_truncated: bool = False
    output_diagnostics: list[OutputDiagnostic] = field(default_factory=list)
    output_diagnostic_total: int = 0
    output_diagnostics_truncated: bool = False


@dataclass(frozen=True)
class ProcessOutputContextsObservation:
    kind: Literal["process_output_contexts"]
    process_id: str
    pid: int | None
    ok: bool
    running: bool
    exit_code: int | None
    signal: str | None
    contexts: list[OutputContextResult]
    total_refs: int
    truncated: bool
    stdout_chars: int
    stderr_chars: int
    max_output_chars: int
    message: str


@dataclass(frozen=True)
class ProcessOutputDiagnosticsObservation:
    kind: Literal["process_output_diagnostics"]
    process_id: str
    pid: int | None
    ok: bool
    running: bool
    exit_code: int | None
    signal: str | None
    diagnostics: list[OutputDiagnostic]
    contexts: list[OutputContextResult]
    total_diagnostics: int
    total_refs: int
    diagnostics_truncated: bool
    contexts_truncated: bool
    stdout_chars: int
    stderr_chars: int
    max_output_chars: int
    message: str


@dataclass(frozen=True)
class WaitProcessObservation:
    kind: Literal["wait_process"]
    process_id: str
    pid: int | None
    ok: bool
    running: bool
    timed_out: bool
    matched: bool
    matched_stream: str | None
    matched_pattern: str | None
    timeout_ms: int
    exit_code: int | None
    signal: str | None
    stdout: str
    stderr: str
    max_output_chars: int
    message: str
    output_contexts: list[OutputContextResult] = field(default_factory=list)
    output_context_total_refs: int = 0
    output_contexts_truncated: bool = False
    output_diagnostics: list[OutputDiagnostic] = field(default_factory=list)
    output_diagnostic_total: int = 0
    output_diagnostics_truncated: bool = False


@dataclass(frozen=True)
class CheckWriteProcessObservation:
    kind: Literal["check_write_process"]
    process_id: str
    pid: int | None
    ok: bool
    running: bool
    command: str | None
    cwd: str | None
    content_chars: int
    message: str
    content_sha256: str = ""
    stdin_file: str | None = None


@dataclass(frozen=True)
class WriteProcessObservation:
    kind: Literal["write_process"]
    process_id: str
    pid: int | None
    ok: bool
    running: bool
    command: str | None
    cwd: str | None
    content_chars: int
    message: str
    content_sha256: str = ""
    stdin_file: str | None = None


@dataclass(frozen=True)
class ProcessInfo:
    process_id: str
    pid: int
    command: str
    cwd: str
    running: bool
    exit_code: int | None
    signal: str | None


@dataclass(frozen=True)
class ListProcessesObservation:
    kind: Literal["list_processes"]
    processes: list[ProcessInfo]
    message: str


@dataclass(frozen=True)
class CheckStopAllProcessesObservation:
    kind: Literal["check_stop_all_processes"]
    ok: bool
    processes: list[ProcessInfo]
    running_count: int
    message: str


@dataclass(frozen=True)
class StopProcessObservation:
    kind: Literal["stop_process"]
    process_id: str
    pid: int | None
    ok: bool
    exit_code: int | None
    signal: str | None
    message: str


@dataclass(frozen=True)
class StoppedProcessInfo:
    process_id: str
    pid: int
    command: str
    cwd: str
    ok: bool
    exit_code: int | None
    signal: str | None
    message: str


@dataclass(frozen=True)
class StopAllProcessesObservation:
    kind: Literal["stop_all_processes"]
    ok: bool
    stopped: list[StoppedProcessInfo]
    message: str


@dataclass(frozen=True)
class CheckStopProcessObservation:
    kind: Literal["check_stop_process"]
    process_id: str
    pid: int | None
    ok: bool
    command: str | None
    cwd: str | None
    running: bool
    exit_code: int | None
    signal: str | None
    message: str
