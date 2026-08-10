from __future__ import annotations

from .types import ChatMessage, ContentBlock


_USER_TASK_PREFIX = "User task:\n"
_RUNTIME_CONTEXT_MARKER = "\n\nProject directory:\n"


def continue_conversation(
    prior_messages: list[ChatMessage],
    fresh_messages: list[ChatMessage],
) -> list[ChatMessage]:
    return [
        fresh_messages[0],
        *(message for message in prior_messages if message.role != "system"),
        fresh_messages[1],
    ]


def conversation_for_next_prompt(
    messages: list[ChatMessage],
    current_task: str,
) -> list[ChatMessage]:
    carried = [message for message in messages if message.role != "system"]
    for index in range(len(carried) - 1, -1, -1):
        compacted = _compact_runtime_user_message(carried[index], current_task)
        if compacted is not None:
            carried[index] = compacted
            break
    return _drop_unpaired_trailing_tool_calls(carried)


def _compact_runtime_user_message(
    message: ChatMessage,
    current_task: str,
) -> ChatMessage | None:
    if message.role != "user":
        return None
    text = _leading_text(message.content)
    if not text.startswith(_USER_TASK_PREFIX) or _RUNTIME_CONTEXT_MARKER not in text:
        return None
    return ChatMessage(role="user", content=f"{_USER_TASK_PREFIX}{current_task}")


def _leading_text(content: str | list[ContentBlock]) -> str:
    if isinstance(content, str):
        return content
    if content and content[0].get("type") == "text":
        return str(content[0].get("text") or "")
    return ""


def _drop_unpaired_trailing_tool_calls(messages: list[ChatMessage]) -> list[ChatMessage]:
    if not messages or messages[-1].role != "assistant" or not isinstance(messages[-1].content, list):
        return messages
    content = messages[-1].content
    if not any(block.get("type") == "tool_call" for block in content):
        return messages
    retained = [block for block in content if block.get("type") != "tool_call"]
    if retained:
        return [*messages[:-1], ChatMessage(role="assistant", content=retained)]
    return messages[:-1]


__all__ = ["continue_conversation", "conversation_for_next_prompt"]
