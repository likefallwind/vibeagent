from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import stat
from threading import RLock
import time
from uuid import UUID, uuid4

from .session_id import is_valid_session_id
from .session_store import list_sessions
from .session_utils import events_path, session_dir
from .user_paths import user_home


SESSION_INDEX_VERSION = 1
MAX_SESSION_INDEX_RECORD_BYTES = 8_192
MAX_SESSION_INDEX_BACKFILL = 10_000
_INDEX_LOCK = RLock()


def register_machine_session(project_root: Path, run_id: str) -> Path:
    root = project_root.resolve(strict=True)
    _require_indexable_session(root, run_id)
    index_root = _initialize_index_root()
    target = index_root / _record_name(root, run_id)
    payload = {
        "version": SESSION_INDEX_VERSION,
        "runId": run_id,
        "projectRoot": str(root),
        "updatedAt": time.time(),
    }
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    if len(encoded) > MAX_SESSION_INDEX_RECORD_BYTES:
        raise ValueError("Machine session index record is too large.")
    with _INDEX_LOCK:
        if target.exists():
            try:
                indexed_run_id, indexed_root = _read_index_record(target, index_root)
                if indexed_run_id == run_id and indexed_root == root:
                    return target
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
                pass
        temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_bytes(encoded)
            temporary.chmod(0o600)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return target


def try_register_machine_session(project_root: Path, run_id: str) -> str | None:
    try:
        register_machine_session(project_root, run_id)
    except (OSError, UnicodeError, ValueError) as error:
        return str(error)
    return None


def backfill_project_session_index(project_root: Path) -> tuple[int, int]:
    root = project_root.resolve()
    registered = 0
    failed = 0
    for session in list_sessions(root, limit=MAX_SESSION_INDEX_BACKFILL):
        if try_register_machine_session(root, session.run_id) is None:
            registered += 1
        else:
            failed += 1
    return registered, failed


def resolve_machine_session_root(current_root: Path, run_id: str) -> Path | None:
    root = current_root.resolve()
    if _session_is_available(root, run_id):
        try_register_machine_session(root, run_id)
        return root
    if not is_machine_searchable_session_id(run_id):
        return None
    index_root = _existing_index_root()
    if index_root is None:
        return None
    matches: set[Path] = set()
    for record_path in sorted(index_root.glob(f"{_run_digest(run_id)}-*.json")):
        try:
            indexed_run_id, indexed_root = _read_index_record(record_path, index_root)
            if indexed_run_id == run_id and _session_is_available(indexed_root, run_id):
                matches.add(indexed_root)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            continue
    if len(matches) > 1:
        raise ValueError(f"Session ID is ambiguous across projects: {run_id}")
    return next(iter(matches), None)


def is_machine_searchable_session_id(value: object) -> bool:
    if not isinstance(value, str) or not is_valid_session_id(value):
        return False
    if _is_generated_session_id(value):
        return True
    try:
        return str(UUID(value)) == value
    except (ValueError, AttributeError):
        return False


def _initialize_index_root() -> Path:
    runtime = user_home() / ".vibeagent"
    _reject_symlink_components(runtime)
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    _validate_private_directory(runtime, "Machine runtime directory", require_private=False)
    try:
        runtime.chmod(0o700)
    except OSError:
        pass
    _validate_private_directory(runtime, "Machine runtime directory")
    target = runtime / "session-index"
    _reject_symlink_components(target)
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    _validate_private_directory(target, "Machine session index", require_private=False)
    try:
        target.chmod(0o700)
    except OSError:
        pass
    _validate_private_directory(target, "Machine session index")
    return target


def _existing_index_root() -> Path | None:
    target = user_home() / ".vibeagent" / "session-index"
    if not target.exists():
        return None
    _reject_symlink_components(target)
    _validate_private_directory(target, "Machine session index")
    return target


def _validate_private_directory(path: Path, label: str, *, require_private: bool = True) -> None:
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"{label} is not a regular directory: {path}")
    if hasattr(os, "getuid") and path.stat().st_uid != os.getuid():
        raise ValueError(f"{label} is not owned by the current user: {path}")
    if require_private and hasattr(os, "getuid") and stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError(f"{label} must not grant group or other permissions: {path}")


def _read_index_record(path: Path, index_root: Path) -> tuple[str, Path]:
    if path.parent != index_root or path.is_symlink() or not path.is_file():
        raise ValueError("Machine session index record is not a regular file.")
    file_stat = path.stat()
    if file_stat.st_size > MAX_SESSION_INDEX_RECORD_BYTES:
        raise ValueError("Machine session index record is too large.")
    if hasattr(os, "getuid") and file_stat.st_uid != os.getuid():
        raise ValueError("Machine session index record is not owned by the current user.")
    if hasattr(os, "getuid") and stat.S_IMODE(file_stat.st_mode) & 0o077:
        raise ValueError("Machine session index record must not grant group or other permissions.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != SESSION_INDEX_VERSION:
        raise ValueError("Machine session index record has an unsupported version.")
    run_id = payload.get("runId")
    project_root = payload.get("projectRoot")
    updated_at = payload.get("updatedAt")
    if not is_machine_searchable_session_id(run_id):
        raise ValueError("Machine session index record has an invalid session ID.")
    if (
        not isinstance(project_root, str)
        or not project_root
        or len(project_root) > 4_096
        or any(ord(character) < 32 or ord(character) == 127 for character in project_root)
    ):
        raise ValueError("Machine session index record has an invalid project root.")
    if (
        not isinstance(updated_at, (int, float))
        or isinstance(updated_at, bool)
        or not math.isfinite(updated_at)
        or updated_at < 0
    ):
        raise ValueError("Machine session index record has an invalid timestamp.")
    root = Path(project_root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir() or root.resolve() != root:
        raise ValueError("Machine session index project root is unavailable or unsafe.")
    if path.name != _record_name(root, run_id):
        raise ValueError("Machine session index record identity does not match its filename.")
    return run_id, root


def _require_indexable_session(project_root: Path, run_id: str) -> None:
    if not is_machine_searchable_session_id(run_id):
        raise ValueError(f"Session ID is not eligible for machine-wide lookup: {run_id}")
    if not _session_is_available(project_root, run_id):
        raise ValueError(f"Session is unavailable for machine-wide lookup: {run_id}")


def _session_is_available(project_root: Path, run_id: str) -> bool:
    if not is_valid_session_id(run_id):
        return False
    try:
        directory = session_dir(project_root, run_id)
        events = events_path(project_root, run_id)
        return directory.is_dir() and not directory.is_symlink() and events.is_file() and events.stat().st_size > 0
    except (OSError, ValueError):
        return False


def _record_name(project_root: Path, run_id: str) -> str:
    root_digest = hashlib.sha256(os.fsencode(project_root)).hexdigest()[:32]
    return f"{_run_digest(run_id)}-{root_digest}.json"


def _run_digest(run_id: str) -> str:
    return hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:32]


def _is_generated_session_id(value: str) -> bool:
    if len(value) != 33 or value[4] != "-" or value[7] != "-" or value[10] != "T":
        return False
    date, rest = value[:10], value[11:]
    if rest[2:3] != "-" or rest[5:6] != "-" or rest[8:9] != "-" or rest[12:14] != "Z-":
        return False
    digits = date.replace("-", "") + rest[:2] + rest[3:5] + rest[6:8] + rest[9:12]
    suffix = rest[14:]
    return digits.isascii() and digits.isdigit() and len(suffix) == 8 and all(
        character in "0123456789abcdef" for character in suffix
    )


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ValueError(f"Machine session index path must not contain a symbolic link: {current}")


__all__ = [
    "backfill_project_session_index",
    "is_machine_searchable_session_id",
    "register_machine_session",
    "resolve_machine_session_root",
    "try_register_machine_session",
]
