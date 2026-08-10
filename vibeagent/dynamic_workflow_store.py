from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Any
from uuid import uuid4

from .dynamic_workflow_types import WorkflowRunSummary


WORKFLOW_ID_PATTERN = re.compile(r"^workflow-[a-f0-9]{12}$")
MAX_WORKFLOW_SOURCE_BYTES = 1_000_000


def make_workflow_id() -> str:
    return f"workflow-{uuid4().hex[:12]}"


def workflows_root(project_root: Path) -> Path:
    return project_root / ".vibeagent" / "workflows"


def create_workflow_record(
    project_root: Path,
    *,
    script: str,
    source: str,
    session_id: str,
) -> dict[str, Any]:
    workflow_id = make_workflow_id()
    now = _timestamp()
    record: dict[str, Any] = {
        "version": 1,
        "id": workflow_id,
        "script": script,
        "session_id": session_id,
        "owner_pid": os.getpid(),
        "status": "running",
        "started_at": now,
        "updated_at": now,
        "finished_at": None,
        "error": None,
        "result": None,
        "total_calls": 0,
        "cached_calls": 0,
        "calls": {},
    }
    run_dir = _workflow_dir(project_root, workflow_id, create=True)
    _write_private_text(run_dir / "source.js", source)
    write_workflow_record(project_root, record)
    return record


def read_workflow_source(project_root: Path, workflow_id: str) -> str:
    path = _workflow_dir(project_root, workflow_id) / "source.js"
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Workflow source is missing or unsafe: {workflow_id}")
    if path.stat().st_size > MAX_WORKFLOW_SOURCE_BYTES:
        raise ValueError("Workflow source exceeds 1000000 bytes.")
    return path.read_text(encoding="utf-8")


def read_workflow_record(project_root: Path, workflow_id: str) -> dict[str, Any]:
    path = _workflow_dir(project_root, workflow_id) / "state.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Workflow not found: {workflow_id}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Workflow state is invalid: {workflow_id}: {error}") from error
    if not isinstance(value, dict) or value.get("id") != workflow_id:
        raise ValueError(f"Workflow state is invalid: {workflow_id}")
    return value


def write_workflow_record(project_root: Path, record: dict[str, Any]) -> None:
    workflow_id = str(record.get("id") or "")
    run_dir = _workflow_dir(project_root, workflow_id, create=True)
    record["updated_at"] = _timestamp()
    payload = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with NamedTemporaryFile("w", encoding="utf-8", dir=run_dir, delete=False) as handle:
        handle.write(payload)
        temp_path = Path(handle.name)
    os.chmod(temp_path, 0o600)
    temp_path.replace(run_dir / "state.json")


def list_workflow_records(project_root: Path, limit: int = 20) -> list[dict[str, Any]]:
    root = workflows_root(project_root)
    if root.is_symlink() or not root.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for path in root.iterdir():
        if path.is_symlink() or not path.is_dir() or not WORKFLOW_ID_PATTERN.fullmatch(path.name):
            continue
        try:
            records.append(read_workflow_record(project_root, path.name))
        except ValueError:
            continue
    records.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    return records[:limit]


def summarize_workflow_record(record: dict[str, Any]) -> WorkflowRunSummary:
    status = str(record.get("status") or "failed")
    if status not in {"running", "completed", "failed", "stopped", "interrupted"}:
        status = "failed"
    return WorkflowRunSummary(
        id=str(record.get("id") or ""),
        script=str(record.get("script") or ""),
        session_id=str(record.get("session_id") or ""),
        status=status,  # type: ignore[arg-type]
        total_calls=int(record.get("total_calls") or 0),
        cached_calls=int(record.get("cached_calls") or 0),
        started_at=str(record.get("started_at") or ""),
        updated_at=str(record.get("updated_at") or ""),
        error=str(record["error"]) if record.get("error") is not None else None,
        result=record.get("result"),
    )


def _workflow_dir(project_root: Path, workflow_id: str, *, create: bool = False) -> Path:
    if not WORKFLOW_ID_PATTERN.fullmatch(workflow_id):
        raise ValueError(f"Invalid workflow ID: {workflow_id}")
    root = workflows_root(project_root)
    if root.is_symlink():
        raise ValueError("Workflow store path must not be a symbolic link.")
    if create:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(root, 0o700)
    if root.exists() and not root.is_dir():
        raise ValueError("Workflow store path is not a directory.")
    run_dir = root / workflow_id
    if run_dir.is_symlink():
        raise ValueError(f"Workflow path must not be a symbolic link: {workflow_id}")
    if create:
        run_dir.mkdir(mode=0o700, exist_ok=True)
        os.chmod(run_dir, 0o700)
    if not run_dir.is_dir():
        raise ValueError(f"Workflow not found: {workflow_id}")
    return run_dir


def _write_private_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")
    os.chmod(path, 0o600)


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


__all__ = [
    "MAX_WORKFLOW_SOURCE_BYTES",
    "create_workflow_record",
    "list_workflow_records",
    "read_workflow_record",
    "read_workflow_source",
    "summarize_workflow_record",
    "write_workflow_record",
]
