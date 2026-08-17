from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import signal
import subprocess
from threading import Event, Thread
import time
from typing import Mapping

from .bounded_subprocess import run_bounded_subprocess
from .tool_memory_limit import (
    TOOL_MEMORY_LIMIT_ENV,
    ToolMemoryLaunch,
    cleanup_tool_memory_launch,
    format_memory_bytes,
    valid_tool_memory_unit,
)


MAX_SYSTEMD_PROBE_OUTPUT_CHARS = 4_000


@dataclass(frozen=True)
class ToolMemoryResult:
    result: str | None = None
    main_code: int | None = None
    main_status: int | None = None
    memory_peak_bytes: int | None = None

    @property
    def exceeded(self) -> bool:
        return self.result == "oom-kill"

    @property
    def signal_name(self) -> str | None:
        if self.main_code != 2 or self.main_status is None:
            return None
        try:
            return signal.Signals(self.main_status).name
        except ValueError:
            return None


def inspect_tool_memory_result(
    launch: ToolMemoryLaunch,
    environment: Mapping[str, str],
) -> ToolMemoryResult:
    if not valid_tool_memory_unit(launch.unit):
        return ToolMemoryResult()
    try:
        completed = run_bounded_subprocess(
            (
                launch.systemctl,
                "--user",
                "show",
                launch.unit,
                "--property=Result,ExecMainCode,ExecMainStatus,MemoryPeak",
            ),
            timeout_ms=3_000,
            max_output_chars=MAX_SYSTEMD_PROBE_OUTPUT_CHARS,
            env=dict(environment),
        )
    except (OSError, subprocess.TimeoutExpired):
        return ToolMemoryResult()
    if completed.returncode != 0:
        return ToolMemoryResult()
    fields = _parse_systemd_fields(completed.stdout)
    result = ToolMemoryResult(
        result=fields.get("Result") or None,
        main_code=_parse_optional_int(fields.get("ExecMainCode")),
        main_status=_parse_optional_int(fields.get("ExecMainStatus")),
        memory_peak_bytes=_parse_optional_int(fields.get("MemoryPeak")),
    )
    if result.result not in {None, "success"}:
        _reset_failed_unit(launch, environment)
    return result


def stop_tool_memory_unit(
    unit: str,
    environment: Mapping[str, str] | None = None,
    *,
    systemctl: str | None = None,
) -> bool:
    if not valid_tool_memory_unit(unit):
        return False
    source = os.environ if environment is None else environment
    executable = systemctl or shutil.which("systemctl", path=source.get("PATH"))
    if executable is None:
        return False
    try:
        completed = run_bounded_subprocess(
            (executable, "--user", "stop", unit),
            timeout_ms=3_000,
            max_output_chars=MAX_SYSTEMD_PROBE_OUTPUT_CHARS,
            env=dict(source),
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def tool_memory_unit_running(
    unit: str,
    environment: Mapping[str, str] | None = None,
    *,
    systemctl: str | None = None,
) -> bool | None:
    if not valid_tool_memory_unit(unit):
        return None
    source = os.environ if environment is None else environment
    executable = systemctl or shutil.which("systemctl", path=source.get("PATH"))
    if executable is None:
        return None
    try:
        completed = run_bounded_subprocess(
            (executable, "--user", "is-active", "--quiet", unit),
            timeout_ms=2_000,
            max_output_chars=MAX_SYSTEMD_PROBE_OUTPUT_CHARS,
            env=dict(source),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode == 0:
        return True
    if completed.returncode in {3, 4}:
        return False
    return None


def start_background_memory_diagnostics(
    process: subprocess.Popen[str],
    launch: ToolMemoryLaunch | None,
    stderr_path: Path,
    exit_code_path: Path,
    environment: Mapping[str, str],
    *,
    requirement: str = TOOL_MEMORY_LIMIT_ENV,
) -> Event | None:
    if launch is None:
        return None
    done = Event()

    def wait_and_report() -> None:
        try:
            returncode = process.wait()
            if returncode == 0:
                return
            result = inspect_tool_memory_result(launch, environment)
            if not result.exceeded:
                return
            message = tool_memory_exceeded_message(
                launch,
                result,
                requirement=requirement,
            )
            with stderr_path.open("a", encoding="utf-8") as handle:
                handle.write(f"{message}\n")
            _write_exit_code_if_missing(exit_code_path, 1)
        except OSError:
            return
        finally:
            cleanup_tool_memory_launch(launch)
            done.set()

    Thread(
        target=wait_and_report,
        name=f"tool-memory-{launch.unit[15:23]}",
        daemon=True,
    ).start()
    return done


def wait_for_tool_memory_service(
    process: subprocess.Popen[str],
    launch: ToolMemoryLaunch | None,
    *,
    timeout_seconds: float = 3.0,
) -> str | None:
    if launch is None:
        return None
    deadline = time.monotonic() + timeout_seconds
    while launch.environment_path.exists() and process.poll() is None:
        if time.monotonic() >= deadline:
            return "Timed out while starting the memory-limited command service."
        time.sleep(0.01)
    if not launch.environment_path.exists():
        return None
    return "Could not start the memory-limited command service."


def tool_memory_exceeded_message(
    launch: ToolMemoryLaunch,
    result: ToolMemoryResult,
    *,
    requirement: str = TOOL_MEMORY_LIMIT_ENV,
) -> str:
    peak = (
        f"; peak {format_memory_bytes(result.memory_peak_bytes)}"
        if result.memory_peak_bytes is not None
        else ""
    )
    return (
        f"Command terminated after exceeding {requirement}="
        f"{format_memory_bytes(launch.limit_bytes)}{peak}."
    )


def _parse_systemd_fields(value: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in value.splitlines():
        name, separator, item = line.partition("=")
        if separator:
            fields[name] = item
    return fields


def _write_exit_code_if_missing(path: Path, exit_code: int) -> None:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError:
        return
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(f"{exit_code}\n")


def _parse_optional_int(value: str | None) -> int | None:
    if value is None or not value.isdecimal():
        return None
    return int(value)


def _reset_failed_unit(
    launch: ToolMemoryLaunch,
    environment: Mapping[str, str],
) -> None:
    try:
        run_bounded_subprocess(
            (launch.systemctl, "--user", "reset-failed", launch.unit),
            timeout_ms=2_000,
            max_output_chars=MAX_SYSTEMD_PROBE_OUTPUT_CHARS,
            env=dict(environment),
        )
    except (OSError, subprocess.TimeoutExpired):
        return


__all__ = [
    "ToolMemoryResult",
    "inspect_tool_memory_result",
    "start_background_memory_diagnostics",
    "stop_tool_memory_unit",
    "tool_memory_exceeded_message",
    "tool_memory_unit_running",
    "wait_for_tool_memory_service",
]
