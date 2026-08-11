from __future__ import annotations

import os
from pathlib import Path
import shlex
from uuid import uuid4

from .command_safety import get_blocked_command_reason
from .session_id import is_valid_session_id
from .workspace_core import RunWorkspace
from .workspace_metadata_files import read_regular_file_bytes


SESSION_ENV_FILE = "environment.sh"
CLAUDE_ENV_FILE = "CLAUDE_ENV_FILE"
MAX_SESSION_ENV_BYTES = 128_000


def ensure_session_environment_file(workspace: RunWorkspace) -> Path:
    path = workspace.session_dir / SESSION_ENV_FILE
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Session environment path is not a regular file: {path}")
    if not path.exists():
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
    read_regular_file_bytes(
        path,
        max_bytes=MAX_SESSION_ENV_BYTES,
        label="Session environment file",
    )
    if os.name != "nt":
        os.chmod(path, 0o600, follow_symlinks=False)
    return path


def wrap_bash_command_with_session_environment(
    workspace: RunWorkspace,
    command: str,
    *,
    enabled: bool,
) -> str:
    if not enabled:
        return command
    try:
        path = ensure_session_environment_file(workspace)
        content = read_regular_file_bytes(
            path,
            max_bytes=MAX_SESSION_ENV_BYTES,
            label="Session environment file",
        ).decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"Session environment could not be loaded: {error}") from error
    blocked = get_blocked_command_reason(content)
    if blocked is not None:
        raise ValueError(f"Session environment blocked: {blocked}")
    quoted_path = shlex.quote(path.as_posix())
    return (
        f". {quoted_path}\n"
        "__vibeagent_env_status=$?\n"
        "if [ \"$__vibeagent_env_status\" -ne 0 ]; then\n"
        "  exit \"$__vibeagent_env_status\"\n"
        "fi\n"
        f"{command}"
    )


def lifecycle_hook_environment(
    workspace: RunWorkspace,
    event: str,
) -> dict[str, str]:
    if event not in {"SessionStart", "CwdChanged", "FileChanged"}:
        return {}
    return {CLAUDE_ENV_FILE: str(ensure_session_environment_file(workspace))}


def inherit_session_environment(
    workspace: RunWorkspace,
    source_run_id: str | None,
) -> tuple[bool, str | None]:
    if source_run_id is None or source_run_id == workspace.run_id:
        return False, None
    if not is_valid_session_id(source_run_id):
        return False, "Source session id is invalid."
    target = workspace.session_dir / SESSION_ENV_FILE
    if target.exists() or target.is_symlink():
        return False, None
    source = (
        workspace.root
        / ".vibeagent"
        / "sessions"
        / source_run_id
        / SESSION_ENV_FILE
    )
    try:
        if source.parent.is_symlink():
            return False, "Source session environment directory is a symbolic link."
        if source.is_symlink() or not source.is_file():
            return False, None
        content = read_regular_file_bytes(
            source,
            max_bytes=MAX_SESSION_ENV_BYTES,
            label="Stored session environment",
        )
        _write_environment_file(target, content)
        return True, None
    except (OSError, ValueError) as error:
        return False, str(error)


def _write_environment_file(path: Path, content: bytes) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Session environment path is not a regular file: {path}")
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "CLAUDE_ENV_FILE",
    "MAX_SESSION_ENV_BYTES",
    "SESSION_ENV_FILE",
    "ensure_session_environment_file",
    "inherit_session_environment",
    "lifecycle_hook_environment",
    "wrap_bash_command_with_session_environment",
]
