from __future__ import annotations

import json
from pathlib import Path
import re
from threading import RLock
from uuid import uuid4

from .workspace_core import RunWorkspace
from .workspace_instruction_rules import InstructionDocument


LOADED_INSTRUCTIONS_FILE = "loaded_instructions.json"
MAX_LOADED_INSTRUCTION_SOURCES = 500
MAX_LOADED_INSTRUCTION_CONSUMERS = 100
MAX_LOADED_STATE_BYTES = 100_000
DEFAULT_INSTRUCTION_CONSUMER = "main"
_STATE_LOCK = RLock()


def claim_unloaded_instruction_documents(
    workspace: RunWorkspace,
    documents: list[InstructionDocument],
    consumer_id: str = DEFAULT_INSTRUCTION_CONSUMER,
) -> list[InstructionDocument]:
    if not documents:
        return []
    normalized_consumer = _validate_consumer_id(consumer_id)
    with _STATE_LOCK:
        state = _read_loaded_state(workspace)
        loaded = state.get(normalized_consumer, [])
        claimed = [document for document in documents if document.claim_path not in loaded]
        if not claimed:
            return []
        updated = list(loaded)
        for document in claimed:
            if document.claim_path not in updated:
                updated.append(document.claim_path)
        if len(updated) > MAX_LOADED_INSTRUCTION_SOURCES:
            updated = updated[-MAX_LOADED_INSTRUCTION_SOURCES:]
        if normalized_consumer not in state and len(state) >= MAX_LOADED_INSTRUCTION_CONSUMERS:
            _evict_old_consumer(state)
        state[normalized_consumer] = updated
        _write_loaded_state(workspace, state)
        return claimed


def reset_loaded_instruction_documents(
    workspace: RunWorkspace,
    consumer_id: str = DEFAULT_INSTRUCTION_CONSUMER,
) -> int:
    normalized_consumer = _validate_consumer_id(consumer_id)
    with _STATE_LOCK:
        state = _read_loaded_state(workspace)
        removed = len(state.pop(normalized_consumer, []))
        if removed:
            _write_loaded_state(workspace, state)
        return removed


def _state_path(workspace: RunWorkspace) -> Path:
    return workspace.session_dir / LOADED_INSTRUCTIONS_FILE


def _read_loaded_state(workspace: RunWorkspace) -> dict[str, list[str]]:
    path = _state_path(workspace)
    if path.is_symlink():
        raise ValueError(f"Loaded instruction state must not be a symlink: {path}")
    if not path.exists():
        return {}
    if not path.is_file() or path.stat().st_size > MAX_LOADED_STATE_BYTES:
        raise ValueError("Loaded instruction state is not a bounded regular file.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid loaded instruction state: {error.msg}") from error
    if isinstance(payload, list):
        return {DEFAULT_INSTRUCTION_CONSUMER: _validate_sources(payload)}
    if not isinstance(payload, dict) or payload.get("version") != 2:
        raise ValueError("Loaded instruction state must use version 2 or the legacy source list.")
    consumers = payload.get("consumers")
    if not isinstance(consumers, dict) or len(consumers) > MAX_LOADED_INSTRUCTION_CONSUMERS:
        raise ValueError(f"Loaded instruction state must contain at most {MAX_LOADED_INSTRUCTION_CONSUMERS} consumers.")
    return {
        _validate_consumer_id(consumer): _validate_sources(sources)
        for consumer, sources in consumers.items()
    }


def _write_loaded_state(workspace: RunWorkspace, consumers: dict[str, list[str]]) -> None:
    path = _state_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError("Loaded instruction state path must not be a symlink.")
    if len(consumers) > MAX_LOADED_INSTRUCTION_CONSUMERS:
        raise ValueError(f"Loaded instruction state exceeds {MAX_LOADED_INSTRUCTION_CONSUMERS} consumers.")
    payload = {"version": 2, "consumers": consumers}
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(encoded.encode("utf-8")) > MAX_LOADED_STATE_BYTES:
        raise ValueError("Loaded instruction state exceeds its size limit.")
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _evict_old_consumer(consumers: dict[str, list[str]]) -> None:
    candidate = next((key for key in consumers if key != DEFAULT_INSTRUCTION_CONSUMER), None)
    if candidate is None:
        candidate = next(iter(consumers), None)
    if candidate is not None:
        consumers.pop(candidate, None)


def _validate_consumer_id(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", value) is None:
        raise ValueError("Instruction consumer id must contain 1-200 safe identifier characters.")
    return value


def _validate_sources(value: object) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_LOADED_INSTRUCTION_SOURCES:
        raise ValueError(f"Loaded instruction sources must contain at most {MAX_LOADED_INSTRUCTION_SOURCES} paths.")
    sources: list[str] = []
    for item in value:
        if not isinstance(item, str) or len(item) > 1_000:
            raise ValueError("Loaded instruction sources must be bounded path strings.")
        path = Path(item)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Loaded instruction source paths must stay project-relative.")
        if item not in sources:
            sources.append(item)
    return sources


__all__ = [
    "DEFAULT_INSTRUCTION_CONSUMER",
    "claim_unloaded_instruction_documents",
    "reset_loaded_instruction_documents",
]
