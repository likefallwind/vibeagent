from __future__ import annotations

import json
from pathlib import Path
import re
import time
from uuid import uuid4

from .background_agent_config import BackgroundAgentConfig
from .background_agent_store import (
    background_agent_runtime_root,
    ensure_private_directory,
    write_private_json,
)
from .background_agent_types import BACKGROUND_AGENT_ID_PATTERN


MAX_BACKGROUND_AGENT_MESSAGE_BYTES = 16 * 1024
MAX_BACKGROUND_AGENT_MESSAGE_CHARS = 4_000
_MESSAGE_NAME_PATTERN = re.compile(r"^[0-9]{20}-[0-9a-f]{12}\.json$")


def enqueue_background_agent_message(
    config: BackgroundAgentConfig,
    message: str,
) -> Path:
    normalized = normalize_background_agent_message(message)
    inbox = ensure_private_directory(
        background_agent_inbox_path(config.project_root, config.agent_id)
    )
    path = inbox / f"{time.time_ns():020d}-{uuid4().hex[:12]}.json"
    write_private_json(
        path,
        {
            "schemaVersion": 1,
            "agentId": config.agent_id,
            "message": normalized,
        },
        exclusive=True,
    )
    return path


def next_background_agent_message(
    config: BackgroundAgentConfig,
) -> tuple[Path, str] | None:
    inbox = background_agent_inbox_path(config.project_root, config.agent_id)
    if inbox.is_symlink() or not inbox.is_dir():
        return None
    for path in sorted(inbox.iterdir()):
        if not _MESSAGE_NAME_PATTERN.fullmatch(path.name):
            continue
        try:
            return path, read_background_agent_message(config, path)
        except ValueError:
            path.unlink(missing_ok=True)
    return None


def read_background_agent_message(
    config: BackgroundAgentConfig,
    path: Path,
) -> str:
    inbox = background_agent_inbox_path(config.project_root, config.agent_id)
    if path.parent != inbox or not _MESSAGE_NAME_PATTERN.fullmatch(path.name):
        raise ValueError("Background agent message path escapes its inbox.")
    if path.is_symlink() or not path.is_file():
        raise ValueError("Background agent message is not a regular file.")
    try:
        if path.stat().st_size > MAX_BACKGROUND_AGENT_MESSAGE_BYTES:
            raise ValueError("Background agent message is too large.")
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid background agent message.") from error
    if (
        not isinstance(payload, dict)
        or payload.get("schemaVersion") != 1
        or payload.get("agentId") != config.agent_id
        or not isinstance(payload.get("message"), str)
    ):
        raise ValueError("Invalid background agent message.")
    return normalize_background_agent_message(payload["message"])


def pending_background_agent_message_count(project_root: Path, agent_id: str) -> int:
    inbox = background_agent_inbox_path(project_root.resolve(), agent_id)
    if inbox.is_symlink() or not inbox.is_dir():
        return 0
    return sum(
        1
        for path in inbox.iterdir()
        if _MESSAGE_NAME_PATTERN.fullmatch(path.name)
        and path.is_file()
        and not path.is_symlink()
    )


def remove_background_agent_inbox(project_root: Path, agent_id: str) -> None:
    inbox = background_agent_inbox_path(project_root.resolve(), agent_id)
    if inbox.is_symlink():
        inbox.unlink(missing_ok=True)
        return
    if not inbox.is_dir():
        return
    for path in inbox.iterdir():
        if path.is_file() or path.is_symlink():
            path.unlink(missing_ok=True)
    inbox.rmdir()


def background_agent_inbox_path(project_root: Path, agent_id: str) -> Path:
    if BACKGROUND_AGENT_ID_PATTERN.fullmatch(agent_id) is None:
        raise ValueError(f"Invalid background agent id: {agent_id}")
    return background_agent_runtime_root(project_root) / "inbox" / agent_id


def normalize_background_agent_message(message: str) -> str:
    normalized = message.strip()
    if not normalized:
        raise ValueError("Background agent message must not be empty.")
    if len(normalized) > MAX_BACKGROUND_AGENT_MESSAGE_CHARS:
        raise ValueError(
            f"Background agent message must not exceed {MAX_BACKGROUND_AGENT_MESSAGE_CHARS} characters."
        )
    return normalized


__all__ = [
    "MAX_BACKGROUND_AGENT_MESSAGE_CHARS",
    "background_agent_inbox_path",
    "enqueue_background_agent_message",
    "next_background_agent_message",
    "normalize_background_agent_message",
    "pending_background_agent_message_count",
    "read_background_agent_message",
    "remove_background_agent_inbox",
]
