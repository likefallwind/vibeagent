from __future__ import annotations

import json
import os
import signal
import time
from dataclasses import dataclass
from pathlib import Path

from .workspace_core import RunWorkspace


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
    max_output_chars: int | None = None


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
        "max_output_chars": record.max_output_chars,
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
    max_output_chars = payload.get("max_output_chars")
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
        max_output_chars=(
            max_output_chars if isinstance(max_output_chars, int) and 1_000 <= max_output_chars <= 50_000 else None
        ),
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
        try:
            return signal.Signals(-exit_code).name
        except ValueError:
            return None
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
