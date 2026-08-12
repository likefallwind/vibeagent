from __future__ import annotations

from dataclasses import dataclass
import hmac
import json
import os
from pathlib import Path
import stat
import tempfile
import time

from .ide_context import IDE_CONTEXT_FILE_ENV, IDE_CONTEXT_TOKEN_ENV, TOKEN_PATTERN


IDE_CONNECTION_VERSION = 1
MAX_IDE_CONNECTION_BYTES = 16 * 1024
MAX_IDE_CONNECTION_AGE_SECONDS = 120
MAX_IDE_CONNECTION_FILES = 1_000


@dataclass(frozen=True)
class IdeConnection:
    context_file: Path
    token: str
    workspace_root: Path

    @property
    def environment(self) -> dict[str, str]:
        return {
            IDE_CONTEXT_FILE_ENV: str(self.context_file),
            IDE_CONTEXT_TOKEN_ENV: self.token,
        }


def default_ide_registry_root() -> Path:
    suffix = str(os.getuid()) if hasattr(os, "getuid") else "user"
    return Path(tempfile.gettempdir()) / f"vibeagent-ide-connections-{suffix}"


def discover_ide_connection(
    project_root: Path,
    *,
    registry_root: Path | None = None,
    now: float | None = None,
) -> IdeConnection:
    root = project_root.resolve()
    registry = registry_root or default_ide_registry_root()
    if not registry.exists():
        raise ValueError("No VibeAgent IDE connection is available for this project.")
    _validate_private_directory(registry)
    current_time = time.time() if now is None else now
    matches: list[IdeConnection] = []
    connection_file_count = 0
    for path in registry.iterdir():
        if path.suffix != ".json":
            continue
        connection_file_count += 1
        if connection_file_count > MAX_IDE_CONNECTION_FILES:
            raise ValueError("IDE connection registry contains too many descriptors.")
        try:
            if current_time - path.stat(follow_symlinks=False).st_mtime > MAX_IDE_CONNECTION_AGE_SECONDS:
                continue
            connection = _read_connection(path)
            if connection.workspace_root != root:
                continue
            _validate_context_identity(connection)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            continue
        matches.append(connection)
        if len(matches) > 1:
            raise ValueError("Multiple VibeAgent IDE connections are available for this project; close extra IDE windows.")
    if not matches:
        raise ValueError("No VibeAgent IDE connection is available for this project.")
    return matches[0]


def _read_connection(path: Path) -> IdeConnection:
    payload = json.loads(_read_private_file(path, MAX_IDE_CONNECTION_BYTES).decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != IDE_CONNECTION_VERSION:
        raise ValueError("unsupported IDE connection version")
    workspace_root = payload.get("workspaceRoot")
    context_file = payload.get("contextFile")
    token = payload.get("token")
    if not isinstance(workspace_root, str) or not Path(workspace_root).is_absolute():
        raise ValueError("IDE connection workspace is invalid")
    if not isinstance(context_file, str) or not Path(context_file).is_absolute():
        raise ValueError("IDE connection context path is invalid")
    if not isinstance(token, str) or TOKEN_PATTERN.fullmatch(token) is None:
        raise ValueError("IDE connection token is invalid")
    return IdeConnection(Path(context_file), token, Path(workspace_root).resolve())


def _validate_context_identity(connection: IdeConnection) -> None:
    payload = json.loads(_read_private_file(connection.context_file, 64 * 1024).decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("unsupported IDE context version")
    token = payload.get("token")
    workspace_root = payload.get("workspaceRoot")
    if not isinstance(token, str) or not hmac.compare_digest(token, connection.token):
        raise ValueError("IDE context token does not match")
    if not isinstance(workspace_root, str) or Path(workspace_root).resolve() != connection.workspace_root:
        raise ValueError("IDE context workspace does not match")


def _validate_private_directory(path: Path) -> None:
    metadata = path.lstat()
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("IDE connection registry must be a directory")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise ValueError("IDE connection registry must be owned by the current user")
    if os.name != "nt" and stat.S_IMODE(metadata.st_mode) & 0o077:
        raise ValueError("IDE connection registry must not grant group or other access")


def _read_private_file(path: Path, maximum_bytes: int) -> bytes:
    if not path.is_absolute():
        raise ValueError("IDE connection path must be absolute")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("IDE connection path must be a regular file")
        if metadata.st_size <= 0 or metadata.st_size > maximum_bytes:
            raise ValueError("IDE connection file size is invalid")
        if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
            raise ValueError("IDE connection file must be owned by the current user")
        if os.name != "nt" and stat.S_IMODE(metadata.st_mode) & 0o077:
            raise ValueError("IDE connection file must not grant group or other access")
        chunks: list[bytes] = []
        remaining = metadata.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 16_384))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        value = b"".join(chunks)
        if len(value) != metadata.st_size:
            raise ValueError("IDE connection file changed while it was read")
        return value
    finally:
        os.close(descriptor)


__all__ = [
    "IdeConnection",
    "default_ide_registry_root",
    "discover_ide_connection",
]
