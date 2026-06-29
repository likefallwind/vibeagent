from __future__ import annotations

import time

from .minimax import content_blocks_to_text
from .types import ChatClient, ChatMessage


CHAT_SYSTEM_PROMPT = """You are VibeAgent's daily conversation mode.

Reply naturally and helpfully in the user's language.
Do not use the coding-agent JSON action protocol.
Do not use coding-agent tools.
Do not claim to create files, run commands, or inspect the local workspace.
If the user asks for code generation, file edits, command execution, or a programming task,
briefly tell them to switch to code mode with /code."""


def run_chat(
    message: str,
    client: ChatClient,
    history: list[ChatMessage] | None = None,
    max_output_tokens: int = 4096,
    model_retries: int = 1,
    model_retry_delay_ms: int = 250,
    model_timeout_ms: int = 120_000,
) -> str:
    # Chat mode is a plain assistant turn with bounded prior conversation context.
    messages = build_chat_messages(message, history or [])
    response = complete_chat_with_retries(
        client,
        messages,
        max_output_tokens=max_output_tokens,
        model_retries=model_retries,
        model_retry_delay_ms=model_retry_delay_ms,
        model_timeout_ms=model_timeout_ms,
    )
    if isinstance(response, str):
        text = response
    else:
        text = content_blocks_to_text(response.content)
    return text.strip() or "(empty response)"


def complete_chat_with_retries(
    client: ChatClient,
    messages: list[ChatMessage],
    *,
    max_output_tokens: int,
    model_retries: int,
    model_retry_delay_ms: int,
    model_timeout_ms: int,
) -> object:
    attempts = max(0, model_retries) + 1
    for attempt in range(1, attempts + 1):
        try:
            return client.complete(messages, max_tokens=max_output_tokens, timeout_ms=model_timeout_ms)
        except Exception:
            if attempt >= attempts:
                raise
            if model_retry_delay_ms > 0:
                time.sleep(model_retry_delay_ms / 1000)
    raise RuntimeError("Model request failed.")


def build_chat_messages(message: str, history: list[ChatMessage] | None = None, max_history: int = 12) -> list[ChatMessage]:
    bounded_history = list(history or [])[-max_history:]
    return [
        ChatMessage(role="system", content=CHAT_SYSTEM_PROMPT),
        *bounded_history,
        ChatMessage(role="user", content=message),
    ]
