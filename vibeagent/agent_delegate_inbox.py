from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .agent_runtime_utils import append_session_event
from .types import ChatMessage
from .workspace_core import RunWorkspace


@dataclass(frozen=True)
class DelegateInbox:
    workspace: RunWorkspace
    subagent_id: str
    parent_iteration: int
    receive: Callable[[bool], list[str]]
    checkpoint: Callable[[list[ChatMessage]], None]

    def append_to(self, messages: list[ChatMessage], *, final: bool = False) -> bool:
        incoming = self.receive(final)
        if not incoming:
            return False
        for message in incoming:
            messages.append(
                ChatMessage(
                    role="user",
                    content=f"Incoming message from the lead or another agent:\n{message}",
                )
            )
        append_session_event(
            self.workspace.session_dir,
            "subagent_messages_received",
            {
                "subagent_id": self.subagent_id,
                "parent_iteration": self.parent_iteration,
                "count": len(incoming),
            },
        )
        self.checkpoint(messages)
        return True

    def close(self) -> None:
        self.receive(True)
        self.receive(True)


__all__ = ["DelegateInbox"]
