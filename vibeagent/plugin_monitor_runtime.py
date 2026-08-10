from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
from queue import Empty, Full, Queue
from threading import RLock

from .agent_runtime_utils import append_session_event
from .command_safety import get_blocked_command_reason
from .command_sandbox import prepare_command_launch
from .plugin_monitor_config import PluginMonitorConfig, read_plugin_monitor_configs
from .plugin_monitor_process import RunningPluginMonitor
from .redaction import redact_sensitive_text
from .workspace_core import RunWorkspace
from .workspace_metadata_files import has_symlink_component


MAX_MONITOR_NOTIFICATIONS = 100
MAX_MONITOR_QUEUE = 1_000


@dataclass(frozen=True)
class PluginMonitorNotification:
    plugin: str
    monitor: str
    description: str
    message: str
    status: str = "output"


AuthorizeMonitor = Callable[[PluginMonitorConfig, int], bool]


class PluginMonitorRuntime:
    def __init__(self, workspace: RunWorkspace) -> None:
        self.workspace = workspace
        self._queue: Queue[PluginMonitorNotification] = Queue(MAX_MONITOR_QUEUE)
        self._lock = RLock()
        self._running: dict[tuple[str, str], RunningPluginMonitor] = {}
        self._dropped = 0
        self._closing = False
        try:
            self.configs = tuple(read_plugin_monitor_configs(workspace))
            self.load_error = None
        except (OSError, UnicodeError, ValueError) as error:
            self.configs = ()
            self.load_error = str(error)

    def start_always(self, authorize: AuthorizeMonitor, *, iteration: int = 0) -> int:
        if self.load_error is not None:
            self._emit(
                PluginMonitorNotification(
                    plugin="configuration",
                    monitor="load",
                    description="Plugin monitor configuration",
                    message=self.load_error,
                    status="error",
                )
            )
            append_session_event(
                self.workspace.session_dir,
                "plugin_monitors_load_failed",
                {"error": self.load_error},
            )
            return 0
        return sum(
            self._start(config, authorize, iteration)
            for config in self.configs
            if config.when == "always"
        )

    def start_for_skill(
        self,
        plugin: str,
        skill: str,
        authorize: AuthorizeMonitor,
        *,
        iteration: int,
    ) -> int:
        return sum(
            self._start(config, authorize, iteration)
            for config in self.configs
            if config.plugin == plugin and config.skill == skill
        )

    def collect(self, max_items: int = MAX_MONITOR_NOTIFICATIONS) -> list[PluginMonitorNotification]:
        selected: list[PluginMonitorNotification] = []
        while len(selected) < max_items:
            try:
                selected.append(self._queue.get_nowait())
            except Empty:
                break
        with self._lock:
            dropped = self._dropped
            self._dropped = 0
        if dropped and len(selected) < max_items:
            selected.append(
                PluginMonitorNotification(
                    plugin="runtime",
                    monitor="overflow",
                    description="Plugin monitor notification queue",
                    message=f"Dropped {dropped} monitor notification(s) because the queue was full.",
                    status="warning",
                )
            )
        return selected

    def close(self) -> None:
        with self._lock:
            self._closing = True
            running = list(self._running.values())
            self._running.clear()
        for item in running:
            item.close()
        if running:
            append_session_event(
                self.workspace.session_dir,
                "plugin_monitors_stopped",
                {"count": len(running)},
            )

    def _start(
        self,
        config: PluginMonitorConfig,
        authorize: AuthorizeMonitor,
        iteration: int,
    ) -> int:
        key = (config.plugin, config.name)
        with self._lock:
            existing = self._running.get(key)
            if self._closing or (existing is not None and existing.process.poll() is None):
                return 0
        if not authorize(config, iteration):
            self._emit(
                PluginMonitorNotification(
                    plugin=config.plugin,
                    monitor=config.name,
                    description=config.description,
                    message="Monitor startup was denied by session approval or project permissions.",
                    status="denied",
                )
            )
            self._record_start(config, iteration, "denied")
            return 0
        blocked = get_blocked_command_reason(config.command)
        if blocked is not None:
            self._start_failed(config, iteration, f"Command blocked: {blocked}")
            return 0
        try:
            self._ensure_plugin_data(config.plugin_data)
            launch = prepare_command_launch(
                self.workspace, config.command, self.workspace.root
            )
            if launch.error is not None:
                raise ValueError(launch.error)
            environment = dict(launch.environment or os.environ)
            environment.update(
                {
                    "CLAUDE_PLUGIN_ROOT": config.plugin_root.as_posix(),
                    "CLAUDE_PLUGIN_DATA": config.plugin_data.as_posix(),
                    "CLAUDE_PROJECT_DIR": self.workspace.root.as_posix(),
                }
            )
            running = RunningPluginMonitor.launch(
                config,
                launch.argv,
                self.workspace.root,
                environment,
            )
        except (OSError, ValueError) as error:
            self._start_failed(config, iteration, str(error))
            return 0
        with self._lock:
            self._running[key] = running
        running.start_readers(self._emit_output, self._monitor_exited)
        self._record_start(config, iteration, "started", pid=running.process.pid)
        return 1

    def _monitor_exited(
        self, running: RunningPluginMonitor, return_code: int
    ) -> None:
        key = (running.config.plugin, running.config.name)
        with self._lock:
            if self._running.get(key) is running:
                self._running.pop(key, None)
            closing = self._closing or running.closing
        if closing:
            return
        detail = f"Monitor process exited with code {return_code}."
        if running.stderr_tail.strip():
            detail += f" stderr: {redact_sensitive_text(running.stderr_tail.strip()[-2_000:])}"
        self._emit(
            PluginMonitorNotification(
                plugin=running.config.plugin,
                monitor=running.config.name,
                description=running.config.description,
                message=detail,
                status="exited" if return_code == 0 else "error",
            )
        )
        append_session_event(
            self.workspace.session_dir,
            "plugin_monitor_exited",
            {
                "plugin": running.config.plugin,
                "monitor": running.config.name,
                "exit_code": return_code,
            },
        )

    def _emit_output(self, config: PluginMonitorConfig, line: str) -> None:
        if not line:
            return
        self._emit(
            PluginMonitorNotification(
                plugin=config.plugin,
                monitor=config.name,
                description=config.description,
                message=redact_sensitive_text(line),
            )
        )

    def _emit(self, notification: PluginMonitorNotification) -> None:
        try:
            self._queue.put_nowait(notification)
        except Full:
            with self._lock:
                self._dropped += 1

    def _start_failed(
        self, config: PluginMonitorConfig, iteration: int, message: str
    ) -> None:
        self._emit(
            PluginMonitorNotification(
                plugin=config.plugin,
                monitor=config.name,
                description=config.description,
                message=message,
                status="error",
            )
        )
        self._record_start(config, iteration, "failed", error=message)

    def _record_start(
        self,
        config: PluginMonitorConfig,
        iteration: int,
        status: str,
        *,
        pid: int | None = None,
        error: str | None = None,
    ) -> None:
        append_session_event(
            self.workspace.session_dir,
            "plugin_monitor_start",
            {
                "iteration": iteration,
                "plugin": config.plugin,
                "monitor": config.name,
                "source": config.source,
                "when": config.when,
                "status": status,
                "pid": pid,
                "error": error,
            },
        )

    def _ensure_plugin_data(self, path: Path) -> None:
        root = self.workspace.root.resolve()
        if has_symlink_component(root, path):
            raise ValueError("Plugin monitor data path contains a symbolic link.")
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        resolved = path.resolve()
        if root not in resolved.parents or path.is_symlink() or not path.is_dir():
            raise ValueError("Plugin monitor data path is outside the project runtime.")


__all__ = ["PluginMonitorNotification", "PluginMonitorRuntime"]
