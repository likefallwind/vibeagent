from __future__ import annotations

from .minimax import content_blocks_to_text
from .types import ChatClient, ChatMessage


CHAT_SYSTEM_PROMPT = """You are VibeAgent's daily conversation mode.

Reply naturally and helpfully in the user's language.
Do not use the coding-agent JSON action protocol.
Do not use coding-agent tools.
Do not claim to create files, run commands, or inspect the local workspace.
If the user asks for code generation, file edits, command execution, or a programming task,
briefly tell them to switch to code mode with /code."""


def run_chat(message: str, client: ChatClient, history: list[ChatMessage] | None = None) -> str:
    # Chat mode is a plain assistant turn with bounded prior conversation context.
    messages = build_chat_messages(message, history or [])
    response = client.complete(messages)
    if isinstance(response, str):
        text = response
    else:
        text = content_blocks_to_text(response.content)
    return text.strip() or "(empty response)"


def build_chat_messages(message: str, history: list[ChatMessage] | None = None, max_history: int = 12) -> list[ChatMessage]:
    bounded_history = list(history or [])[-max_history:]
    return [
        ChatMessage(role="system", content=CHAT_SYSTEM_PROMPT),
        *bounded_history,
        ChatMessage(role="user", content=message),
    ]
