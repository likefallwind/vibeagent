from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from threading import Event, Lock, RLock, Thread
from typing import Any

from .agent_runtime_utils import append_session_event
from .dynamic_workflow_node import ensure_node_workflow_runtime, request_to_dict, run_node_workflow
from .dynamic_workflow_store import (
    MAX_WORKFLOW_SOURCE_BYTES,
    create_workflow_record,
    list_workflow_records,
    read_workflow_record,
    read_workflow_source,
    summarize_workflow_record,
    write_workflow_record,
)
from .dynamic_workflow_types import WorkflowAgentExecutor, WorkflowAgentRequest, WorkflowRunSummary
from .redaction import redact_jsonable_payload
from .workspace_core import RunWorkspace
from .workspace_resolve import resolve_inside_run


@dataclass
class _ActiveWorkflow:
    cancel_event: Event
    done_event: Event
    thread: Thread


class DynamicWorkflowManager:
    def __init__(self, workspace: RunWorkspace, execute_agent: WorkflowAgentExecutor) -> None:
        self.workspace = workspace
        self.execute_agent = execute_agent
        self._lock = RLock()
        self._shared_code_lock = Lock()
        self._active: dict[str, _ActiveWorkflow] = {}

    def start(self, script_path: str) -> WorkflowRunSummary:
        ensure_node_workflow_runtime()
        path = resolve_inside_run(self.workspace.root, script_path)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Workflow script is not a regular project file: {script_path}")
        if path.suffix not in {".js", ".mjs", ".cjs"}:
            raise ValueError("Workflow script must use a .js, .mjs, or .cjs extension.")
        if path.stat().st_size > MAX_WORKFLOW_SOURCE_BYTES:
            raise ValueError("Workflow source exceeds 1000000 bytes.")
        source = path.read_text(encoding="utf-8")
        relative = path.relative_to(self.workspace.root).as_posix()
        record = create_workflow_record(
            self.workspace.root,
            script=relative,
            source=source,
            session_id=self.workspace.run_id,
        )
        self._launch(record, source)
        return summarize_workflow_record(record)

    def resume(self, workflow_id: str) -> WorkflowRunSummary:
        ensure_node_workflow_runtime()
        finishing: _ActiveWorkflow | None = None
        with self._lock:
            active = self._active.get(workflow_id)
            if active is not None and not active.done_event.is_set():
                current = read_workflow_record(self.workspace.root, workflow_id)
                if current.get("status") == "running":
                    raise ValueError(f"Workflow is already running: {workflow_id}")
                finishing = active
        if finishing is not None and not finishing.done_event.wait(2):
            raise ValueError(f"Workflow is still finishing: {workflow_id}")
        record = read_workflow_record(self.workspace.root, workflow_id)
        if record.get("status") == "completed":
            raise ValueError(f"Workflow already completed: {workflow_id}")
        if record.get("status") == "running" and _pid_is_alive(record.get("owner_pid")):
            raise ValueError(f"Workflow is owned by another live process: {workflow_id}")
        source = read_workflow_source(self.workspace.root, workflow_id)
        record["status"] = "running"
        record["owner_pid"] = os.getpid()
        record["error"] = None
        record["finished_at"] = None
        record["cached_calls"] = 0
        write_workflow_record(self.workspace.root, record)
        self._launch(record, source)
        return summarize_workflow_record(record)

    def stop(self, workflow_id: str) -> WorkflowRunSummary:
        with self._lock:
            active = self._active.get(workflow_id)
            if active is None or active.done_event.is_set():
                raise ValueError(f"Workflow is not running: {workflow_id}")
            active.cancel_event.set()
        active.done_event.wait(2)
        return self.get(workflow_id)

    def get(self, workflow_id: str) -> WorkflowRunSummary:
        return summarize_workflow_record(self._refresh_stale_record(read_workflow_record(self.workspace.root, workflow_id)))

    def list(self, limit: int = 20) -> list[WorkflowRunSummary]:
        return [
            summarize_workflow_record(self._refresh_stale_record(record))
            for record in list_workflow_records(self.workspace.root, limit)
        ]

    def close(self) -> None:
        with self._lock:
            active = list(self._active.items())
            for _workflow_id, runtime in active:
                if not runtime.done_event.is_set():
                    runtime.cancel_event.set()
        for _workflow_id, runtime in active:
            runtime.done_event.wait(2)

    def _launch(self, record: dict[str, Any], source: str) -> None:
        workflow_id = str(record["id"])
        cancel_event = Event()
        done_event = Event()

        def run() -> None:
            try:
                self._run_record(workflow_id, source, cancel_event)
            finally:
                done_event.set()

        thread = Thread(target=run, name=f"vibeagent-{workflow_id}", daemon=True)
        with self._lock:
            self._active[workflow_id] = _ActiveWorkflow(cancel_event, done_event, thread)
        append_session_event(
            self.workspace.session_dir,
            "workflow_started",
            {"workflow_id": workflow_id, "script": record["script"]},
        )
        thread.start()

    def _run_record(self, workflow_id: str, source: str, cancel_event: Event) -> None:
        def on_call_completed(
            request: WorkflowAgentRequest,
            result: dict[str, object],
            cached: bool,
        ) -> None:
            with self._lock:
                record = read_workflow_record(self.workspace.root, workflow_id)
                if cached:
                    record["cached_calls"] = int(record.get("cached_calls") or 0) + 1
                else:
                    calls = record.setdefault("calls", {})
                    if not isinstance(calls, dict):
                        raise ValueError(f"Workflow call cache is invalid: {workflow_id}")
                    calls[request.call_id] = {
                        "request": request_to_dict(request),
                        "result": _json_safe_result(result),
                    }
                    record["total_calls"] = len(calls)
                write_workflow_record(self.workspace.root, record)
            append_session_event(
                self.workspace.session_dir,
                "workflow_agent_completed",
                {
                    "workflow_id": workflow_id,
                    "call_id": request.call_id,
                    "cached": cached,
                    "ok": bool(result.get("ok", True)),
                },
            )

        def on_log(level: str, values: list[object]) -> None:
            append_session_event(
                self.workspace.session_dir,
                "workflow_log",
                {"workflow_id": workflow_id, "level": level, "values": values[:20]},
            )

        try:
            current = read_workflow_record(self.workspace.root, workflow_id)
            calls = current.get("calls")
            cached_calls = calls if isinstance(calls, dict) else {}
            def execute_for_run(request: WorkflowAgentRequest, cancelled) -> dict[str, object]:
                selected = replace(request, workflow_id=workflow_id)
                if selected.mode == "code" and selected.isolation is None:
                    with self._shared_code_lock:
                        return self.execute_agent(selected, cancelled)
                return self.execute_agent(selected, cancelled)

            result = run_node_workflow(
                source=source,
                filename=str(current.get("script") or "workflow.js"),
                execute_agent=execute_for_run,
                cancel_event=cancel_event,
                cached_calls=cached_calls,
                on_call_completed=on_call_completed,
                on_log=on_log,
            )
        except InterruptedError as error:
            self._finish(workflow_id, "stopped", error=str(error))
        except Exception as error:
            status = "stopped" if cancel_event.is_set() else "failed"
            self._finish(workflow_id, status, error=f"{type(error).__name__}: {error}")
        else:
            self._finish(workflow_id, "completed", result=result)

    def _finish(
        self,
        workflow_id: str,
        status: str,
        *,
        result: object = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            record = read_workflow_record(self.workspace.root, workflow_id)
            record["status"] = status
            record["owner_pid"] = None
            record["result"] = _json_safe_result(result)
            record["error"] = error
            record["finished_at"] = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            write_workflow_record(self.workspace.root, record)
        append_session_event(
            self.workspace.session_dir,
            "workflow_finished",
            {"workflow_id": workflow_id, "status": status, "error": error},
        )

    def _refresh_stale_record(self, record: dict[str, Any]) -> dict[str, Any]:
        if record.get("status") != "running":
            return record
        workflow_id = str(record.get("id") or "")
        with self._lock:
            active = self._active.get(workflow_id)
            locally_active = active is not None and not active.done_event.is_set()
        if locally_active or _pid_is_alive(record.get("owner_pid")):
            return record
        record["status"] = "interrupted"
        record["owner_pid"] = None
        record["error"] = "Workflow owner process exited before completion."
        write_workflow_record(self.workspace.root, record)
        return record


def _json_safe_result(value: object) -> object:
    try:
        json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)
    return redact_jsonable_payload(value)


def _pid_is_alive(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return False
    try:
        os.kill(value, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


__all__ = ["DynamicWorkflowManager"]
