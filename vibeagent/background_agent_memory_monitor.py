from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import threading
import time
from uuid import uuid4

from .background_agent_store import (
    background_agent_runtime_root,
    ensure_private_directory,
    write_private_json,
)
from .background_agent_types import BACKGROUND_AGENT_ID_PATTERN
from .background_agent_memory import BACKGROUND_AGENT_MEMORY_LIMIT_ENV
from .process_registry import read_process_start_ticks
from .tool_memory_limit import ToolMemoryLaunch, valid_tool_memory_unit
from .tool_memory_systemd import (
    inspect_tool_memory_result,
    tool_memory_exceeded_message,
    tool_memory_unit_running,
)


MONITOR_PAYLOAD_VERSION = 1
MAX_MONITOR_PAYLOAD_BYTES = 16 * 1024
_MONITOR_ENVIRONMENT_KEYS = (
    "DBUS_SESSION_BUS_ADDRESS",
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "XDG_RUNTIME_DIR",
)


def start_background_agent_memory_monitor(
    project_root: Path,
    agent_id: str,
    launch: ToolMemoryLaunch,
    worker_process: subprocess.Popen[str],
    *,
    stderr_path: Path,
    exit_code_path: Path,
) -> subprocess.Popen[str]:
    root = project_root.resolve()
    launch_root = ensure_private_directory(background_agent_runtime_root(root) / "launch")
    payload_path = launch_root / f"{agent_id}-memory-{uuid4().hex[:12]}.json"
    write_private_json(
        payload_path,
        {
            "schemaVersion": MONITOR_PAYLOAD_VERSION,
            "agentId": agent_id,
            "projectRoot": root.as_posix(),
            "unit": launch.unit,
            "limitBytes": launch.limit_bytes,
            "environmentPath": launch.environment_path.as_posix(),
            "systemctl": launch.systemctl,
            "workerPid": worker_process.pid,
            "workerStartTicks": read_process_start_ticks(worker_process.pid),
            "stderrPath": stderr_path.relative_to(root).as_posix(),
            "exitCodePath": exit_code_path.relative_to(root).as_posix(),
        },
        exclusive=True,
    )
    environment = {
        key: value
        for key in _MONITOR_ENVIRONMENT_KEYS
        if (value := os.environ.get(key)) is not None
    }
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "vibeagent.background_agent_memory_monitor",
                payload_path.as_posix(),
            ],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            start_new_session=os.name != "nt",
            env=environment,
        )
    except Exception:
        payload_path.unlink(missing_ok=True)
        raise
    threading.Thread(
        target=process.wait,
        name=f"vibeagent-memory-monitor-{agent_id}",
        daemon=True,
    ).start()
    return process


def run_monitor(payload_path: Path) -> int:
    payload: dict[str, object] | None = None
    try:
        payload = _read_payload(payload_path)
        _wait_for_worker(payload)
        _record_result(payload)
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return 1
    finally:
        _cleanup_payload_files(payload_path, payload)


def _read_payload(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Background agent memory monitor payload is unavailable.")
    metadata = path.stat()
    if metadata.st_size > MAX_MONITOR_PAYLOAD_BYTES:
        raise ValueError("Background agent memory monitor payload is too large.")
    if hasattr(os, "getuid") and (
        metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077
    ):
        raise ValueError("Background agent memory monitor payload is not private.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schemaVersion") != MONITOR_PAYLOAD_VERSION:
        raise ValueError("Background agent memory monitor payload is invalid.")
    root_value = payload.get("projectRoot")
    agent_id = payload.get("agentId")
    if (
        not isinstance(root_value, str)
        or not Path(root_value).is_absolute()
        or not isinstance(agent_id, str)
        or BACKGROUND_AGENT_ID_PATTERN.fullmatch(agent_id) is None
    ):
        raise ValueError("Background agent memory monitor identity is invalid.")
    root = Path(root_value)
    if root.is_symlink() or not root.is_dir() or root.resolve() != root:
        raise ValueError("Background agent memory monitor project is unavailable.")
    expected_parent = background_agent_runtime_root(root) / "launch"
    if path.parent != expected_parent or not path.name.startswith(f"{agent_id}-memory-"):
        raise ValueError("Background agent memory monitor payload path is invalid.")
    unit = payload.get("unit")
    limit = payload.get("limitBytes")
    systemctl = payload.get("systemctl")
    worker_pid = payload.get("workerPid")
    worker_start_ticks = payload.get("workerStartTicks")
    if (
        not isinstance(unit, str)
        or not valid_tool_memory_unit(unit)
        or not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit <= 0
        or not isinstance(systemctl, str)
        or not Path(systemctl).is_absolute()
        or not isinstance(worker_pid, int)
        or worker_pid <= 0
        or (worker_start_ticks is not None and not isinstance(worker_start_ticks, int))
    ):
        raise ValueError("Background agent memory monitor process data is invalid.")
    for key, suffix in (
        ("stderrPath", ".stderr.log"),
        ("exitCodePath", ".exitcode"),
    ):
        resolved = _resolve_project_path(root, payload.get(key))
        if resolved is None or resolved.name != f"{agent_id}{suffix}":
            raise ValueError("Background agent memory monitor output path is invalid.")
    environment_path = Path(str(payload.get("environmentPath", "")))
    temp_root = Path(tempfile.gettempdir()).resolve()
    if (
        not environment_path.is_absolute()
        or environment_path.parent.resolve() != temp_root
        or not environment_path.name.startswith("vibeagent-tool-env-")
        or environment_path.suffix != ".json"
    ):
        raise ValueError("Background agent memory monitor environment path is invalid.")
    return payload


def _wait_for_worker(payload: dict[str, object]) -> None:
    unit = str(payload["unit"])
    systemctl = str(payload["systemctl"])
    pid = int(payload["workerPid"])
    start_ticks = payload.get("workerStartTicks")
    while True:
        active = tool_memory_unit_running(unit, systemctl=systemctl)
        if active is False:
            return
        if active is None and not _same_process(pid, start_ticks):
            return
        time.sleep(0.1)


def _record_result(payload: dict[str, object]) -> None:
    root = Path(str(payload["projectRoot"]))
    launch = ToolMemoryLaunch(
        argv=(),
        unit=str(payload["unit"]),
        limit_bytes=int(payload["limitBytes"]),
        environment_path=Path(str(payload["environmentPath"])),
        systemctl=str(payload["systemctl"]),
    )
    result = inspect_tool_memory_result(launch, os.environ)
    stderr_path = _resolve_project_path(root, payload["stderrPath"])
    exit_code_path = _resolve_project_path(root, payload["exitCodePath"])
    if stderr_path is None or exit_code_path is None:
        return
    if result.exceeded:
        _append_diagnostic(
            stderr_path,
            tool_memory_exceeded_message(
                launch,
                result,
                requirement=BACKGROUND_AGENT_MEMORY_LIMIT_ENV,
            ),
        )
        _write_exit_code_if_missing(exit_code_path, 1)
    elif result.result not in {None, "success"} and _write_exit_code_if_missing(
        exit_code_path,
        1,
    ):
        _append_diagnostic(
            stderr_path,
            f"Background agent service failed before recording an exit code: {result.result}.",
        )


def _same_process(pid: int, start_ticks: object) -> bool:
    current = read_process_start_ticks(pid)
    return current is not None and (start_ticks is None or current == start_ticks)


def _resolve_project_path(root: Path, value: object) -> Path | None:
    if not isinstance(value, str):
        return None
    try:
        path = (root / value).resolve()
    except OSError:
        return None
    return path if path != root and root in path.parents else None


def _append_diagnostic(path: Path, message: str) -> None:
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{message}\n")
    except OSError:
        return


def _write_exit_code_if_missing(path: Path, exit_code: int) -> bool:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError:
        return False
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(f"{exit_code}\n")
    return True


def _cleanup_payload_files(path: Path, payload: object) -> None:
    path.unlink(missing_ok=True)
    if isinstance(payload, dict):
        environment_path = payload.get("environmentPath")
        if isinstance(environment_path, str):
            Path(environment_path).unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    values = sys.argv[1:] if argv is None else argv
    if len(values) != 1:
        return 2
    return run_monitor(Path(values[0]))


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "run_monitor",
    "start_background_agent_memory_monitor",
]
