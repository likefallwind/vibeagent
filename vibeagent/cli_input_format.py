from __future__ import annotations

from collections.abc import Iterable
import json


class TaskInputFormatError(ValueError):
    pass


def resolve_stream_json_task_text(raw: str) -> str:
    chunks: list[str] = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise TaskInputFormatError(f"Invalid stream-json input on line {line_number}: {exc.msg}.") from exc
        chunks.extend(_text_chunks_from_record(record))
    return "\n".join(chunk for chunk in chunks if chunk.strip()).strip()


def _text_chunks_from_record(record: object) -> Iterable[str]:
    if not isinstance(record, dict):
        return ()
    messages = record.get("messages")
    if isinstance(messages, list):
        chunks: list[str] = []
        for message in messages:
            chunks.extend(_text_from_role_message(message))
        return tuple(chunks)
    if not _allows_task_text(record):
        return ()
    direct_text = record.get("text")
    if isinstance(direct_text, str):
        return (direct_text,)
    direct_message = record.get("message")
    if isinstance(direct_message, str):
        return (direct_message,)
    if isinstance(direct_message, dict):
        role_message_text = _text_from_role_message(direct_message)
        if role_message_text or _record_role(direct_message) is not None:
            return role_message_text
    message_text = _text_from_message(direct_message)
    if message_text:
        return message_text
    return _text_from_content(record.get("content"))


def _text_from_message(message: object) -> tuple[str, ...]:
    if not isinstance(message, dict):
        return ()
    text = message.get("text")
    if isinstance(text, str):
        return (text,)
    return _text_from_content(message.get("content"))


def _text_from_role_message(message: object) -> tuple[str, ...]:
    if not isinstance(message, dict) or not _allows_task_text(message):
        return ()
    direct_text = message.get("text")
    if isinstance(direct_text, str):
        return (direct_text,)
    direct_message = message.get("message")
    if isinstance(direct_message, str):
        return (direct_message,)
    if isinstance(direct_message, dict):
        nested_message = _text_from_role_message(direct_message)
        if nested_message or _record_role(direct_message) is not None:
            return nested_message
    return _text_from_content(message.get("content"))


def _text_from_content(content: object) -> tuple[str, ...]:
    if isinstance(content, str):
        return (content,)
    if not isinstance(content, list):
        return ()
    chunks: list[str] = []
    for item in content:
        if isinstance(item, str):
            chunks.append(item)
        elif isinstance(item, dict) and isinstance(item.get("text"), str):
            chunks.append(item["text"])
    return tuple(chunks)


def _allows_task_text(record: dict[str, object]) -> bool:
    role = _record_role(record)
    return role is None or role == "user"


def _record_role(record: dict[str, object]) -> str | None:
    role = record.get("role")
    if isinstance(role, str) and role.strip():
        return role.strip().lower()
    record_type = record.get("type")
    if isinstance(record_type, str):
        normalized = record_type.strip().lower()
        if normalized in {"user", "assistant", "system"}:
            return normalized
    return None
