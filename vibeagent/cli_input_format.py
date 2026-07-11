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
    direct_text = record.get("text")
    if isinstance(direct_text, str):
        return (direct_text,)
    direct_message = record.get("message")
    if isinstance(direct_message, str):
        return (direct_message,)
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
