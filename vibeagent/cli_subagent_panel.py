from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path
import re
import shutil
import sys
from threading import Event, RLock, Thread
from time import monotonic
from typing import TextIO

from .background_delegate_runtime import list_background_delegate_snapshots
from .plugin_subagent_status_line import (
    ResolvedSubagentStatusLine,
    resolve_subagent_status_line,
    run_subagent_status_line,
)
from .session_event_observers import observe_session_events
from .session_utils import parse_usage_payload
from .types import (
    ApprovalDecision,
    ApprovalHandler,
    ApprovalPolicy,
    ApprovalRequest,
    UserInputAnswer,
    UserInputHandler,
    UserInputRequest,
)
from .workspace_core import RunWorkspace


ANSI_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
REFRESH_SECONDS = 0.3
CUSTOM_REFRESH_SECONDS = 1.0


class SubagentPanel:
    def __init__(self, project_root: Path, *, stream: TextIO | None = None) -> None:
        self.project_root = project_root.resolve()
        self.stream = stream or sys.stdout
        self.enabled = getattr(self.stream, "isatty", lambda: False)() is True
        self.workspace: RunWorkspace | None = None
        self.config: ResolvedSubagentStatusLine | None = None
        self.config_error: str | None = None
        self.custom_authorized = False
        self.permission_mode = "default"
        self._lock = RLock()
        self._stop = Event()
        self._thread: Thread | None = None
        self._observer: AbstractContextManager[None] | None = None
        self._tokens: dict[str, int] = {}
        self._token_samples: dict[str, list[dict[str, int]]] = {}
        self._rendered_lines = 0
        self._last_text = ""
        self._last_custom_at = 0.0
        self._custom_rows: dict[str, str] = {}
        self._suspended = False
        if self.enabled:
            try:
                self.config = resolve_subagent_status_line(self.project_root)
            except (OSError, UnicodeError, ValueError) as error:
                self.config_error = str(error)

    def authorize_custom(self, handler: ApprovalHandler | None, policy: ApprovalPolicy) -> None:
        self.permission_mode = {
            "allow": "bypassPermissions",
            "auto": "auto",
            "dontAsk": "dontAsk",
            "plan": "plan",
        }.get(policy, "default")
        if self.config is None:
            return
        if policy == "allow":
            self.custom_authorized = True
            return
        if policy in {"deny", "dontAsk", "plan"} or handler is None:
            return
        decision = handler(
            ApprovalRequest(
                action_type="run_command",
                target=self.config.command,
                risk=f"Plugin {self.config.plugin} refreshes the interactive subagent status line.",
            )
        )
        self.custom_authorized = decision.approved

    def bind(self, workspace: RunWorkspace) -> None:
        if not self.enabled:
            return
        self.workspace = workspace
        self._observer = observe_session_events(workspace.session_dir, self._observe_event)
        self._observer.__enter__()
        self._thread = Thread(target=self._refresh_loop, name="vibeagent-subagent-panel", daemon=True)
        self._thread.start()

    def log(self, _status: str, _detail: str | None) -> None:
        self.refresh()

    def wrap_approval_handler(self, handler: ApprovalHandler | None) -> ApprovalHandler | None:
        if handler is None:
            return None

        def wrapped(request: ApprovalRequest) -> ApprovalDecision:
            self.clear()
            try:
                return handler(request)
            finally:
                self.refresh(force=True)

        needs_prompt = getattr(handler, "needs_prompt", None)
        if callable(needs_prompt):
            setattr(wrapped, "needs_prompt", needs_prompt)

        return wrapped

    def wrap_user_input_handler(self, handler: UserInputHandler | None) -> UserInputHandler | None:
        if handler is None:
            return None

        def wrapped(request: UserInputRequest) -> UserInputAnswer | None:
            self.clear()
            try:
                return handler(request)
            finally:
                self.refresh(force=True)

        return wrapped

    def refresh(self, *, force: bool = False) -> None:
        workspace = self.workspace
        if not self.enabled or workspace is None:
            return
        with self._lock:
            if self._suspended:
                return
        snapshots = list_background_delegate_snapshots(workspace)
        if not snapshots:
            self.clear()
            return
        columns = max(20, shutil.get_terminal_size((80, 24)).columns)
        tasks = [self._task_payload(item) for item in snapshots]
        now = monotonic()
        if self.config is not None and self.custom_authorized and (
            force or now - self._last_custom_at >= CUSTOM_REFRESH_SECONDS
        ):
            self._last_custom_at = now
            try:
                self._custom_rows = run_subagent_status_line(
                    workspace,
                    self.config,
                    {
                        "session_id": workspace.run_id,
                        "transcript_path": str(workspace.session_dir / "events.jsonl"),
                        "cwd": str(workspace.root),
                        "permission_mode": self.permission_mode,
                        "hook_event_name": "SubagentStatusLine",
                        "columns": columns,
                        "tasks": tasks,
                    },
                )
            except (OSError, ValueError) as error:
                self.config_error = str(error)
                self.custom_authorized = False
        rows = []
        for task in tasks:
            task_id = str(task["id"])
            custom = self._custom_rows.get(task_id)
            if custom == "":
                continue
            default = f"{task['name']}  {task['status']}  {task['label']}  {task['tokenCount']} tok"
            rows.append(_clip_status_text(custom if custom is not None else default, columns - 2))
        text = "\n".join([f"Agents ({len(tasks)})", *(f"  {row}" for row in rows)])
        self._render(text, force=force)

    def clear(self) -> None:
        if not self.enabled:
            return
        with self._lock:
            if self._rendered_lines:
                self.stream.write("\x1b[1A\r\x1b[2K" * self._rendered_lines)
                self.stream.flush()
            self._rendered_lines = 0
            self._last_text = ""

    def pause(self) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._suspended = True
            self.clear()

    def resume(self) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._suspended = False
        self.refresh(force=True)

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self._observer is not None:
            self._observer.__exit__(None, None, None)
            self._observer = None
        self.clear()

    def _refresh_loop(self) -> None:
        while not self._stop.wait(REFRESH_SECONDS):
            self.refresh()

    def _observe_event(self, _session_dir, event: dict[str, object]) -> None:
        if event.get("type") != "subagent_model":
            return
        task_id = event.get("subagent_id")
        if not isinstance(task_id, str):
            return
        usage = parse_usage_payload(event.get("usage"))
        tokens = usage["total_tokens"]
        with self._lock:
            total = self._tokens.get(task_id, 0) + tokens
            self._tokens[task_id] = total
            self._token_samples.setdefault(task_id, []).append(
                {"timestamp": int(datetime.now(UTC).timestamp() * 1000), "tokens": total}
            )
            self._token_samples[task_id] = self._token_samples[task_id][-20:]

    def _task_payload(self, snapshot) -> dict[str, object]:
        name = snapshot.action.teammate_name or snapshot.action.agent or snapshot.task_id
        with self._lock:
            token_count = self._tokens.get(snapshot.task_id, 0)
            token_samples = list(self._token_samples.get(snapshot.task_id, ()))
        return {
            "id": snapshot.task_id,
            "name": name,
            "type": snapshot.action.agent or snapshot.action.mode,
            "status": snapshot.status,
            "description": snapshot.action.task,
            "label": " ".join(snapshot.action.task.split()),
            "startTime": int(snapshot.started_at * 1000),
            "tokenCount": token_count,
            "tokenSamples": token_samples,
            "cwd": str(self.project_root),
        }

    def _render(self, text: str, *, force: bool) -> None:
        with self._lock:
            if self._suspended:
                return
            if text == self._last_text and not force:
                return
            if self._rendered_lines:
                self.stream.write("\x1b[1A\r\x1b[2K" * self._rendered_lines)
            self.stream.write(text + "\n")
            self.stream.flush()
            self._rendered_lines = len(text.splitlines())
            self._last_text = text


def _clip_status_text(value: str, width: int) -> str:
    text = " ".join(ANSI_PATTERN.sub("", value).split())
    if len(text) <= width:
        return text
    return text[: max(1, width - 3)] + "..."


__all__ = ["SubagentPanel"]
