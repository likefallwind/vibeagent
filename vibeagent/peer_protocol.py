from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import struct
import time

from .peer_registry import current_process_peer, find_peer_session
from .peer_types import PeerDelivery, PeerMessage, PeerMessagingError


PEER_PROTOCOL_VERSION = 1
MAX_PEER_REQUEST_BYTES = 16_384
MAX_PEER_MESSAGE_CHARS = 4_000


def send_peer_message(target: str, message: str, *, root: Path | None = None) -> PeerDelivery | None:
    peer = find_peer_session(target, root=root)
    if peer is None:
        return None
    sender = current_process_peer(root=root)
    if sender is None:
        raise PeerMessagingError("This process has no registered peer inbox.")
    if peer.id == sender.id:
        raise PeerMessagingError("A session cannot send a peer message to itself.")
    payload = {
        "version": PEER_PROTOCOL_VERSION,
        "sender": {
            "id": sender.id,
            "name": sender.name,
            "projectRoot": sender.project_root,
            "bypassesPermissions": sender.bypasses_permissions,
        },
        "message": message,
    }
    encoded = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    if len(encoded) > MAX_PEER_REQUEST_BYTES:
        raise PeerMessagingError("Peer message request is too large.")
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(2)
            connection.connect(peer.socket_path)
            connection.sendall(encoded)
            response = json.loads(read_bounded_request(connection).decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PeerMessagingError(f"Peer message delivery failed: {error}") from error
    status = response.get("status") if isinstance(response, dict) else None
    if status not in {"delivered", "held", "refused", "error"}:
        raise PeerMessagingError("Peer returned an invalid delivery response.")
    detail = response.get("message") if isinstance(response, dict) else None
    return PeerDelivery(status, peer.id, peer.name, str(detail or f"Message {status} by peer session {peer.name}."))


def read_bounded_request(connection: socket.socket) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while size <= MAX_PEER_REQUEST_BYTES:
        chunk = connection.recv(min(4_096, MAX_PEER_REQUEST_BYTES + 1 - size))
        if not chunk:
            break
        chunks.append(chunk)
        size += len(chunk)
        if b"\n" in chunk:
            break
    raw = b"".join(chunks).split(b"\n", 1)[0]
    if not raw or len(raw) > MAX_PEER_REQUEST_BYTES:
        raise PeerMessagingError("Peer request is empty or too large.")
    return raw


def parse_peer_message(payload: object) -> PeerMessage:
    if not isinstance(payload, dict) or payload.get("version") != PEER_PROTOCOL_VERSION:
        raise PeerMessagingError("Unsupported or malformed peer request.")
    sender = payload.get("sender")
    message = payload.get("message")
    if not isinstance(sender, dict):
        raise PeerMessagingError("Peer request has invalid sender metadata.")
    sender_id = sender.get("id")
    sender_name = sender.get("name")
    project_root = sender.get("projectRoot")
    bypasses = sender.get("bypassesPermissions")
    if not isinstance(sender_id, str) or not sender_id or len(sender_id) > 64:
        raise PeerMessagingError("Peer request has an invalid sender ID.")
    if not isinstance(sender_name, str) or not sender_name or len(sender_name) > 64:
        raise PeerMessagingError("Peer request has an invalid sender name.")
    if not isinstance(project_root, str) or not project_root or len(project_root) > 4_096:
        raise PeerMessagingError("Peer request has an invalid sender project root.")
    if not isinstance(bypasses, bool):
        raise PeerMessagingError("Peer request has an invalid permission class.")
    if not isinstance(message, str) or not message.strip() or len(message) > MAX_PEER_MESSAGE_CHARS:
        raise PeerMessagingError("Peer request has an invalid message.")
    return PeerMessage(sender_id, sender_name, project_root, bypasses, message.strip(), time.time())


def validate_registered_sender(
    message: PeerMessage,
    *,
    connection: socket.socket,
    root: Path | None = None,
) -> None:
    sender = find_peer_session(message.sender_id, root=root)
    if sender is None:
        raise PeerMessagingError("Peer sender is not registered.")
    if (
        sender.name != message.sender_name
        or sender.project_root != message.sender_project_root
        or sender.bypasses_permissions != message.sender_bypasses_permissions
    ):
        raise PeerMessagingError("Peer sender metadata does not match its registration.")
    if hasattr(socket, "SO_PEERCRED"):
        credentials = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        connecting_pid, connecting_uid, _ = struct.unpack("3i", credentials)
        if connecting_uid != os.getuid() or connecting_pid != sender.pid:
            raise PeerMessagingError("Peer sender process does not match its registration.")


__all__ = [
    "PEER_PROTOCOL_VERSION",
    "parse_peer_message",
    "read_bounded_request",
    "send_peer_message",
    "validate_registered_sender",
]
