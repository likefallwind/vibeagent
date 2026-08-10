from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock
from typing import Literal
from uuid import uuid4

from .redaction import redact_jsonable_payload
from .types import ChatMessage, DelegateTaskAction, DelegateTaskObservation
from .workspace_agent_profile_parser import MAX_AGENT_TURNS
from .workspace_core import RunWorkspace


TRANSCRIPT_VERSION = 1
MAX_TRANSCRIPT_BYTES = 8_000_000
MAX_TRANSCRIPT_FILES = 1_000
SUBAGENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_STORE_LOCK = RLock()


class SubagentTranscriptError(ValueError):
    pass


@dataclass(frozen=True)
class SubagentTranscript:
    subagent_id: str
    action: DelegateTaskAction
    messages: list[ChatMessage]
    status: Literal["running", "completed", "failed", "cancelled"]
    runs: int


def create_subagent_transcript(
    workspace: RunWorkspace,
    subagent_id: str,
    action: DelegateTaskAction,
    messages: list[ChatMessage],
) -> None:
    _validate_subagent_id(subagent_id)
    _write_transcript(workspace, SubagentTranscript(subagent_id, action, list(messages), "running", 1))


def resume_subagent_transcript(
    workspace: RunWorkspace,
    transcript: SubagentTranscript,
    messages: list[ChatMessage],
) -> None:
    with _STORE_LOCK:
        current = read_subagent_transcript(workspace, transcript.subagent_id)
        if current.status == "running":
            raise SubagentTranscriptError(f"Subagent {transcript.subagent_id} is still running.")
        if current.runs != transcript.runs:
            raise SubagentTranscriptError(f"Subagent {transcript.subagent_id} transcript changed before resume.")
        _write_transcript(
            workspace,
            SubagentTranscript(
                transcript.subagent_id,
                transcript.action,
                list(messages),
                "running",
                transcript.runs + 1,
            ),
        )


def checkpoint_subagent_transcript(
    workspace: RunWorkspace,
    subagent_id: str,
    action: DelegateTaskAction,
    messages: list[ChatMessage],
) -> None:
    current = read_subagent_transcript(workspace, subagent_id)
    _write_transcript(
        workspace,
        SubagentTranscript(subagent_id, action, list(messages), "running", current.runs),
    )


def complete_subagent_transcript(
    workspace: RunWorkspace,
    subagent_id: str,
    action: DelegateTaskAction,
    messages: list[ChatMessage],
    result: DelegateTaskObservation,
) -> None:
    current = read_subagent_transcript(workspace, subagent_id)
    status = "cancelled" if result.cancelled else ("completed" if result.ok else "failed")
    _write_transcript(
        workspace,
        SubagentTranscript(subagent_id, action, list(messages), status, current.runs),
    )


def read_subagent_transcript(workspace: RunWorkspace, subagent_id: str) -> SubagentTranscript:
    path = _transcript_path(workspace, subagent_id)
    with _STORE_LOCK:
        _validate_store_path(path)
        if not path.exists():
            raise SubagentTranscriptError(f"Subagent {subagent_id} was not found in this session.")
        if not path.is_file():
            raise SubagentTranscriptError(f"Subagent transcript is not a regular file: {path}")
        if path.stat().st_size > MAX_TRANSCRIPT_BYTES:
            raise SubagentTranscriptError(f"Subagent transcript exceeds {MAX_TRANSCRIPT_BYTES} bytes.")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SubagentTranscriptError(f"Invalid subagent transcript: {error}") from error
    return _parse_transcript(payload, subagent_id)


def list_subagent_transcripts(
    workspace: RunWorkspace,
) -> tuple[list[SubagentTranscript], int, bool]:
    root = workspace.session_dir / "subagents"
    with _STORE_LOCK:
        if root.is_symlink():
            raise SubagentTranscriptError(f"Subagent transcript directory must not be a symlink: {root}")
        if not root.exists():
            return [], 0, False
        if not root.is_dir():
            raise SubagentTranscriptError(f"Subagent transcript path is not a directory: {root}")
        entries = sorted(
            (path for path in root.iterdir() if not (path.name.startswith(".") and path.suffix == ".tmp")),
            key=lambda path: path.name,
        )
        truncated = len(entries) > MAX_TRANSCRIPT_FILES
        transcripts: list[SubagentTranscript] = []
        invalid = 0
        for path in entries[:MAX_TRANSCRIPT_FILES]:
            if path.is_symlink() or not path.is_file() or path.suffix != ".json":
                invalid += 1
                continue
            subagent_id = path.stem
            try:
                transcripts.append(read_subagent_transcript(workspace, subagent_id))
            except SubagentTranscriptError:
                invalid += 1
    return transcripts, invalid, truncated


def _write_transcript(workspace: RunWorkspace, transcript: SubagentTranscript) -> None:
    path = _transcript_path(workspace, transcript.subagent_id)
    payload = redact_jsonable_payload(
        {
            "version": TRANSCRIPT_VERSION,
            "subagent_id": transcript.subagent_id,
            "action": asdict(transcript.action),
            "messages": [asdict(message) for message in transcript.messages],
            "status": transcript.status,
            "runs": transcript.runs,
        }
    )
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(encoded.encode("utf-8")) > MAX_TRANSCRIPT_BYTES:
        raise SubagentTranscriptError(f"Subagent transcript exceeds {MAX_TRANSCRIPT_BYTES} bytes.")
    with _STORE_LOCK:
        _validate_store_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _validate_store_path(path)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_text(encoded, encoding="utf-8")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def _transcript_path(workspace: RunWorkspace, subagent_id: str) -> Path:
    _validate_subagent_id(subagent_id)
    return workspace.session_dir / "subagents" / f"{subagent_id}.json"


def _validate_subagent_id(subagent_id: str) -> None:
    if not SUBAGENT_ID_PATTERN.fullmatch(subagent_id) or subagent_id in {".", ".."}:
        raise SubagentTranscriptError("Invalid subagent ID.")


def _validate_store_path(path: Path) -> None:
    if path.parent.is_symlink():
        raise SubagentTranscriptError(f"Subagent transcript directory must not be a symlink: {path.parent}")
    if path.is_symlink():
        raise SubagentTranscriptError(f"Subagent transcript must not be a symlink: {path}")


def _parse_transcript(payload: object, expected_id: str) -> SubagentTranscript:
    if not isinstance(payload, dict) or payload.get("version") != TRANSCRIPT_VERSION:
        raise SubagentTranscriptError("Unsupported or malformed subagent transcript.")
    if payload.get("subagent_id") != expected_id:
        raise SubagentTranscriptError("Subagent transcript ID does not match its filename.")
    action_value = payload.get("action")
    messages_value = payload.get("messages")
    status = payload.get("status")
    runs = payload.get("runs")
    if status not in {"running", "completed", "failed", "cancelled"} or not isinstance(runs, int) or runs < 1:
        raise SubagentTranscriptError("Malformed subagent transcript metadata.")
    if not isinstance(action_value, dict) or not isinstance(messages_value, list):
        raise SubagentTranscriptError("Malformed subagent transcript content.")
    action = _parse_action(action_value)
    messages = [_parse_message(value) for value in messages_value]
    if not messages or messages[0].role != "system":
        raise SubagentTranscriptError("Subagent transcript must start with a system message.")
    return SubagentTranscript(expected_id, action, messages, status, runs)


def _parse_action(value: dict[str, object]) -> DelegateTaskAction:
    task = value.get("task")
    context = value.get("context")
    max_iterations = value.get("max_iterations")
    mode = value.get("mode")
    agent = value.get("agent")
    background = value.get("run_in_background")
    if (
        value.get("type") != "delegate_task"
        or not isinstance(task, str)
        or not task
        or context is not None and not isinstance(context, str)
        or isinstance(max_iterations, bool)
        or not isinstance(max_iterations, int)
        or not 1 <= max_iterations <= MAX_AGENT_TURNS
        or mode not in {"explore", "code"}
        or agent is not None and not isinstance(agent, str)
        or not isinstance(background, bool)
    ):
        raise SubagentTranscriptError("Malformed delegated action in transcript.")
    return DelegateTaskAction("delegate_task", task, context, max_iterations, mode, agent, background)


def _parse_message(value: object) -> ChatMessage:
    if not isinstance(value, dict) or value.get("role") not in {"system", "user", "assistant"}:
        raise SubagentTranscriptError("Malformed message in subagent transcript.")
    content = value.get("content")
    if not isinstance(content, (str, list)) or isinstance(content, list) and any(not isinstance(item, dict) for item in content):
        raise SubagentTranscriptError("Malformed message content in subagent transcript.")
    return ChatMessage(role=value["role"], content=content)  # type: ignore[arg-type]
