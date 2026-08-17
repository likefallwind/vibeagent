from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import uuid
from typing import Mapping, Sequence

from .tool_memory_exec import MAX_ENVIRONMENT_FILE_BYTES


TOOL_MEMORY_LIMIT_ENV = "CLAUDE_CODE_TOOL_MEMORY_LIMIT"
_LIMIT_PATTERN = re.compile(r"^(?P<amount>[1-9][0-9]*)(?P<unit>[kmgtpe]?i?b?)?$", re.IGNORECASE)
_UNIT_PATTERN = re.compile(r"^vibeagent-tool-[0-9a-f]{32}\.service$")
_UNIT_MULTIPLIERS = {
    "": 1,
    "b": 1,
    "k": 1024,
    "ki": 1024,
    "kb": 1024,
    "kib": 1024,
    "m": 1024**2,
    "mi": 1024**2,
    "mb": 1024**2,
    "mib": 1024**2,
    "g": 1024**3,
    "gi": 1024**3,
    "gb": 1024**3,
    "gib": 1024**3,
    "t": 1024**4,
    "ti": 1024**4,
    "tb": 1024**4,
    "tib": 1024**4,
    "p": 1024**5,
    "pi": 1024**5,
    "pb": 1024**5,
    "pib": 1024**5,
    "e": 1024**6,
    "ei": 1024**6,
    "eb": 1024**6,
    "eib": 1024**6,
}
MAX_TOOL_MEMORY_LIMIT_BYTES = 1024**5


class ToolMemoryLimitError(ValueError):
    pass


@dataclass(frozen=True)
class ToolMemoryLaunch:
    argv: tuple[str, ...]
    unit: str
    limit_bytes: int
    environment_path: Path
    systemctl: str


def parse_tool_memory_limit(environment: Mapping[str, str]) -> int | None:
    raw = environment.get(TOOL_MEMORY_LIMIT_ENV)
    if raw is None:
        return None
    value = raw.strip()
    match = _LIMIT_PATTERN.fullmatch(value)
    if match is None:
        raise ToolMemoryLimitError(
            f"{TOOL_MEMORY_LIMIT_ENV} must be a positive byte count or use a K, M, G, T, or P suffix."
        )
    unit = match.group("unit").lower()
    limit = int(match.group("amount")) * _UNIT_MULTIPLIERS[unit]
    if limit > MAX_TOOL_MEMORY_LIMIT_BYTES:
        raise ToolMemoryLimitError(
            f"{TOOL_MEMORY_LIMIT_ENV} must not exceed {format_memory_bytes(MAX_TOOL_MEMORY_LIMIT_BYTES)}."
        )
    return limit


def prepare_tool_memory_launch(
    argv: Sequence[str],
    cwd: Path,
    environment: Mapping[str, str],
) -> ToolMemoryLaunch | None:
    limit = parse_tool_memory_limit(environment)
    if limit is None:
        return None
    return prepare_memory_launch(
        argv,
        cwd,
        environment,
        limit_bytes=limit,
        requirement=TOOL_MEMORY_LIMIT_ENV,
    )


def prepare_memory_launch(
    argv: Sequence[str],
    cwd: Path,
    environment: Mapping[str, str],
    *,
    limit_bytes: int,
    requirement: str,
) -> ToolMemoryLaunch:
    if limit_bytes <= 0 or limit_bytes > MAX_TOOL_MEMORY_LIMIT_BYTES:
        raise ToolMemoryLimitError(
            f"{requirement} must be between 1 byte and "
            f"{format_memory_bytes(MAX_TOOL_MEMORY_LIMIT_BYTES)}."
        )
    if not sys.platform.startswith("linux"):
        raise ToolMemoryLimitError(
            f"{requirement} requires Linux or WSL with a user systemd manager."
        )
    search_path = environment.get("PATH")
    systemd_run = shutil.which("systemd-run", path=search_path)
    systemctl = shutil.which("systemctl", path=search_path)
    if systemd_run is None or systemctl is None:
        raise ToolMemoryLimitError(
            f"{requirement} requires systemd-run and systemctl on PATH."
        )
    environment_path = _write_private_environment(environment)
    unit = f"vibeagent-tool-{uuid.uuid4().hex}.service"
    command = (
        systemd_run,
        "--user",
        "--wait",
        "--pipe",
        "--quiet",
        f"--unit={unit}",
        f"--working-directory={cwd.resolve()}",
        "--service-type=exec",
        f"--property=MemoryMax={limit_bytes}",
        "--property=MemorySwapMax=0",
        "--property=OOMPolicy=kill",
        "--property=KillMode=control-group",
        "--",
        sys.executable,
        "-m",
        "vibeagent.tool_memory_exec",
        environment_path.as_posix(),
        "--",
        *tuple(argv),
    )
    return ToolMemoryLaunch(
        argv=command,
        unit=unit,
        limit_bytes=limit_bytes,
        environment_path=environment_path,
        systemctl=systemctl,
    )


def cleanup_tool_memory_launch(launch: ToolMemoryLaunch | None) -> None:
    if launch is not None:
        launch.environment_path.unlink(missing_ok=True)


def format_memory_bytes(value: int) -> str:
    for suffix, divisor in (("PiB", 1024**5), ("TiB", 1024**4), ("GiB", 1024**3), ("MiB", 1024**2), ("KiB", 1024)):
        if value >= divisor and value % divisor == 0:
            return f"{value // divisor} {suffix}"
    return f"{value} bytes"


def valid_tool_memory_unit(unit: str) -> bool:
    return bool(_UNIT_PATTERN.fullmatch(unit))


def _write_private_environment(environment: Mapping[str, str]) -> Path:
    payload = json.dumps(dict(environment), ensure_ascii=False)
    if len(payload.encode("utf-8")) > MAX_ENVIRONMENT_FILE_BYTES:
        raise ToolMemoryLimitError(
            f"Tool command environment exceeds {MAX_ENVIRONMENT_FILE_BYTES} bytes."
        )
    descriptor, raw_path = tempfile.mkstemp(prefix="vibeagent-tool-env-", suffix=".json")
    path = Path(raw_path)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        path.unlink(missing_ok=True)
        raise
    return path


__all__ = [
    "MAX_TOOL_MEMORY_LIMIT_BYTES",
    "TOOL_MEMORY_LIMIT_ENV",
    "ToolMemoryLaunch",
    "ToolMemoryLimitError",
    "cleanup_tool_memory_launch",
    "format_memory_bytes",
    "parse_tool_memory_limit",
    "prepare_memory_launch",
    "prepare_tool_memory_launch",
    "valid_tool_memory_unit",
]
