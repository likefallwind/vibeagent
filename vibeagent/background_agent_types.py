from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


BACKGROUND_AGENT_SCHEMA_VERSION = 2
BACKGROUND_AGENT_ID_PATTERN = re.compile(r"^[0-9a-f]{12}$")
DEFAULT_BACKGROUND_AGENT_LOG_CHARS = 20_000
MAX_BACKGROUND_AGENT_LOG_CHARS = 100_000
ACTIVE_BACKGROUND_AGENT_STATUSES = frozenset(
    {"running", "needs-input", "approval-error", "input-error"}
)


@dataclass(frozen=True)
class BackgroundAgentRecord:
    id: str
    project_root: Path
    invocation_root: Path
    pid: int
    start_ticks: int | None
    started_at: str
    task_summary: str
    session_name: str | None
    stdout_path: Path
    stderr_path: Path
    exit_code_path: Path
    stopped_path: Path
    memory_unit: str | None = None
    memory_limit_bytes: int | None = None


@dataclass(frozen=True)
class BackgroundAgentView:
    record: BackgroundAgentRecord
    status: str
    exit_code: int | None


@dataclass(frozen=True)
class BackgroundAgentBatchRespawn:
    eligible_count: int
    respawned: tuple[BackgroundAgentView, ...]
    failures: tuple[tuple[str, str], ...]


__all__ = [
    "ACTIVE_BACKGROUND_AGENT_STATUSES",
    "BACKGROUND_AGENT_ID_PATTERN",
    "BACKGROUND_AGENT_SCHEMA_VERSION",
    "DEFAULT_BACKGROUND_AGENT_LOG_CHARS",
    "MAX_BACKGROUND_AGENT_LOG_CHARS",
    "BackgroundAgentRecord",
    "BackgroundAgentBatchRespawn",
    "BackgroundAgentView",
]
