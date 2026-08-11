from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json

from . import MACHINE_OUTPUT_SCHEMA_VERSION


class TaskInputFormatError(ValueError):
    pass


@dataclass(frozen=True)
class StreamJsonTaskInput:
    task: str
    system_prompt: str | None = None
    assistant_context: str | None = None
    session_id: str | None = None
    user_messages: tuple[str, ...] = ()


SESSION_ID_KEYS = ("session_id", "sessionId", "run_id", "runId")
NON_TASK_RECORD_TYPES = {"event", "result"}


def resolve_stream_json_task_text(raw: str) -> str:
    return resolve_stream_json_task_input(raw).task


def resolve_json_task_text(raw: str) -> str:
    return resolve_json_task_input(raw).task


def resolve_json_task_input(raw: str) -> StreamJsonTaskInput:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TaskInputFormatError(f"Invalid json input: {exc.msg}.") from exc
    records = parsed if isinstance(parsed, list) else [parsed]
    return _resolve_task_input_records(records)


def resolve_stream_json_task_input(raw: str) -> StreamJsonTaskInput:
    records: list[object] = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            records.append(json.loads(stripped))
        except json.JSONDecodeError as exc:
            raise TaskInputFormatError(f"Invalid stream-json input on line {line_number}: {exc.msg}.") from exc
    return _resolve_task_input_records(records)


def _resolve_task_input_records(records: Iterable[object]) -> StreamJsonTaskInput:
    user_chunks: list[str] = []
    system_chunks: list[str] = []
    assistant_chunks: list[str] = []
    chunks: list[str] = []
    user_messages: list[str] = []
    session_id: str | None = None
    for record in records:
        _validate_schema_version(record)
        session_id = session_id or _session_id_from_record(record)
        chunks.extend(_text_chunks_from_record(record))
        user_messages.extend(_user_messages_from_record(record))
        role_chunks = _role_text_chunks_from_record(record)
        user_chunks.extend(role_chunks.user)
        system_chunks.extend(role_chunks.system)
        assistant_chunks.extend(role_chunks.assistant)
    task_chunks = user_chunks if user_chunks or system_chunks or assistant_chunks else chunks
    return StreamJsonTaskInput(
        task=_join_text_chunks(task_chunks),
        system_prompt=_optional_join_text_chunks(system_chunks),
        assistant_context=_optional_join_text_chunks(assistant_chunks),
        session_id=session_id,
        user_messages=tuple(user_messages),
    )


def _validate_schema_version(record: object) -> None:
    if not isinstance(record, dict) or "schemaVersion" not in record:
        return
    schema_version = record.get("schemaVersion")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        raise TaskInputFormatError("schemaVersion must be an integer.")
    if schema_version > MACHINE_OUTPUT_SCHEMA_VERSION:
        raise TaskInputFormatError(
            f"Unsupported schemaVersion {schema_version}; this VibeAgent supports up to {MACHINE_OUTPUT_SCHEMA_VERSION}."
        )
    if schema_version < 1:
        raise TaskInputFormatError("schemaVersion must be at least 1.")


@dataclass(frozen=True)
class _RoleTextChunks:
    user: tuple[str, ...] = ()
    system: tuple[str, ...] = ()
    assistant: tuple[str, ...] = ()


def _role_text_chunks_from_record(record: object) -> _RoleTextChunks:
    if not isinstance(record, dict):
        return _RoleTextChunks()
    messages = _message_sequence_from_record(record)
    if messages is not None:
        user: list[str] = []
        system: list[str] = []
        assistant: list[str] = []
        for message in messages:
            chunks = _role_text_chunks_from_message(message)
            user.extend(chunks.user)
            system.extend(chunks.system)
            assistant.extend(chunks.assistant)
        return _RoleTextChunks(tuple(user), tuple(system), tuple(assistant))
    return _role_text_chunks_from_message(record)


def _role_text_chunks_from_message(message: object) -> _RoleTextChunks:
    if not isinstance(message, dict):
        return _RoleTextChunks()
    if _is_non_task_machine_record(message):
        return _RoleTextChunks()
    role = _record_role(message)
    nested = message.get("message")
    if role is None and isinstance(nested, dict) and _record_role(nested) is not None:
        return _role_text_chunks_from_message(nested)
    text = _message_text_chunks(message)
    if role == "system":
        return _RoleTextChunks(system=text)
    if role == "assistant":
        return _RoleTextChunks(assistant=text)
    if role == "user" or (role is None and text):
        return _RoleTextChunks(user=text)
    return _RoleTextChunks()


def _user_messages_from_record(record: object) -> tuple[str, ...]:
    if not isinstance(record, dict):
        return ()
    messages = _message_sequence_from_record(record)
    if messages is not None:
        replay: list[str] = []
        for message in messages:
            replay.extend(_user_messages_from_message(message))
        return tuple(replay)
    return _user_messages_from_message(record)


def _user_messages_from_message(message: object) -> tuple[str, ...]:
    if not isinstance(message, dict) or _is_non_task_machine_record(message):
        return ()
    role = _record_role(message)
    nested = message.get("message")
    if role is None and isinstance(nested, dict) and _record_role(nested) is not None:
        return _user_messages_from_message(nested)
    if role not in {None, "user"}:
        return ()
    text = _join_text_chunks(_message_text_chunks(message))
    return (text,) if text else ()


def _text_chunks_from_record(record: object) -> Iterable[str]:
    if not isinstance(record, dict):
        return ()
    messages = _message_sequence_from_record(record)
    if messages is not None:
        chunks: list[str] = []
        for message in messages:
            chunks.extend(_text_from_role_message(message))
        return tuple(chunks)
    if not _allows_task_text(record):
        return ()
    direct_text = _direct_text_chunks(record)
    if direct_text:
        return direct_text
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
    direct_text = _direct_text_chunks(message)
    if direct_text:
        return direct_text
    return _text_from_content(message.get("content"))


def _text_from_role_message(message: object) -> tuple[str, ...]:
    if not isinstance(message, dict) or not _allows_task_text(message):
        return ()
    return _message_text_chunks(message)


def _message_text_chunks(message: dict[str, object]) -> tuple[str, ...]:
    direct_text = _direct_text_chunks(message)
    if direct_text:
        return direct_text
    direct_message = message.get("message")
    if isinstance(direct_message, str):
        return (direct_message,)
    if isinstance(direct_message, dict):
        nested_message = _message_text_chunks(direct_message)
        if nested_message or _record_role(direct_message) is not None:
            return nested_message
    return _text_from_content(message.get("content"))


def _direct_text_chunks(record: dict[str, object]) -> tuple[str, ...]:
    for key in ("text", "prompt", "input"):
        value = record.get(key)
        if isinstance(value, str):
            return (value,)
    return ()


def _message_sequence_from_record(record: dict[str, object]) -> list[object] | None:
    messages = record.get("messages")
    if isinstance(messages, list):
        return messages
    input_value = record.get("input")
    if isinstance(input_value, list):
        return input_value
    return None


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
    if _is_non_task_machine_record(record):
        return False
    return role is None or role == "user"


def _is_non_task_machine_record(record: dict[str, object]) -> bool:
    if _record_role(record) is not None:
        return False
    record_type = record.get("type")
    return isinstance(record_type, str) and record_type.strip().lower() in NON_TASK_RECORD_TYPES


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


def _session_id_from_record(record: object) -> str | None:
    if not isinstance(record, dict):
        return None
    direct = _direct_session_id(record)
    if direct is not None:
        return direct
    for key in ("message", "event"):
        nested = record.get(key)
        if isinstance(nested, dict):
            nested_session_id = _session_id_from_record(nested)
            if nested_session_id is not None:
                return nested_session_id
    for key in ("messages", "input"):
        nested_sequence = record.get(key)
        if isinstance(nested_sequence, list):
            for item in nested_sequence:
                nested_session_id = _session_id_from_record(item)
                if nested_session_id is not None:
                    return nested_session_id
    return None


def _direct_session_id(record: dict[str, object]) -> str | None:
    for key in SESSION_ID_KEYS:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _join_text_chunks(chunks: Iterable[str]) -> str:
    return "\n".join(chunk for chunk in chunks if chunk.strip()).strip()


def _optional_join_text_chunks(chunks: Iterable[str]) -> str | None:
    joined = _join_text_chunks(chunks)
    return joined or None
