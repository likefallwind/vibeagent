from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CommandCheckAction:
    type: Literal["command_check"]
    command: str
    cwd: str | None = None


@dataclass(frozen=True)
class RunCommandItem:
    command: str
    timeout_ms: int | None = None
    cwd: str | None = None
    max_output_chars: int | None = None
    extract_output_contexts: bool = False
    extract_output_diagnostics: bool = False
    context_lines: int = 5
    max_diagnostics: int = 50
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class CheckRunCommandsAction:
    type: Literal["check_run_commands"]
    commands: list[RunCommandItem]


@dataclass(frozen=True)
class CheckStartCommandAction:
    type: Literal["check_start_command"]
    command: str
    cwd: str | None = None


@dataclass(frozen=True)
class PortCheckAction:
    type: Literal["port_check"]
    port: int
    host: str = "127.0.0.1"
    timeout_ms: int | None = None


@dataclass(frozen=True)
class HttpCheckAction:
    type: Literal["http_check"]
    url: str
    timeout_ms: int | None = None
    max_body_chars: int | None = None
    contains: str | None = None
    regex: bool = False


@dataclass(frozen=True)
class HttpFetchAction:
    type: Literal["http_fetch"]
    url: str
    timeout_ms: int | None = None
    max_body_chars: int | None = None


@dataclass(frozen=True)
class EnvironmentInfoAction:
    type: Literal["environment_info"]


@dataclass(frozen=True)
class RunCommandAction:
    type: Literal["run_command"]
    command: str
    timeout_ms: int | None = None
    cwd: str | None = None
    max_output_chars: int | None = None
    extract_output_contexts: bool = False
    extract_output_diagnostics: bool = False
    context_lines: int = 5
    max_diagnostics: int = 50
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class RunCommandsAction:
    type: Literal["run_commands"]
    commands: list[RunCommandItem]
    stop_on_failure: bool = True


@dataclass(frozen=True)
class StartCommandAction:
    type: Literal["start_command"]
    command: str
    cwd: str | None = None


@dataclass(frozen=True)
class ReadProcessAction:
    type: Literal["read_process"]
    process_id: str
    max_output_chars: int | None = None


@dataclass(frozen=True)
class ProcessOutputContextsAction:
    type: Literal["process_output_contexts"]
    process_id: str
    max_output_chars: int = 20_000
    context_lines: int = 5
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class ProcessOutputDiagnosticsAction:
    type: Literal["process_output_diagnostics"]
    process_id: str
    max_output_chars: int = 20_000
    context_lines: int = 2
    max_diagnostics: int = 50
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class WaitProcessAction:
    type: Literal["wait_process"]
    process_id: str
    timeout_ms: int | None = None
    stdout_contains: str | None = None
    stderr_contains: str | None = None
    regex: bool = False
    max_output_chars: int | None = None


@dataclass(frozen=True)
class CheckWriteProcessAction:
    type: Literal["check_write_process"]
    process_id: str
    content: str


@dataclass(frozen=True)
class WriteProcessAction:
    type: Literal["write_process"]
    process_id: str
    content: str


@dataclass(frozen=True)
class ListProcessesAction:
    type: Literal["list_processes"]


@dataclass(frozen=True)
class CheckStopAllProcessesAction:
    type: Literal["check_stop_all_processes"]


@dataclass(frozen=True)
class StopProcessAction:
    type: Literal["stop_process"]
    process_id: str


@dataclass(frozen=True)
class StopAllProcessesAction:
    type: Literal["stop_all_processes"]


@dataclass(frozen=True)
class CheckStopProcessAction:
    type: Literal["check_stop_process"]
    process_id: str
