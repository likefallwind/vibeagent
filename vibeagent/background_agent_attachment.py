from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Literal

from .background_agent_store import (
    background_agent_runtime_root,
    ensure_background_agent_runtime_root,
    ensure_private_directory,
    write_private_json,
    write_private_json_atomic,
)
from .background_agent_types import BACKGROUND_AGENT_ID_PATTERN
from .process_registry import read_process_start_ticks


ATTACHMENT_VERSION = 1
MAX_ATTACHMENT_BYTES = 16_384
AttachmentState = Literal["attaching", "attached"]


@dataclass(frozen=True)
class BackgroundAgentAttachment:
    agent_id: str
    pid: int
    start_ticks: int | None
    state: AttachmentState
    created_at: str


def claim_background_agent_attachment(
    project_root: Path,
    agent_id: str,
    *,
    waiting_for_worker: bool,
) -> BackgroundAgentAttachment:
    root = project_root.resolve()
    existing = read_background_agent_attachment(root, agent_id)
    if existing is not None:
        raise ValueError(
            f"Background agent is already {existing.state} in another terminal: {agent_id}"
        )
    ensure_background_agent_runtime_root(root)
    ensure_private_directory(background_agent_attachment_root(root))
    attachment = BackgroundAgentAttachment(
        agent_id=agent_id,
        pid=os.getpid(),
        start_ticks=read_process_start_ticks(os.getpid()),
        state="attaching" if waiting_for_worker else "attached",
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    write_private_json(
        background_agent_attachment_path(root, agent_id),
        _attachment_payload(attachment),
        exclusive=True,
    )
    return attachment


def activate_background_agent_attachment(
    project_root: Path,
    agent_id: str,
) -> BackgroundAgentAttachment:
    root = project_root.resolve()
    attachment = _require_current_attachment(root, agent_id)
    updated = replace(attachment, state="attached")
    write_private_json_atomic(
        background_agent_attachment_path(root, agent_id),
        _attachment_payload(updated),
    )
    return updated


def release_background_agent_attachment(project_root: Path, agent_id: str) -> None:
    root = project_root.resolve()
    attachment = read_background_agent_attachment(root, agent_id)
    if attachment is None:
        return
    if (
        attachment.pid != os.getpid()
        or attachment.start_ticks != read_process_start_ticks(os.getpid())
    ):
        raise ValueError(f"Background agent attachment belongs to another terminal: {agent_id}")
    background_agent_attachment_path(root, agent_id).unlink(missing_ok=True)


def read_background_agent_attachment(
    project_root: Path,
    agent_id: str,
) -> BackgroundAgentAttachment | None:
    root = project_root.resolve()
    path = background_agent_attachment_path(root, agent_id)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Background agent attachment is not a regular file: {path}")
    if not path.is_file():
        return None
    try:
        if path.stat().st_size > MAX_ATTACHMENT_BYTES:
            raise ValueError(f"Background agent attachment is too large: {agent_id}")
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid background agent attachment: {agent_id}") from error
    attachment = _parse_attachment(payload, agent_id)
    if _attachment_process_running(attachment):
        return attachment
    path.unlink(missing_ok=True)
    return None


def background_agent_attachment_root(project_root: Path) -> Path:
    return background_agent_runtime_root(project_root) / "attachments"


def background_agent_attachment_path(project_root: Path, agent_id: str) -> Path:
    _require_agent_id(agent_id)
    return background_agent_attachment_root(project_root) / f"{agent_id}.json"


def _require_current_attachment(
    project_root: Path,
    agent_id: str,
) -> BackgroundAgentAttachment:
    attachment = read_background_agent_attachment(project_root, agent_id)
    if attachment is None:
        raise ValueError(f"Background agent attachment was lost: {agent_id}")
    if (
        attachment.pid != os.getpid()
        or attachment.start_ticks != read_process_start_ticks(os.getpid())
    ):
        raise ValueError(f"Background agent attachment belongs to another terminal: {agent_id}")
    return attachment


def _attachment_payload(attachment: BackgroundAgentAttachment) -> dict[str, object]:
    return {
        "schemaVersion": ATTACHMENT_VERSION,
        "agentId": attachment.agent_id,
        "pid": attachment.pid,
        "startTicks": attachment.start_ticks,
        "state": attachment.state,
        "createdAt": attachment.created_at,
    }


def _parse_attachment(payload: object, agent_id: str) -> BackgroundAgentAttachment:
    if not isinstance(payload, dict) or payload.get("schemaVersion") != ATTACHMENT_VERSION:
        raise ValueError(f"Invalid background agent attachment: {agent_id}")
    pid = payload.get("pid")
    start_ticks = payload.get("startTicks")
    state = payload.get("state")
    created_at = payload.get("createdAt")
    if (
        payload.get("agentId") != agent_id
        or not isinstance(pid, int)
        or isinstance(pid, bool)
        or pid <= 0
        or (
            start_ticks is not None
            and (not isinstance(start_ticks, int) or isinstance(start_ticks, bool))
        )
        or state not in {"attaching", "attached"}
        or not isinstance(created_at, str)
        or not created_at
    ):
        raise ValueError(f"Invalid background agent attachment: {agent_id}")
    return BackgroundAgentAttachment(
        agent_id=agent_id,
        pid=pid,
        start_ticks=start_ticks,
        state=state,
        created_at=created_at,
    )


def _attachment_process_running(attachment: BackgroundAgentAttachment) -> bool:
    try:
        os.kill(attachment.pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return (
        attachment.start_ticks is None
        or read_process_start_ticks(attachment.pid) == attachment.start_ticks
    )


def _require_agent_id(agent_id: str) -> None:
    if BACKGROUND_AGENT_ID_PATTERN.fullmatch(agent_id) is None:
        raise ValueError(f"Invalid background agent id: {agent_id}")


__all__ = [
    "BackgroundAgentAttachment",
    "activate_background_agent_attachment",
    "background_agent_attachment_path",
    "claim_background_agent_attachment",
    "read_background_agent_attachment",
    "release_background_agent_attachment",
]
