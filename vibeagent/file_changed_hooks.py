from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat

from .agent_lifecycle_runtime import AgentLifecycleRuntime
from .session_file_watch_state import MAX_WATCH_PATHS, read_dynamic_watch_paths
from .session_working_directory import read_session_cwd
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks


MAX_FILE_EVENTS_PER_POLL = 50


@dataclass(frozen=True)
class FileChangedEvent:
    path: Path
    event: str


@dataclass(frozen=True)
class FileChangedPollResult:
    events: tuple[FileChangedEvent, ...] = ()
    system_messages: tuple[str, ...] = ()


@dataclass(frozen=True)
class _FileFingerprint:
    mode: int
    size: int
    mtime_ns: int
    ctime_ns: int
    inode: int


class FileChangedHookRuntime:
    def __init__(
        self,
        workspace: RunWorkspace,
        hooks: ProjectHooks,
        lifecycle: AgentLifecycleRuntime,
    ) -> None:
        self.workspace = workspace
        self.hooks = hooks
        self.lifecycle = lifecycle
        self._cwd = read_session_cwd(workspace)
        self._snapshots: dict[Path, _FileFingerprint | None] = {}
        self._sync_paths()

    def poll(
        self,
        *,
        workspace: RunWorkspace | None = None,
        iteration: int = 0,
    ) -> FileChangedPollResult:
        if workspace is not None and workspace != self.workspace:
            self.workspace = workspace
        cwd = read_session_cwd(self.workspace)
        if cwd != self._cwd:
            self._cwd = cwd
        paths = self._sync_paths()
        events: list[FileChangedEvent] = []
        for path in paths:
            previous = self._snapshots[path]
            try:
                current = _fingerprint(path)
            except OSError:
                continue
            event = _change_event(previous, current)
            self._snapshots[path] = current
            if event is not None:
                events.append(FileChangedEvent(path=path, event=event))
            if len(events) >= MAX_FILE_EVENTS_PER_POLL:
                break

        system_messages: list[str] = []
        for changed in events:
            result = self.lifecycle.file_changed(
                self.workspace,
                str(changed.path),
                changed.event,
                iteration=iteration,
            )
            system_messages.extend(result.system_messages)
        return FileChangedPollResult(
            events=tuple(events),
            system_messages=tuple(system_messages),
        )

    def _sync_paths(self) -> tuple[Path, ...]:
        static_paths = tuple(
            self._cwd / name for name in static_watch_filenames(self.hooks)
        )
        dynamic_paths = read_dynamic_watch_paths(self.workspace)
        paths = tuple(dict.fromkeys((*static_paths, *dynamic_paths)))[:MAX_WATCH_PATHS]
        selected = set(paths)
        for stale in set(self._snapshots) - selected:
            del self._snapshots[stale]
        for path in paths:
            if path in self._snapshots:
                continue
            try:
                self._snapshots[path] = _fingerprint(path)
            except OSError:
                self._snapshots[path] = None
        return paths


def static_watch_filenames(hooks: ProjectHooks) -> tuple[str, ...]:
    names: list[str] = []
    for hook in hooks.hooks:
        if hook.event != "FileChanged" or not hook.matcher:
            continue
        for name in hook.matcher.split("|"):
            if _valid_literal_filename(name) and name not in names:
                names.append(name)
            if len(names) >= MAX_WATCH_PATHS:
                return tuple(names)
    return tuple(names)


def _valid_literal_filename(name: str) -> bool:
    return (
        bool(name)
        and name not in {".", "..", ".git", ".vibeagent"}
        and len(name) <= 255
        and "\x00" not in name
        and "/" not in name
        and "\\" not in name
    )


def _fingerprint(path: Path) -> _FileFingerprint | None:
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return None
    return _FileFingerprint(
        mode=stat.S_IFMT(info.st_mode),
        size=info.st_size,
        mtime_ns=info.st_mtime_ns,
        ctime_ns=info.st_ctime_ns,
        inode=info.st_ino,
    )


def _change_event(
    previous: _FileFingerprint | None,
    current: _FileFingerprint | None,
) -> str | None:
    if previous is None and current is not None:
        return "add"
    if previous is not None and current is None:
        return "unlink"
    if previous is not None and current is not None and previous != current:
        return "change"
    return None


__all__ = [
    "FileChangedEvent",
    "FileChangedHookRuntime",
    "FileChangedPollResult",
    "static_watch_filenames",
]
