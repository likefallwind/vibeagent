from __future__ import annotations

from collections import deque
import json
import os
from pathlib import Path
import socket
import sys
from threading import Event, Lock, Thread
import time
from typing import Any

from .peer_registry import (
    initialize_peer_root,
    new_peer_id,
    peer_runtime_root,
    peer_socket_path,
    remove_peer_registration,
    write_peer_registration,
)
from .peer_protocol import (
    PEER_PROTOCOL_VERSION,
    parse_peer_message,
    read_bounded_request,
    validate_registered_sender,
)
from .peer_types import PeerInboundMode, PeerMessage, PeerMessagingError, PeerSession
from .types import ApprovalPolicy
from .workspace_core import RunWorkspace


MAX_DELIVERED_MESSAGES = 50
MAX_HELD_MESSAGES = 100
DUPLICATE_WINDOW_SECONDS = 5.0
_VALID_INBOUND_MODES = frozenset({"accept", "hold", "refuse"})


class PeerSessionRuntime:
    def __init__(
        self,
        project_root: str | Path,
        approval_policy: ApprovalPolicy,
        *,
        name: str | None = None,
        root: Path | None = None,
    ) -> None:
        self.root = initialize_peer_root(root or peer_runtime_root())
        self.id = new_peer_id()
        self.project_root = str(Path(project_root).resolve())
        self.name = _normalize_peer_name(name or os.environ.get("VIBEAGENT_SESSION_NAME") or _default_name(Path(project_root), self.id))
        self.run_id: str | None = None
        self.approval_policy = approval_policy
        self._explicit_inbound = _read_inbound_mode(Path(project_root))
        self._socket_path = peer_socket_path(self.root, self.id)
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._stop = Event()
        self._lock = Lock()
        self._delivered: deque[PeerMessage] = deque(maxlen=MAX_DELIVERED_MESSAGES)
        self._held: deque[PeerMessage] = deque(maxlen=MAX_HELD_MESSAGES)
        self._recent: dict[tuple[str, str], float] = {}
        self._thread = Thread(target=self._serve, name=f"vibeagent-peer-{self.id}", daemon=True)
        try:
            self._socket.bind(str(self._socket_path))
            self._socket_path.chmod(0o600)
            self._socket.listen(16)
            self._socket.settimeout(0.2)
            self._thread.start()
            self._write_registration()
        except Exception:
            self._stop.set()
            self._socket.close()
            if self._thread.is_alive():
                self._thread.join(timeout=1)
            remove_peer_registration(self.root, self.id)
            raise

    @property
    def socket_path(self) -> Path:
        return self._socket_path

    def update_workspace(self, workspace: RunWorkspace, approval_policy: ApprovalPolicy) -> None:
        self.project_root = str(workspace.root)
        self.run_id = workspace.run_id
        self.approval_policy = approval_policy
        self._explicit_inbound = _read_inbound_mode(workspace.root, trusted=workspace.project_config_trusted)
        self._release_held_if_allowed()
        self._write_registration()

    def update_approval_policy(self, approval_policy: ApprovalPolicy) -> None:
        self.approval_policy = approval_policy
        self._release_held_if_allowed()
        self._write_registration()

    def collect_messages(self) -> list[PeerMessage]:
        with self._lock:
            messages = list(self._delivered)
            self._delivered.clear()
        return messages

    def held_messages(self) -> list[PeerMessage]:
        with self._lock:
            return list(self._held)

    def decide_held(self, *, accept: bool, sender_id: str | None = None) -> tuple[int, int]:
        decided = 0
        retained: deque[PeerMessage] = deque(maxlen=MAX_HELD_MESSAGES)
        with self._lock:
            while self._held:
                message = self._held.popleft()
                if sender_id is not None and message.sender_id != sender_id:
                    retained.append(message)
                    continue
                decided += 1
                if accept:
                    self._delivered.append(message)
            self._held = retained
            remaining = len(self._held)
        return decided, remaining

    def close(self) -> None:
        if self._stop.is_set():
            return
        self._stop.set()
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as wake:
                wake.settimeout(0.1)
                wake.connect(str(self._socket_path))
        except OSError:
            pass
        try:
            self._socket.close()
        except OSError:
            pass
        self._thread.join(timeout=1)
        remove_peer_registration(self.root, self.id)

    def __enter__(self) -> PeerSessionRuntime:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                connection, _ = self._socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with connection:
                response = self._handle_connection(connection)
                try:
                    connection.sendall((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))
                except OSError:
                    pass

    def _handle_connection(self, connection: socket.socket) -> dict[str, object]:
        try:
            raw = read_bounded_request(connection)
            payload = json.loads(raw.decode("utf-8"))
            message = parse_peer_message(payload)
            validate_registered_sender(message, connection=connection, root=self.root)
            status = self._accept_message(message)
            return {"version": PEER_PROTOCOL_VERSION, "status": status}
        except (OSError, UnicodeError, json.JSONDecodeError, PeerMessagingError) as error:
            return {"version": PEER_PROTOCOL_VERSION, "status": "error", "message": str(error)[:500]}

    def _accept_message(self, message: PeerMessage) -> str:
        now = time.time()
        key = (message.sender_id, message.message)
        with self._lock:
            cutoff = now - DUPLICATE_WINDOW_SECONDS
            self._recent = {item: seen for item, seen in self._recent.items() if seen >= cutoff}
            if key in self._recent:
                return "refused"
            self._recent[key] = now
            mode = self._inbound_mode(message.sender_bypasses_permissions)
            if mode == "accept":
                self._delivered.append(message)
                return "delivered"
            if mode == "hold":
                self._held.append(message)
                return "held"
            return "refused"

    def _inbound_mode(self, sender_bypasses_permissions: bool) -> PeerInboundMode:
        if self._explicit_inbound is not None:
            return self._explicit_inbound
        receiver_bypasses = _bypasses_permissions(self.approval_policy)
        return "accept" if receiver_bypasses == sender_bypasses_permissions else "hold"

    def _release_held_if_allowed(self) -> None:
        with self._lock:
            retained: deque[PeerMessage] = deque(maxlen=MAX_HELD_MESSAGES)
            while self._held:
                message = self._held.popleft()
                mode = self._inbound_mode(message.sender_bypasses_permissions)
                if mode == "accept":
                    self._delivered.append(message)
                elif mode == "hold":
                    retained.append(message)
            self._held = retained

    def _write_registration(self) -> None:
        write_peer_registration(
            self.root,
            PeerSession(
                id=self.id,
                name=self.name,
                project_root=self.project_root,
                run_id=self.run_id,
                socket_path=str(self._socket_path),
                pid=os.getpid(),
                bypasses_permissions=_bypasses_permissions(self.approval_policy),
                updated_at=time.time(),
            ),
        )


def _read_inbound_mode(project_root: Path, *, trusted: bool = False) -> PeerInboundMode | None:
    configured = os.environ.get("VIBEAGENT_CROSS_SESSION_INBOUND", "").strip().lower()
    if configured:
        if configured not in _VALID_INBOUND_MODES:
            raise PeerMessagingError("VIBEAGENT_CROSS_SESSION_INBOUND must be accept, hold, or refuse.")
        return configured  # type: ignore[return-value]
    for relative, may_accept in ((".claude/settings.local.json", True), (".claude/settings.json", trusted)):
        path = project_root / relative
        if (project_root / ".claude").is_symlink() or not path.is_file() or path.is_symlink():
            continue
        try:
            if path.stat().st_size > 1_000_000:
                continue
            payload: Any = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        value = payload.get("crossSessionInbound") if isinstance(payload, dict) else None
        if value == "refuse" or (may_accept and value in {"accept", "hold"}):
            return value
    return None


def _bypasses_permissions(policy: ApprovalPolicy) -> bool:
    return policy in {"allow", "deny", "plan"}


def _default_name(project_root: Path, peer_id: str) -> str:
    base = project_root.resolve().name or "session"
    return f"{base}-{peer_id[:4]}"


def _normalize_peer_name(value: str) -> str:
    normalized = "".join(char if char.isalnum() or char in "._-" else "-" for char in value.strip())
    normalized = normalized.strip("-.")[:64]
    if not normalized:
        raise PeerMessagingError("Peer session name must contain a letter or number.")
    return normalized


def create_peer_runtime(
    project_root: str | Path,
    approval_policy: ApprovalPolicy,
    *,
    name: str | None = None,
) -> PeerSessionRuntime | None:
    disabled = os.environ.get("VIBEAGENT_DISABLE_CROSS_SESSION", "").strip().lower()
    if disabled in {"1", "true", "yes", "on"} or sys.platform == "win32":
        return None
    try:
        return PeerSessionRuntime(project_root, approval_policy, name=name)
    except (OSError, PeerMessagingError):
        return None


__all__ = ["PeerSessionRuntime", "create_peer_runtime"]
