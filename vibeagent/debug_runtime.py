from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import stat
import sys
from threading import RLock
from typing import Any

from .redaction import redact_jsonable_payload, redact_sensitive_text
from .session_event_observers import observe_session_events
from .types import AgentLogger
from .workspace_core import RunWorkspace


DEBUG_CATEGORY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
MAX_DEBUG_FILTER_CHARS = 1_000
MAX_DEBUG_RECORD_CHARS = 100_000


@dataclass(frozen=True)
class DebugFilter:
    included: frozenset[str] = frozenset()
    excluded: frozenset[str] = frozenset()

    def allows(self, category: str) -> bool:
        normalized = category.lower()
        if normalized in self.excluded or "*" in self.excluded:
            return False
        return not self.included or normalized in self.included or "*" in self.included


@dataclass(frozen=True)
class DebugOptions:
    enabled: bool = False
    categories: DebugFilter = DebugFilter()
    file: Path | None = None


class DebugRuntime:
    def __init__(self, options: DebugOptions) -> None:
        self.options = options
        self._lock = RLock()
        self._write_error_reported = False

    @property
    def enabled(self) -> bool:
        return self.options.enabled

    @property
    def logger(self) -> AgentLogger | None:
        return self.log_status if self.enabled else None

    def log_status(self, status: str, detail: str | None) -> None:
        payload: dict[str, object] = {"status": status}
        if detail:
            payload["detail"] = redact_sensitive_text(detail)
        self.emit(_status_category(status), "status", payload)

    def observe_event(self, _session_dir: Path, event: dict[str, Any]) -> None:
        event_type = str(event.get("type") or "event")
        self.emit(_event_category(event_type), event_type, event)

    def emit(self, category: str, event: str, payload: dict[str, Any]) -> None:
        if not self.enabled or not self.options.categories.allows(category):
            return
        safe_payload = redact_jsonable_payload(payload)
        record = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "category": category,
            "event": event,
            "payload": safe_payload,
        }
        encoded = json.dumps(record, ensure_ascii=False, sort_keys=True)
        if len(encoded) > MAX_DEBUG_RECORD_CHARS:
            encoded = json.dumps(
                {
                    "timestamp": record["timestamp"],
                    "category": category,
                    "event": event,
                    "payload": {"truncated": True, "originalChars": len(encoded)},
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        with self._lock:
            if self.options.file is None:
                print(f"[debug:{category}] {event} {encoded}", file=sys.stderr)
                return
            try:
                _append_private_line(self.options.file, encoded)
            except OSError as error:
                if not self._write_error_reported:
                    self._write_error_reported = True
                    print(
                        f"Debug log write failed: {redact_sensitive_text(str(error))}",
                        file=sys.stderr,
                    )

    def event_scope(self, workspace: RunWorkspace | None):
        if not self.enabled or workspace is None:
            return nullcontext()
        return observe_session_events(workspace.session_dir, self.observe_event)


def normalize_debug_arguments(argv: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    options = True
    for value in argv:
        if options and value == "--":
            options = False
            normalized.append(value)
        elif options and value.startswith("--debug="):
            normalized.extend(("--debug", "--_debug-filter", value.partition("=")[2]))
        else:
            normalized.append(value)
    return normalized


def resolve_debug_options(
    enabled: bool,
    category_filter: str | None,
    debug_file: str | None,
    *,
    invocation_root: Path,
) -> DebugOptions:
    active = enabled or debug_file is not None
    categories = parse_debug_filter(category_filter)
    path = _resolve_debug_file(debug_file, invocation_root) if debug_file is not None else None
    return DebugOptions(enabled=active, categories=categories, file=path)


def parse_debug_filter(value: str | None) -> DebugFilter:
    if value is None or not value.strip():
        return DebugFilter()
    normalized = value.strip()
    if len(normalized) > MAX_DEBUG_FILTER_CHARS:
        raise ValueError(f"--debug category filter cannot exceed {MAX_DEBUG_FILTER_CHARS} characters.")
    included: set[str] = set()
    excluded: set[str] = set()
    for raw in normalized.split(","):
        item = raw.strip()
        negative = item.startswith("!")
        name = item[1:] if negative else item
        if name != "*" and DEBUG_CATEGORY_PATTERN.fullmatch(name) is None:
            raise ValueError("--debug categories must be comma-separated names optionally prefixed with '!'.")
        target = excluded if negative else included
        target.add(name.lower())
    overlap = included & excluded
    if overlap:
        names = ", ".join(sorted(overlap))
        raise ValueError(f"--debug categories cannot both include and exclude: {names}.")
    return DebugFilter(frozenset(included), frozenset(excluded))


def combine_agent_loggers(*loggers: AgentLogger | None) -> AgentLogger | None:
    active = tuple(logger for logger in loggers if logger is not None)
    if not active:
        return None
    if len(active) == 1:
        return active[0]

    def combined(status: str, detail: str | None) -> None:
        for logger in active:
            logger(status, detail)

    return combined


def combine_event_observers(
    *observers: Callable[[Path, dict[str, Any]], None] | None,
) -> Callable[[Path, dict[str, Any]], None] | None:
    active = tuple(observer for observer in observers if observer is not None)
    if not active:
        return None
    if len(active) == 1:
        return active[0]

    def combined(session_dir: Path, event: dict[str, Any]) -> None:
        for observer in active:
            observer(session_dir, event)

    return combined


def _resolve_debug_file(value: str, invocation_root: Path) -> Path:
    normalized = value.strip()
    if not normalized or "\0" in normalized:
        raise ValueError("--debug-file requires a non-empty path.")
    path = Path(normalized).expanduser()
    path = path if path.is_absolute() else invocation_root / path
    parent = path.parent.resolve()
    if not parent.is_dir():
        raise ValueError(f"--debug-file parent directory not found: {path.parent}")
    resolved = parent / path.name
    if resolved.is_symlink() or (resolved.exists() and not resolved.is_file()):
        raise ValueError(f"--debug-file must be a regular non-symlink file: {resolved}")
    try:
        _append_private_line(resolved, "")
    except OSError as error:
        raise ValueError(f"Could not open --debug-file: {redact_sensitive_text(str(error))}") from error
    return resolved


def _append_private_line(path: Path, line: str) -> None:
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise OSError("Debug log path is not a regular file.")
        os.fchmod(descriptor, 0o600)
        if line:
            pending = memoryview((line + "\n").encode("utf-8"))
            while pending:
                written = os.write(descriptor, pending)
                if written <= 0:
                    raise OSError("Could not write debug log record.")
                pending = pending[written:]
    finally:
        os.close(descriptor)


def _event_category(event_type: str) -> str:
    lowered = event_type.lower()
    if "mcp" in lowered:
        return "mcp"
    if "hook" in lowered:
        return "hooks"
    if any(token in lowered for token in ("approval", "permission", "sandbox")):
        return "permissions"
    if any(token in lowered for token in ("model", "budget", "fallback", "usage")):
        return "api"
    if any(token in lowered for token in ("subagent", "delegate", "team", "peer")):
        return "agents"
    if any(token in lowered for token in ("tool", "step", "process", "checkpoint", "review")):
        return "tools"
    if any(token in lowered for token in ("config", "setting", "plugin", "instruction", "startup")):
        return "startup"
    return "session"


def _status_category(status: str) -> str:
    return "api" if status == "thinking" else "tools"


__all__ = [
    "DebugFilter",
    "DebugOptions",
    "DebugRuntime",
    "combine_agent_loggers",
    "combine_event_observers",
    "normalize_debug_arguments",
    "parse_debug_filter",
    "resolve_debug_options",
]
