from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from uuid import uuid4

from .workspace_core import RunWorkspace
from .workspace_instruction_rules import InstructionDocument


LOADED_INSTRUCTIONS_FILE = "loaded_instructions.json"
MAX_LOADED_INSTRUCTION_SOURCES = 500
MAX_LOADED_STATE_BYTES = 100_000
_STATE_LOCK = RLock()


def claim_unloaded_instruction_documents(
    workspace: RunWorkspace,
    documents: list[InstructionDocument],
) -> list[InstructionDocument]:
    if not documents:
        return []
    with _STATE_LOCK:
        loaded = _read_loaded_sources(workspace)
        claimed = [document for document in documents if document.path not in loaded]
        if not claimed:
            return []
        updated = list(loaded)
        for document in claimed:
            if document.path not in updated:
                updated.append(document.path)
        if len(updated) > MAX_LOADED_INSTRUCTION_SOURCES:
            updated = updated[-MAX_LOADED_INSTRUCTION_SOURCES:]
        _write_loaded_sources(workspace, updated)
        return claimed


def _state_path(workspace: RunWorkspace) -> Path:
    return workspace.session_dir / LOADED_INSTRUCTIONS_FILE


def _read_loaded_sources(workspace: RunWorkspace) -> list[str]:
    path = _state_path(workspace)
    if path.is_symlink():
        raise ValueError(f"Loaded instruction state must not be a symlink: {path}")
    if not path.exists():
        return []
    if not path.is_file() or path.stat().st_size > MAX_LOADED_STATE_BYTES:
        raise ValueError("Loaded instruction state is not a bounded regular file.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid loaded instruction state: {error.msg}") from error
    if not isinstance(payload, list) or not all(isinstance(item, str) for item in payload):
        raise ValueError("Loaded instruction state must be a list of source paths.")
    return list(dict.fromkeys(payload))


def _write_loaded_sources(workspace: RunWorkspace, sources: list[str]) -> None:
    path = _state_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError("Loaded instruction state path must not be a symlink.")
    encoded = json.dumps(sources, ensure_ascii=False, indent=2) + "\n"
    if len(encoded.encode("utf-8")) > MAX_LOADED_STATE_BYTES:
        raise ValueError("Loaded instruction state exceeds its size limit.")
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
