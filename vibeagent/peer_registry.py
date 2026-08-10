from __future__ import annotations

import json
import math
import os
from pathlib import Path
import tempfile
from uuid import uuid4

from .peer_types import PeerMessagingError, PeerSession


PEER_REGISTRY_VERSION = 1
MAX_REGISTRY_BYTES = 16_384
PEER_ID_LENGTH = 12


def peer_runtime_root() -> Path:
    configured = os.environ.get("VIBEAGENT_PEER_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().absolute()
    user_id = os.getuid() if hasattr(os, "getuid") else os.getpid()
    return Path(tempfile.gettempdir()).absolute() / f"vibeagent-{user_id}" / "peers"


def initialize_peer_root(root: Path | None = None) -> Path:
    target = (root or peer_runtime_root()).absolute()
    _reject_symlink_components(target)
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    if target.is_symlink() or not target.is_dir():
        raise PeerMessagingError(f"Peer runtime root is not a regular directory: {target}")
    if hasattr(os, "getuid") and target.stat().st_uid != os.getuid():
        raise PeerMessagingError(f"Peer runtime root is not owned by the current user: {target}")
    try:
        target.chmod(0o700)
    except OSError:
        pass
    return target


def new_peer_id() -> str:
    return uuid4().hex[:PEER_ID_LENGTH]


def peer_socket_path(root: Path, peer_id: str) -> Path:
    return root / f"{peer_id}.sock"


def peer_registration_path(root: Path, peer_id: str) -> Path:
    return root / f"{peer_id}.json"


def write_peer_registration(root: Path, peer: PeerSession) -> Path:
    target_root = initialize_peer_root(root)
    path = peer_registration_path(target_root, peer.id)
    _validate_runtime_path(target_root, path)
    encoded = json.dumps(
        {
            "version": PEER_REGISTRY_VERSION,
            "id": peer.id,
            "name": peer.name,
            "projectRoot": peer.project_root,
            "runId": peer.run_id,
            "socketPath": peer.socket_path,
            "pid": peer.pid,
            "bypassesPermissions": peer.bypasses_permissions,
            "updatedAt": peer.updated_at,
        },
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"
    if len(encoded.encode("utf-8")) > MAX_REGISTRY_BYTES:
        raise PeerMessagingError("Peer registration is too large.")
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(encoded, encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def list_peer_sessions(*, exclude_pid: int | None = None, root: Path | None = None) -> tuple[list[PeerSession], int]:
    target_root = initialize_peer_root(root)
    peers: list[PeerSession] = []
    invalid = 0
    for path in sorted(target_root.glob("*.json")):
        try:
            peer = read_peer_registration(path, target_root)
            if not _peer_is_live(peer):
                _remove_stale_registration(path, peer, target_root)
                continue
            if exclude_pid is not None and peer.pid == exclude_pid:
                continue
            peers.append(peer)
        except (OSError, UnicodeError, json.JSONDecodeError, PeerMessagingError):
            invalid += 1
    peers.sort(key=lambda peer: (-peer.updated_at, peer.name, peer.id))
    return peers, invalid


def read_peer_registration(path: Path, root: Path | None = None) -> PeerSession:
    target_root = initialize_peer_root(root)
    _validate_runtime_path(target_root, path)
    if not path.is_file() or path.stat().st_size > MAX_REGISTRY_BYTES:
        raise PeerMessagingError(f"Invalid peer registration file: {path}")
    return _parse_peer(json.loads(path.read_text(encoding="utf-8")), target_root)


def find_peer_session(target: str, *, root: Path | None = None) -> PeerSession | None:
    peers, _ = list_peer_sessions(root=root)
    exact_id = [peer for peer in peers if peer.id == target]
    if exact_id:
        return exact_id[0]
    by_name = [peer for peer in peers if peer.name == target]
    if len(by_name) == 1:
        return by_name[0]
    if len(by_name) > 1:
        ids = ", ".join(peer.id for peer in by_name)
        raise PeerMessagingError(f"Peer name is ambiguous; use one of these IDs: {ids}")
    return None


def current_process_peer(*, root: Path | None = None) -> PeerSession | None:
    peers, _ = list_peer_sessions(root=root)
    own = [peer for peer in peers if peer.pid == os.getpid()]
    return max(own, key=lambda peer: peer.updated_at) if own else None


def remove_peer_registration(root: Path, peer_id: str) -> None:
    target_root = initialize_peer_root(root)
    for path in (peer_registration_path(target_root, peer_id), peer_socket_path(target_root, peer_id)):
        _validate_runtime_path(target_root, path)
        path.unlink(missing_ok=True)


def _parse_peer(payload: object, root: Path) -> PeerSession:
    if not isinstance(payload, dict) or payload.get("version") != PEER_REGISTRY_VERSION:
        raise PeerMessagingError("Unsupported or malformed peer registration.")
    peer_id = payload.get("id")
    name = payload.get("name")
    project_root = payload.get("projectRoot")
    run_id = payload.get("runId")
    socket_path = payload.get("socketPath")
    pid = payload.get("pid")
    bypasses = payload.get("bypassesPermissions")
    updated_at = payload.get("updatedAt")
    if not isinstance(peer_id, str) or len(peer_id) != PEER_ID_LENGTH or any(char not in "0123456789abcdef" for char in peer_id):
        raise PeerMessagingError("Peer registration has an invalid ID.")
    if not isinstance(name, str) or not name or len(name) > 64:
        raise PeerMessagingError("Peer registration has an invalid name.")
    if not isinstance(project_root, str) or not project_root or len(project_root) > 4_096:
        raise PeerMessagingError("Peer registration has an invalid project root.")
    if run_id is not None and (not isinstance(run_id, str) or len(run_id) > 200):
        raise PeerMessagingError("Peer registration has an invalid run ID.")
    if not isinstance(socket_path, str):
        raise PeerMessagingError("Peer registration has an invalid socket path.")
    socket = Path(socket_path)
    _validate_runtime_path(root, socket)
    if socket != peer_socket_path(root, peer_id):
        raise PeerMessagingError("Peer registration socket does not match its ID.")
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        raise PeerMessagingError("Peer registration has an invalid PID.")
    if not isinstance(bypasses, bool):
        raise PeerMessagingError("Peer registration has an invalid permission class.")
    if not isinstance(updated_at, (int, float)) or isinstance(updated_at, bool) or not math.isfinite(updated_at) or updated_at < 0:
        raise PeerMessagingError("Peer registration has an invalid timestamp.")
    return PeerSession(peer_id, name, project_root, run_id, socket_path, pid, bypasses, float(updated_at))


def _peer_is_live(peer: PeerSession) -> bool:
    if not Path(peer.socket_path).exists():
        return False
    try:
        os.kill(peer.pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return False
    return True


def _remove_stale_registration(path: Path, peer: PeerSession, root: Path) -> None:
    path.unlink(missing_ok=True)
    socket = Path(peer.socket_path)
    _validate_runtime_path(root, socket)
    socket.unlink(missing_ok=True)


def _validate_runtime_path(root: Path, path: Path) -> None:
    if path.parent != root:
        raise PeerMessagingError(f"Peer runtime path escapes its root: {path}")
    if path.is_symlink():
        raise PeerMessagingError(f"Peer runtime path must not be a symlink: {path}")


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise PeerMessagingError(f"Peer runtime path must not contain a symlink: {current}")


__all__ = [
    "current_process_peer",
    "find_peer_session",
    "initialize_peer_root",
    "list_peer_sessions",
    "new_peer_id",
    "peer_runtime_root",
    "peer_socket_path",
    "remove_peer_registration",
    "write_peer_registration",
]
