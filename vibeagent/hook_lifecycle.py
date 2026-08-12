from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from time import monotonic
from uuid import uuid4

from .agent_hook_results import HookRunResult
from .agent_runtime_utils import append_session_event
from .process_command_runtime import truncate_command_output
from .redaction import redact_sensitive_text
from .workspace_hook_types import ProjectHook


MAX_HOOK_STREAM_OUTPUT_CHARS = 10_000
HOOK_PROGRESS_INTERVAL_SECONDS = 1.0


@dataclass
class HookLifecycleReporter:
    session_dir: Path
    hook: ProjectHook
    iteration: int
    hook_index: int
    target: str
    hook_id: str = field(default_factory=lambda: str(uuid4()))
    _started_at: float = field(default_factory=monotonic, init=False, repr=False)
    _last_progress_at: float = field(default=0.0, init=False, repr=False)
    _stdout: str = field(default="", init=False, repr=False)
    _stderr: str = field(default="", init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    @property
    def hook_name(self) -> str:
        source_name = Path(self.hook.source).name or "configured"
        return f"{self.hook.handler_type}:{source_name}#{self.hook_index}"[:300]

    def started(self) -> None:
        append_session_event(
            self.session_dir,
            "hook_started",
            self._base_payload(),
        )

    def command_output(self, stdout: str, stderr: str) -> None:
        with self._lock:
            self._stdout = _append_bounded(self._stdout, stdout)
            self._stderr = _append_bounded(self._stderr, stderr)
            now = monotonic()
            if (
                now - self._started_at < HOOK_PROGRESS_INTERVAL_SECONDS
                or now - self._last_progress_at < HOOK_PROGRESS_INTERVAL_SECONDS
            ):
                return
            self._last_progress_at = now
            append_session_event(
                self.session_dir,
                "hook_progress",
                {
                    **self._base_payload(),
                    "stdout": self._stdout,
                    "stderr": self._stderr,
                    "output": _combined_output(self._stdout, self._stderr),
                },
            )

    def response(self, result: HookRunResult) -> None:
        stdout = _bounded_output(result.stdout)
        stderr = _bounded_output(result.stderr)
        output = _combined_output(stdout, stderr) or _bounded_output(result.message)
        payload: dict[str, object] = {
            **self._base_payload(),
            "stdout": stdout,
            "stderr": stderr,
            "output": output,
            "outcome": _hook_outcome(result),
            "status": result.status,
        }
        if result.exit_code is not None:
            payload["exit_code"] = result.exit_code
        append_session_event(self.session_dir, "hook_response", payload)

    def failed(self, error: BaseException) -> None:
        message = _bounded_output(f"{type(error).__name__}: {error}")
        append_session_event(
            self.session_dir,
            "hook_response",
            {
                **self._base_payload(),
                "stdout": self._stdout,
                "stderr": self._stderr,
                "output": message,
                "outcome": "cancelled" if isinstance(error, KeyboardInterrupt) else "error",
                "status": "cancelled" if isinstance(error, KeyboardInterrupt) else "failed",
            },
        )

    def _base_payload(self) -> dict[str, object]:
        return {
            "iteration": self.iteration,
            "index": self.hook_index,
            "hook_id": self.hook_id,
            "hook_name": self.hook_name,
            "event": self.hook.event,
            "tool": self.target,
            "source": self.hook.source,
            "handler_type": self.hook.handler_type,
        }


def _append_bounded(existing: str, chunk: str) -> str:
    combined = existing + redact_sensitive_text(chunk)
    return truncate_command_output(combined, MAX_HOOK_STREAM_OUTPUT_CHARS)[0]


def _bounded_output(value: str) -> str:
    return truncate_command_output(
        redact_sensitive_text(value),
        MAX_HOOK_STREAM_OUTPUT_CHARS,
    )[0]


def _combined_output(stdout: str, stderr: str) -> str:
    return _bounded_output("\n".join(value for value in (stdout, stderr) if value))


def _hook_outcome(result: HookRunResult) -> str:
    if result.status in {"cancelled", "discarded"}:
        return "cancelled"
    return "success" if result.ok else "error"


__all__ = ["HookLifecycleReporter"]
