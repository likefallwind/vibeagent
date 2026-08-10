from __future__ import annotations

from .peer_runtime import PeerSessionRuntime


def handle_peer_inbox_command(runtime: PeerSessionRuntime | None, argument: str | None) -> str:
    if runtime is None:
        return "Peer messaging is unavailable in this session."
    if argument is None:
        held = runtime.held_messages()
        lines = [f"Held peer messages: {len(held)}"]
        for message in held:
            preview = " ".join(message.message.split())[:160]
            lines.append(f"  {message.sender_id} from={message.sender_name} message={preview}")
        if not held:
            lines.append("  none")
        return "\n".join(lines)
    parts = argument.split()
    if len(parts) != 2 or parts[0].lower() not in {"accept", "deny"}:
        return "Usage: /peer-inbox [accept|deny <sender-id|all>]"
    sender_id = None if parts[1].lower() == "all" else parts[1]
    decided, remaining = runtime.decide_held(accept=parts[0].lower() == "accept", sender_id=sender_id)
    action = "Accepted" if parts[0].lower() == "accept" else "Denied"
    return f"{action} {decided} held peer message(s); remaining: {remaining}."


__all__ = ["handle_peer_inbox_command"]
