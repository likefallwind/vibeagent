from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock
from uuid import uuid4

from .agent_conversation import conversation_for_next_prompt
from .redaction import redact_jsonable_payload, redact_sensitive_text
from .session_event_sanitization import sanitize_tool_call_input, sanitize_tool_result_payload
from .session_utils import session_dir
from .types import ChatMessage, ContentBlock
from .workspace_core import RunWorkspace


CONVERSATION_VERSION = 1
MAX_CONVERSATION_BYTES = 8_000_000
MAX_CONVERSATION_MESSAGES = 512
MAX_PERSISTED_TEXT_CHARS = 200_000
_STORE_LOCK = RLock()


class SessionConversationError(ValueError):
    pass


@dataclass(frozen=True)
class SessionConversationLoad:
    messages: tuple[ChatMessage, ...] = ()
    warning: str | None = None


def checkpoint_session_conversation(
    workspace: RunWorkspace,
    messages: list[ChatMessage],
    current_task: str,
) -> None:
    carried = conversation_for_next_prompt(messages, current_task)
    sanitized = [_sanitize_message(message) for message in carried]
    sanitized = _trim_to_conversation_boundary(
        sanitized[-MAX_CONVERSATION_MESSAGES:]
    )
    payload = {
        "version": CONVERSATION_VERSION,
        "run_id": workspace.run_id,
        "messages": [asdict(message) for message in sanitized],
    }
    encoded = _encode_bounded(payload)
    path = _conversation_path(workspace.session_dir)
    with _STORE_LOCK:
        _validate_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _validate_path(path)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_text(encoded, encoding="utf-8")
            os.chmod(temporary, 0o600)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def load_session_conversation(project_root: str | Path, run_id: str | None) -> SessionConversationLoad:
    if run_id is None:
        return SessionConversationLoad()
    try:
        return SessionConversationLoad(tuple(read_session_conversation(project_root, run_id)))
    except (OSError, UnicodeError, SessionConversationError, ValueError) as error:
        return SessionConversationLoad(
            warning=f"Conversation transcript unavailable for {run_id}; using bounded session context instead: {error}"
        )


def read_session_conversation(project_root: str | Path, run_id: str) -> list[ChatMessage]:
    path = _conversation_path(session_dir(project_root, run_id))
    with _STORE_LOCK:
        _validate_path(path)
        if not path.exists():
            return []
        if path.stat().st_size > MAX_CONVERSATION_BYTES:
            raise SessionConversationError(
                f"Conversation transcript exceeds {MAX_CONVERSATION_BYTES} bytes."
            )
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise SessionConversationError(f"Invalid conversation transcript: {error}") from error
    return _parse_payload(payload, run_id)


def _encode_bounded(payload: dict[str, object]) -> str:
    messages = list(payload["messages"])  # type: ignore[arg-type]
    while True:
        current = {**payload, "messages": messages}
        encoded = json.dumps(current, ensure_ascii=False, separators=(",", ":")) + "\n"
        if len(encoded.encode("utf-8")) <= MAX_CONVERSATION_BYTES:
            return encoded
        if len(messages) <= 1:
            raise SessionConversationError(
                f"Conversation transcript exceeds {MAX_CONVERSATION_BYTES} bytes."
            )
        messages = _trim_to_conversation_boundary(messages[1:])


def _sanitize_message(message: ChatMessage) -> ChatMessage:
    if isinstance(message.content, str):
        return ChatMessage(message.role, _bounded_redacted_text(message.content))
    blocks = [_sanitize_block(block) for block in message.content]
    return ChatMessage(message.role, [block for block in blocks if block is not None])


def _sanitize_block(block: ContentBlock) -> ContentBlock | None:
    block_type = block.get("type")
    if block_type == "text":
        return {"type": "text", "text": _bounded_redacted_text(str(block.get("text") or ""))}
    if block_type == "tool_call":
        return redact_jsonable_payload(
            {
                "type": "tool_call",
                "id": str(block.get("id") or ""),
                "name": str(block.get("name") or ""),
                "input": sanitize_tool_call_input(block.get("input")),
            }
        )
    if block_type == "tool_result":
        sanitized: ContentBlock = {
            "type": "tool_result",
            "tool_call_id": str(block.get("tool_call_id") or ""),
            "content": _sanitize_tool_result_content(block.get("content")),
        }
        if isinstance(block.get("is_error"), bool):
            sanitized["is_error"] = block["is_error"]
        return sanitized
    if block_type in {"image", "image_url", "document"}:
        return None
    return None


def _sanitize_tool_result_content(value: object) -> object:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return _bounded_redacted_text(value)
        sanitized = redact_jsonable_payload(sanitize_tool_result_payload(parsed))
        return _bounded_redacted_text(json.dumps(sanitized, ensure_ascii=False))
    if isinstance(value, list):
        blocks = [_sanitize_block(block) for block in value if isinstance(block, dict)]
        return [block for block in blocks if block is not None]
    sanitized = redact_jsonable_payload(sanitize_tool_result_payload(value))
    return _bounded_redacted_text(json.dumps(sanitized, ensure_ascii=False))


def _bounded_redacted_text(value: str) -> str:
    redacted = redact_sensitive_text(value)
    if len(redacted) <= MAX_PERSISTED_TEXT_CHARS:
        return redacted
    return redacted[:MAX_PERSISTED_TEXT_CHARS] + "...[truncated]"


def _parse_payload(payload: object, expected_run_id: str) -> list[ChatMessage]:
    if not isinstance(payload, dict) or payload.get("version") != CONVERSATION_VERSION:
        raise SessionConversationError("Unsupported or malformed conversation transcript.")
    if payload.get("run_id") != expected_run_id:
        raise SessionConversationError("Conversation transcript session does not match its directory.")
    values = payload.get("messages")
    if not isinstance(values, list) or len(values) > MAX_CONVERSATION_MESSAGES:
        raise SessionConversationError("Malformed conversation transcript messages.")
    messages = [_parse_message(value) for value in values]
    if any(message.role == "system" for message in messages):
        raise SessionConversationError("Persisted conversation must not contain system messages.")
    return messages


def _parse_message(value: object) -> ChatMessage:
    if not isinstance(value, dict) or value.get("role") not in {"user", "assistant"}:
        raise SessionConversationError("Malformed conversation message.")
    content = value.get("content")
    if not isinstance(content, (str, list)):
        raise SessionConversationError("Malformed conversation message content.")
    if isinstance(content, list) and any(not isinstance(block, dict) for block in content):
        raise SessionConversationError("Malformed conversation content block.")
    if isinstance(content, list):
        for block in content:
            _validate_content_block(block)
    return ChatMessage(value["role"], content)  # type: ignore[arg-type]


def _validate_content_block(block: dict[str, object]) -> None:
    block_type = block.get("type")
    if block_type == "text" and isinstance(block.get("text"), str):
        return
    if (
        block_type == "tool_call"
        and isinstance(block.get("id"), str)
        and isinstance(block.get("name"), str)
        and isinstance(block.get("input"), dict)
    ):
        return
    if (
        block_type == "tool_result"
        and isinstance(block.get("tool_call_id"), str)
        and isinstance(block.get("content"), (str, list))
    ):
        nested = block.get("content")
        if isinstance(nested, list):
            for item in nested:
                if not isinstance(item, dict) or item.get("type") != "text" or not isinstance(item.get("text"), str):
                    raise SessionConversationError("Malformed persisted tool result content.")
        return
    raise SessionConversationError("Unsupported persisted conversation content block.")


def _trim_to_conversation_boundary(messages: list[object]) -> list[object]:
    trimmed = list(messages)
    while trimmed and not _is_user_prompt_message(trimmed[0]):
        trimmed.pop(0)
    return trimmed


def _is_user_prompt_message(value: object) -> bool:
    if isinstance(value, ChatMessage):
        return value.role == "user" and isinstance(value.content, str)
    if not isinstance(value, dict) or value.get("role") != "user":
        return False
    return isinstance(value.get("content"), str)


def _conversation_path(directory: Path) -> Path:
    return directory / "conversation.json"


def _validate_path(path: Path) -> None:
    if path.parent.is_symlink() or (path.parent.exists() and not path.parent.is_dir()):
        raise SessionConversationError(f"Session path is not a regular directory: {path.parent}")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise SessionConversationError(f"Conversation transcript is not a regular file: {path}")


__all__ = [
    "MAX_CONVERSATION_BYTES",
    "MAX_CONVERSATION_MESSAGES",
    "SessionConversationError",
    "SessionConversationLoad",
    "checkpoint_session_conversation",
    "load_session_conversation",
    "read_session_conversation",
]
