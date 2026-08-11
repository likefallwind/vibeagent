from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from .process_background_lookup import background_process_for_root, background_processes_for_root
from .process_lifecycle import close_background_handles, signal_name, terminate_process
from .process_registry import (
    persistent_process_running,
    process_signal_name,
    read_persistent_process_exit_code,
    read_persistent_process_record,
    read_persistent_process_records,
    remove_persistent_process_record,
    terminate_persistent_process,
)
from .types import (
    CheckStopAllProcessesObservation,
    CheckStopProcessObservation,
    ListProcessesObservation,
    ProcessInfo,
    StopAllProcessesObservation,
    StopProcessObservation,
    StoppedProcessInfo,
)


def _background_processes() -> dict[str, Any]:
    runtime_module = sys.modules.get("vibeagent.process_runtime")
    value = getattr(runtime_module, "BACKGROUND_PROCESSES", None) if runtime_module is not None else None
    return value if isinstance(value, dict) else {}


def list_background_processes(root: Path) -> ListProcessesObservation:
    processes_by_id: dict[str, ProcessInfo] = {}
    for process_id, background in sorted(background_processes_for_root(root).items()):
        exit_code = background.process.poll()
        running = exit_code is None
        if not running:
            close_background_handles(background)
        processes_by_id[process_id] = (
            ProcessInfo(
                process_id=process_id,
                pid=background.process.pid,
                command=background.command,
                cwd=background.cwd,
                running=running,
                exit_code=exit_code,
                signal=signal_name(exit_code) if exit_code and exit_code < 0 else None,
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
    background = background_process_for_root(root, process_id)
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
    signal = signal_name(exit_code) if exit_code and exit_code < 0 else None
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
    background_processes = _background_processes()
    scoped_processes = background_processes_for_root(root)
    for process_id, background in sorted(scoped_processes.items()):
        if background.process.poll() is None:
            terminate_process(background.process)
        exit_code = background.process.poll()
        close_background_handles(background)
        background_processes.pop(process_id, None)
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
                signal=signal_name(exit_code) if exit_code and exit_code < 0 else None,
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
    background_processes = _background_processes()
    background = background_process_for_root(root, process_id)
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
        terminate_process(background.process)
    exit_code = background.process.poll()
    close_background_handles(background)
    background_processes.pop(process_id, None)
    remove_persistent_process_record(root, process_id)
    return StopProcessObservation(
        kind="stop_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=True,
        exit_code=exit_code,
        signal=signal_name(exit_code) if exit_code and exit_code < 0 else None,
        message=f"Stopped process {process_id}.",
    )
