from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
from uuid import uuid4

from .background_agent_types import (
    BACKGROUND_AGENT_ID_PATTERN,
    BACKGROUND_AGENT_SCHEMA_VERSION,
    BackgroundAgentRecord,
    BackgroundAgentView,
)
from .process_registry import PersistentProcessRecord, persistent_process_running


def list_background_agents(project_root: Path) -> tuple[BackgroundAgentView, ...]:
    root = project_root.resolve()
    runtime_root = background_agent_runtime_root(root)
    if not runtime_root.is_dir() or runtime_root.is_symlink():
        return ()
    records: list[BackgroundAgentRecord] = []
    for path in sorted(runtime_root.glob("*.json")):
        record = read_background_agent_record(root, path)
        if record is not None:
            records.append(record)
    records.sort(key=lambda item: item.started_at, reverse=True)
    return tuple(background_agent_view(record) for record in records)


def get_background_agent(project_root: Path, agent_id: str) -> BackgroundAgentView | None:
    root = project_root.resolve()
    path = background_agent_record_path(root, agent_id)
    if path is None:
        return None
    record = read_background_agent_record(root, path)
    return background_agent_view(record) if record is not None else None


def background_agent_view(record: BackgroundAgentRecord) -> BackgroundAgentView:
    exit_code = read_background_agent_exit_code(record.exit_code_path)
    if record.stopped_path.is_file():
        status = "stopped"
    elif exit_code == 0:
        status = "completed"
    elif exit_code is not None:
        status = "failed"
    elif persistent_process_running(as_process_record(record)):
        status = "running"
    else:
        status = "lost"
    return BackgroundAgentView(record=record, status=status, exit_code=exit_code)


def background_agent_runtime_root(project_root: Path) -> Path:
    return project_root / ".vibeagent" / "background-agents"


def background_agent_record_path(project_root: Path, agent_id: str) -> Path | None:
    if BACKGROUND_AGENT_ID_PATTERN.fullmatch(agent_id) is None:
        return None
    return background_agent_runtime_root(project_root) / f"{agent_id}.json"


def background_agent_view_payload(view: BackgroundAgentView) -> dict[str, object]:
    record = view.record
    return {
        "id": record.id,
        "status": view.status,
        "exitCode": view.exit_code,
        "pid": record.pid,
        "startedAt": record.started_at,
        "task": record.task_summary,
        "sessionName": record.session_name,
        "stdoutPath": relative_runtime_path(record),
        "stderrPath": relative_runtime_path(record, stderr=True),
    }


def ensure_background_agent_runtime_root(project_root: Path) -> Path:
    runtime = project_root / ".vibeagent"
    if runtime.is_symlink() or (runtime.exists() and not runtime.is_dir()):
        raise ValueError(f"Runtime path is not a regular directory: {runtime}")
    runtime.mkdir(parents=True, exist_ok=True)
    return ensure_private_directory(background_agent_runtime_root(project_root))


def ensure_private_directory(path: Path) -> Path:
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise ValueError(f"Background agent path is not a regular directory: {path}")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.chmod(0o700)
    except OSError:
        pass
    return path


def write_background_agent_record(
    record: BackgroundAgentRecord,
    *,
    exclusive: bool = True,
) -> None:
    path = background_agent_record_path(record.project_root, record.id)
    if path is None:
        raise ValueError(f"Invalid background agent id: {record.id}")
    payload = {
        "schemaVersion": BACKGROUND_AGENT_SCHEMA_VERSION,
        **asdict(record),
        "project_root": record.project_root.as_posix(),
        "invocation_root": record.invocation_root.as_posix(),
        "stdout_path": record.stdout_path.relative_to(record.project_root).as_posix(),
        "stderr_path": record.stderr_path.relative_to(record.project_root).as_posix(),
        "exit_code_path": record.exit_code_path.relative_to(record.project_root).as_posix(),
        "stopped_path": record.stopped_path.relative_to(record.project_root).as_posix(),
    }
    if exclusive:
        write_private_json(path, payload, exclusive=True)
    else:
        write_private_json_atomic(path, payload)


def read_background_agent_record(
    project_root: Path,
    path: Path,
) -> BackgroundAgentRecord | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("schemaVersion") != BACKGROUND_AGENT_SCHEMA_VERSION:
        return None
    agent_id = payload.get("id")
    if not isinstance(agent_id, str) or background_agent_record_path(project_root, agent_id) != path:
        return None
    pid = payload.get("pid")
    started_at = payload.get("started_at")
    task_summary = payload.get("task_summary")
    session_name = payload.get("session_name")
    invocation_root = payload.get("invocation_root")
    if (
        not isinstance(pid, int)
        or pid <= 0
        or not isinstance(started_at, str)
        or not isinstance(task_summary, str)
        or (session_name is not None and not isinstance(session_name, str))
        or not isinstance(invocation_root, str)
        or not Path(invocation_root).is_absolute()
    ):
        return None
    paths = [
        resolve_background_agent_path(project_root, payload.get(key))
        for key in ("stdout_path", "stderr_path", "exit_code_path", "stopped_path")
    ]
    if any(item is None for item in paths):
        return None
    stdout_path, stderr_path, exit_code_path, stopped_path = paths
    assert stdout_path is not None
    assert stderr_path is not None
    assert exit_code_path is not None
    assert stopped_path is not None
    return BackgroundAgentRecord(
        id=agent_id,
        project_root=project_root,
        invocation_root=Path(invocation_root),
        pid=pid,
        start_ticks=payload.get("start_ticks") if isinstance(payload.get("start_ticks"), int) else None,
        started_at=started_at,
        task_summary=task_summary,
        session_name=session_name,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        exit_code_path=exit_code_path,
        stopped_path=stopped_path,
    )


def resolve_background_agent_path(project_root: Path, value: object) -> Path | None:
    if not isinstance(value, str):
        return None
    try:
        resolved = (project_root / value).resolve()
    except OSError:
        return None
    if resolved == project_root or project_root not in resolved.parents:
        return None
    return resolved


def as_process_record(record: BackgroundAgentRecord) -> PersistentProcessRecord:
    return PersistentProcessRecord(
        id=record.id,
        command="vibeagent background agent",
        cwd=record.invocation_root.as_posix(),
        pid=record.pid,
        stdout_path=record.stdout_path,
        stderr_path=record.stderr_path,
        exit_code_path=record.exit_code_path,
        start_ticks=record.start_ticks,
    )


def relative_runtime_path(record: BackgroundAgentRecord, *, stderr: bool = False) -> str:
    path = record.stderr_path if stderr else record.stdout_path
    return path.relative_to(record.project_root).as_posix()


def open_private_log(path: Path):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    return os.fdopen(descriptor, "w", encoding="utf-8")


def open_private_log_append(path: Path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Background agent log is not a regular file: {path}")
    flags = os.O_WRONLY | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    return os.fdopen(descriptor, "a", encoding="utf-8")


def write_private_json(path: Path, payload: object, *, exclusive: bool) -> None:
    write_private_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        exclusive=exclusive,
    )


def write_private_json_atomic(path: Path, payload: object) -> None:
    write_private_text_atomic(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )


def write_private_text(path: Path, text: str, *, exclusive: bool) -> None:
    flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC)
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)


def write_private_text_atomic(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def read_background_agent_exit_code(path: Path) -> int | None:
    try:
        text = path.read_text(encoding="utf-8").strip().splitlines()[0]
        return int(text)
    except (OSError, IndexError, ValueError):
        return None


__all__ = [
    "as_process_record",
    "background_agent_record_path",
    "background_agent_runtime_root",
    "background_agent_view",
    "background_agent_view_payload",
    "ensure_background_agent_runtime_root",
    "ensure_private_directory",
    "get_background_agent",
    "list_background_agents",
    "open_private_log",
    "open_private_log_append",
    "read_background_agent_exit_code",
    "write_background_agent_record",
    "write_private_json",
    "write_private_json_atomic",
    "write_private_text",
    "write_private_text_atomic",
]
