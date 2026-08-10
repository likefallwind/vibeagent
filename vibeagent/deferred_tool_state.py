from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .redaction import redact_jsonable_payload
from .session_event_sanitization import sanitize_tool_call_input
from .types import ContentBlock
from .workspace_core import RunWorkspace


DEFERRED_TOOL_STATE_VERSION = 1
MAX_DEFERRED_TOOL_STATE_BYTES = 2_000_000


@dataclass(frozen=True)
class DeferredToolState:
    assistant_content: tuple[ContentBlock, ...]
    completed_tool_results: tuple[ContentBlock, ...]
    next_tool_index: int

    @property
    def tool_calls(self) -> tuple[ContentBlock, ...]:
        return tuple(
            block for block in self.assistant_content if block.get("type") == "tool_call"
        )

    @property
    def pending_tool_use(self) -> dict[str, object]:
        calls = self.tool_calls
        if self.next_tool_index < 0 or self.next_tool_index >= len(calls):
            raise ValueError("Deferred tool state does not identify a pending tool call.")
        block = calls[self.next_tool_index]
        value = {
            "id": str(block.get("id") or ""),
            "name": str(block.get("name") or ""),
            "input": sanitize_tool_call_input(block.get("input")),
        }
        return redact_jsonable_payload(value)


class DeferredToolStateError(ValueError):
    pass


def write_deferred_tool_state(workspace: RunWorkspace, state: DeferredToolState) -> None:
    payload = {
        "version": DEFERRED_TOOL_STATE_VERSION,
        "run_id": workspace.run_id,
        # Pending inputs must remain exact so resume can execute the same call.
        # The state file is private; model-visible output uses pending_tool_use.
        "assistant_content": list(state.assistant_content),
        "completed_tool_results": redact_jsonable_payload(
            list(state.completed_tool_results)
        ),
        "next_tool_index": state.next_tool_index,
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    if len(encoded.encode("utf-8")) > MAX_DEFERRED_TOOL_STATE_BYTES:
        raise DeferredToolStateError(
            f"Deferred tool state exceeds {MAX_DEFERRED_TOOL_STATE_BYTES} bytes."
        )
    path = _state_path(workspace.session_dir)
    _validate_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(encoded, encoding="utf-8")
        os.chmod(temporary, 0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def read_deferred_tool_state(workspace: RunWorkspace) -> DeferredToolState | None:
    path = _state_path(workspace.session_dir)
    _validate_path(path)
    if not path.exists():
        return None
    if path.stat().st_size > MAX_DEFERRED_TOOL_STATE_BYTES:
        raise DeferredToolStateError(
            f"Deferred tool state exceeds {MAX_DEFERRED_TOOL_STATE_BYTES} bytes."
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DeferredToolStateError(f"Invalid deferred tool state: {error}") from error
    return _parse_state(payload, workspace.run_id)


def clear_deferred_tool_state(workspace: RunWorkspace) -> None:
    path = _state_path(workspace.session_dir)
    _validate_path(path)
    path.unlink(missing_ok=True)


def _parse_state(payload: object, run_id: str) -> DeferredToolState:
    if not isinstance(payload, dict) or payload.get("version") != DEFERRED_TOOL_STATE_VERSION:
        raise DeferredToolStateError("Unsupported or malformed deferred tool state.")
    if payload.get("run_id") != run_id:
        raise DeferredToolStateError("Deferred tool state session does not match its directory.")
    assistant = payload.get("assistant_content")
    results = payload.get("completed_tool_results")
    next_index = payload.get("next_tool_index")
    if not isinstance(assistant, list) or not all(isinstance(item, dict) for item in assistant):
        raise DeferredToolStateError("Deferred assistant content must be a list of blocks.")
    if not isinstance(results, list) or not all(isinstance(item, dict) for item in results):
        raise DeferredToolStateError("Deferred tool results must be a list of blocks.")
    if type(next_index) is not int:
        raise DeferredToolStateError("Deferred next tool index must be an integer.")
    state = DeferredToolState(tuple(assistant), tuple(results), next_index)  # type: ignore[arg-type]
    pending = state.pending_tool_use
    if not pending["id"] or not pending["name"] or not isinstance(pending["input"], dict):
        raise DeferredToolStateError("Deferred pending tool call is malformed.")
    if len(state.completed_tool_results) != state.next_tool_index:
        raise DeferredToolStateError("Deferred completed results do not match the pending index.")
    return state


def _state_path(session_dir: Path) -> Path:
    return session_dir / "deferred_tool_use.json"


def _validate_path(path: Path) -> None:
    if path.is_symlink():
        raise DeferredToolStateError(
            f"Deferred tool state path must not be a symbolic link: {path}"
        )


__all__ = [
    "DeferredToolState",
    "DeferredToolStateError",
    "clear_deferred_tool_state",
    "read_deferred_tool_state",
    "write_deferred_tool_state",
]
