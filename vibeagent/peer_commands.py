from __future__ import annotations

from .peer_registry import list_peer_sessions
from .peer_types import PeerMessagingError


def get_peer_sessions_text(max_peers: int = 100) -> str:
    try:
        peers, invalid = list_peer_sessions()
    except (OSError, PeerMessagingError) as error:
        return f"Peer sessions unavailable: {error}"
    shown = peers[: max(1, min(max_peers, 500))]
    lines = [f"Reachable peer sessions: {len(shown)}/{len(peers)} (invalid: {invalid})"]
    for peer in shown:
        lines.append(
            f"  {peer.id} name={peer.name} pid={peer.pid} project={peer.project_root} "
            f"run={peer.run_id or '.'} bypassesPermissions={str(peer.bypasses_permissions).lower()}"
        )
    if not shown:
        lines.append("  none")
    return "\n".join(lines)


__all__ = ["get_peer_sessions_text"]
