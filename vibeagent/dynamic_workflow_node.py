from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import json
import os
import re
import shutil
import subprocess
from threading import Event, Lock, Thread
from typing import Any, Callable, TextIO

from .bounded_text_lines import TextLineTooLongError, iter_bounded_text_lines
from .dynamic_workflow_protocol import parse_workflow_agent_request, request_to_dict
from .dynamic_workflow_script import NODE_WORKFLOW_BRIDGE
from .dynamic_workflow_types import WorkflowAgentExecutor, WorkflowAgentRequest
from .process_command_capture import BoundedTextCapture, OUTPUT_READ_CHUNK_CHARS


MAX_WORKFLOW_CALLS = 1_000
MAX_WORKFLOW_CONCURRENCY = 16
MAX_PROTOCOL_LINE_BYTES = 1_100_000
MAX_WORKFLOW_STDERR_CHARS = 20_000
MIN_NODE_MAJOR_VERSION = 22


def ensure_node_workflow_runtime() -> None:
    executable = shutil.which("node", path=os.environ.get("PATH"))
    if executable is None:
        raise ValueError("Dynamic workflows require Node.js 22 or newer on PATH.")
    completed = subprocess.run(
        [executable, "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=5,
        env=_workflow_process_env(),
        check=False,
    )
    match = re.fullmatch(r"v(\d+)(?:\.\d+){2}\s*", completed.stdout)
    if completed.returncode != 0 or match is None or int(match.group(1)) < MIN_NODE_MAJOR_VERSION:
        version = completed.stdout.strip() or completed.stderr.strip() or "unknown"
        raise ValueError(f"Dynamic workflows require Node.js 22 or newer; found {version}.")


def run_node_workflow(
    *,
    source: str,
    filename: str,
    execute_agent: WorkflowAgentExecutor,
    cancel_event: Event,
    cached_calls: dict[str, object],
    on_call_completed: Callable[[WorkflowAgentRequest, dict[str, object], bool], None],
    on_log: Callable[[str, list[object]], None] | None = None,
) -> object:
    process = subprocess.Popen(
        ["node", "--permission", "--input-type=commonjs", "-e", NODE_WORKFLOW_BRIDGE],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
        env=_workflow_process_env(),
    )
    if process.stdin is None or process.stdout is None or process.stderr is None:  # pragma: no cover
        process.kill()
        raise RuntimeError("Failed to create workflow bridge pipes.")
    stderr_capture = BoundedTextCapture(MAX_WORKFLOW_STDERR_CHARS)
    stderr_thread = Thread(target=_read_stderr, args=(process.stderr, stderr_capture), daemon=True)
    stderr_thread.start()
    cancel_thread = Thread(target=_terminate_when_cancelled, args=(cancel_event, process), daemon=True)
    cancel_thread.start()
    writer_lock = Lock()
    futures: set[Future[None]] = set()
    total_calls = 0
    done_message: dict[str, Any] | None = None

    def write_message(message: dict[str, object]) -> None:
        with writer_lock:
            if process.poll() is not None:
                return
            process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
            process.stdin.flush()

    write_message({"type": "init", "source": source, "filename": filename})
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKFLOW_CONCURRENCY, thread_name_prefix="vibeagent-workflow") as pool:
            for line in iter_bounded_text_lines(process.stdout, max_line_bytes=MAX_PROTOCOL_LINE_BYTES):
                if cancel_event.is_set():
                    process.terminate()
                    raise InterruptedError("Workflow stopped.")
                try:
                    message = json.loads(line)
                except json.JSONDecodeError as error:
                    raise RuntimeError(f"Workflow bridge emitted invalid JSON: {error}") from error
                message_type = message.get("type")
                if message_type == "log":
                    if on_log is not None:
                        values = message.get("values")
                        on_log(str(message.get("level") or "log"), values if isinstance(values, list) else [])
                    continue
                if message_type == "done":
                    done_message = message
                    break
                if message_type != "agent":
                    raise RuntimeError(f"Workflow bridge emitted unsupported message: {message_type!r}")
                total_calls += 1
                if total_calls > MAX_WORKFLOW_CALLS:
                    write_message(_error_response(str(message.get("call_id") or ""), "Workflow exceeded 1000 agent calls."))
                    continue
                request = parse_workflow_agent_request(message)
                cached = cached_calls.get(request.call_id)
                if isinstance(cached, dict):
                    cached_request = cached.get("request")
                    cached_result = cached.get("result")
                    if cached_request != request_to_dict(request) or not isinstance(cached_result, dict):
                        write_message(_error_response(request.call_id, f"Resume mismatch at {request.call_id}."))
                    else:
                        on_call_completed(request, cached_result, True)
                        write_message({"type": "response", "call_id": request.call_id, "ok": True, "result": cached_result})
                    continue
                futures.add(
                    pool.submit(
                        _execute_and_respond,
                        request,
                        execute_agent,
                        cancel_event,
                        on_call_completed,
                        write_message,
                    )
                )
            for future in futures:
                future.result()
    except TextLineTooLongError as error:
        process.kill()
        raise RuntimeError("Workflow bridge emitted an oversized protocol message.") from error
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
        stderr_thread.join(timeout=1)
        cancel_thread.join(timeout=1)
        process.stdin.close()
        process.stdout.close()
        process.stderr.close()

    if cancel_event.is_set():
        raise InterruptedError("Workflow stopped.")
    if done_message is None:
        detail = stderr_capture.render()[0].strip()
        raise RuntimeError(f"Workflow bridge exited before completion{': ' + detail if detail else '.'}")
    if not bool(done_message.get("ok")):
        raise RuntimeError(str(done_message.get("error") or "Workflow script failed."))
    return done_message.get("result")


def _execute_and_respond(
    request: WorkflowAgentRequest,
    execute_agent: WorkflowAgentExecutor,
    cancel_event: Event,
    on_call_completed: Callable[[WorkflowAgentRequest, dict[str, object], bool], None],
    write_message: Callable[[dict[str, object]], None],
) -> None:
    try:
        result = execute_agent(request, cancel_event.is_set)
        if not isinstance(result, dict):
            raise TypeError("Workflow agent executor must return an object.")
        on_call_completed(request, result, False)
        write_message({"type": "response", "call_id": request.call_id, "ok": True, "result": result})
    except Exception as error:
        write_message(_error_response(request.call_id, f"{type(error).__name__}: {error}"))


def _error_response(call_id: str, error: str) -> dict[str, object]:
    return {"type": "response", "call_id": call_id, "ok": False, "error": error}


def _read_stderr(stream: TextIO, capture: BoundedTextCapture) -> None:
    while True:
        chunk = stream.read(OUTPUT_READ_CHUNK_CHARS)
        if not chunk:
            return
        capture.append(chunk)


def _terminate_when_cancelled(cancel_event: Event, process: subprocess.Popen[str]) -> None:
    while process.poll() is None:
        if cancel_event.wait(timeout=0.1):
            process.terminate()
            return


def _workflow_process_env() -> dict[str, str]:
    return {
        key: os.environ[key]
        for key in ("PATH", "LANG", "LC_ALL", "SYSTEMROOT", "WINDIR")
        if key in os.environ
    }


__all__ = [
    "ensure_node_workflow_runtime",
    "MAX_WORKFLOW_CALLS",
    "MAX_WORKFLOW_CONCURRENCY",
    "parse_workflow_agent_request",
    "request_to_dict",
    "run_node_workflow",
]
