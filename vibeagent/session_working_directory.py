from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import shlex
from uuid import uuid4

from .agent_runtime_utils import append_session_event
from .plugin_environment import plugin_command_environment
from .session_id import is_valid_session_id
from .types import CommandResult
from .workspace_core import RunWorkspace
from .workspace_resolve import resolve_command_cwd


SESSION_CWD_FILE = "cwd.json"
MAINTAIN_PROJECT_CWD_ENV = "CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR"
MAX_STATE_BYTES = 4_096


@dataclass(frozen=True)
class ShellCwdContext:
    cwd: Path
    capture_path: Path | None


def prepare_shell_cwd(
    workspace: RunWorkspace,
    requested_cwd: str | None,
    *,
    maintain: bool,
    capture: bool = True,
) -> ShellCwdContext:
    enabled = maintain and workspace.maintain_shell_cwd and _persistence_enabled(workspace)
    if requested_cwd is not None:
        cwd = resolve_command_cwd(workspace, requested_cwd)
    elif enabled:
        cwd = read_session_cwd(workspace)
    else:
        cwd = resolve_command_cwd(workspace, None)
    capture_path = _new_capture_path(workspace) if enabled and capture else None
    return ShellCwdContext(cwd=cwd, capture_path=capture_path)


def prepare_action_shell_cwd(workspace: RunWorkspace, action: object) -> object:
    if (
        not bool(getattr(action, "maintain_cwd", False))
        or getattr(action, "cwd", None) is not None
    ):
        return action
    context = prepare_shell_cwd(
        workspace,
        None,
        maintain=True,
        capture=False,
    )
    return replace(action, cwd=str(context.cwd))


def wrap_posix_command_for_cwd_capture(command: str, capture_path: Path | None) -> str:
    if capture_path is None:
        return command
    quoted_path = shlex.quote(capture_path.as_posix())
    return (
        "__vibeagent_capture_cwd() {\n"
        "  __vibeagent_status=$?\n"
        f"  printf '%s\\n' \"$PWD\" > {quoted_path}\n"
        "  return \"$__vibeagent_status\"\n"
        "}\n"
        "trap __vibeagent_capture_cwd EXIT\n"
        f"{command}"
    )


def wrap_powershell_command_for_cwd_capture(command: str, capture_path: Path | None) -> str:
    if capture_path is None:
        return command
    escaped_path = str(capture_path).replace("'", "''")
    return (
        "try { & {\n"
        f"{command}\n"
        "} } finally { "
        f"[System.IO.File]::WriteAllText('{escaped_path}', (Get-Location).ProviderPath) }}"
    )


def finalize_shell_cwd(
    workspace: RunWorkspace,
    context: ShellCwdContext,
    result: CommandResult,
) -> CommandResult:
    capture_path = context.capture_path
    if capture_path is None:
        return result
    try:
        captured = _read_capture_path(capture_path)
    finally:
        capture_path.unlink(missing_ok=True)
    previous = context.cwd.resolve()
    final, reset = _validated_final_cwd(workspace, previous, captured)
    persistence_warning: str | None = None
    try:
        write_session_cwd(workspace, final)
    except (OSError, ValueError) as error:
        persistence_warning = f"Shell cwd persistence warning: {error}"
    stderr = result.stderr
    notices: list[str] = []
    if reset:
        notices.append(f"Shell cwd was reset to {final}.")
    if persistence_warning is not None:
        notices.append(persistence_warning)
    if notices:
        notice = "\n".join(notices)
        stderr = f"{stderr.rstrip()}\n{notice}\n" if stderr else f"{notice}\n"
    if final == previous and not reset:
        return replace(result, stderr=stderr) if notices else result
    append_session_event(
        workspace.session_dir,
        "cwd_changed",
        {
            "old_cwd": str(previous),
            "new_cwd": str(final),
            "reset": reset,
        },
    )
    return replace(
        result,
        stderr=stderr,
        previous_cwd=str(previous),
        final_cwd=str(final),
        cwd_reset=reset,
    )


def read_session_cwd(workspace: RunWorkspace) -> Path:
    path = workspace.session_dir / SESSION_CWD_FILE
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_STATE_BYTES:
            return workspace.root.resolve()
        payload = json.loads(path.read_text(encoding="utf-8"))
        value = payload.get("cwd") if isinstance(payload, dict) else None
        if not isinstance(value, str) or not value:
            return workspace.root.resolve()
        return resolve_command_cwd(workspace, value)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return workspace.root.resolve()


def write_session_cwd(workspace: RunWorkspace, cwd: Path) -> None:
    path = workspace.session_dir / SESSION_CWD_FILE
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Session cwd path is not a regular file: {path}")
    encoded = json.dumps({"cwd": str(cwd.resolve())}, separators=(",", ":"))
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def inherit_session_cwd(workspace: RunWorkspace, source_run_id: str | None) -> tuple[bool, str | None]:
    if source_run_id is None or source_run_id == workspace.run_id:
        return False, None
    if not is_valid_session_id(source_run_id):
        return False, "Source session id is invalid."
    target = workspace.session_dir / SESSION_CWD_FILE
    if target.exists() or target.is_symlink():
        return False, None
    source = workspace.root / ".vibeagent" / "sessions" / source_run_id / SESSION_CWD_FILE
    try:
        if source.parent.is_symlink():
            return False, "Source session cwd directory is a symbolic link."
        if source.is_symlink() or not source.is_file() or source.stat().st_size > MAX_STATE_BYTES:
            return False, None
        payload = json.loads(source.read_text(encoding="utf-8"))
        value = payload.get("cwd") if isinstance(payload, dict) else None
        if not isinstance(value, str):
            return False, "Stored session cwd is invalid."
        cwd = resolve_command_cwd(workspace, value)
        write_session_cwd(workspace, cwd)
        return True, None
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        return False, str(error)


def _new_capture_path(workspace: RunWorkspace) -> Path:
    path = workspace.session_dir / f".cwd-capture-{uuid4().hex}"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    return path


def _read_capture_path(path: Path) -> str | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_STATE_BYTES:
            return None
        value = path.read_text(encoding="utf-8").strip()
        return value or None
    except (OSError, UnicodeError):
        return None


def _validated_final_cwd(
    workspace: RunWorkspace,
    previous: Path,
    captured: str | None,
) -> tuple[Path, bool]:
    if captured is None:
        return previous, False
    try:
        return resolve_command_cwd(workspace, captured), False
    except ValueError:
        return workspace.root.resolve(), True


def _persistence_enabled(workspace: RunWorkspace) -> bool:
    try:
        value = plugin_command_environment(workspace).get(MAINTAIN_PROJECT_CWD_ENV, "")
    except (OSError, ValueError):
        return False
    return value.strip().lower() not in {"1", "true", "yes", "on"}


__all__ = [
    "MAINTAIN_PROJECT_CWD_ENV",
    "SESSION_CWD_FILE",
    "ShellCwdContext",
    "finalize_shell_cwd",
    "inherit_session_cwd",
    "prepare_action_shell_cwd",
    "prepare_shell_cwd",
    "read_session_cwd",
    "wrap_posix_command_for_cwd_capture",
    "wrap_powershell_command_for_cwd_capture",
    "write_session_cwd",
]
