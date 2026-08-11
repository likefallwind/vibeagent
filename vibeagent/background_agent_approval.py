from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import time
from typing import Literal
from uuid import uuid4

from .background_agent_config import BackgroundAgentConfig
from .background_agent_lock import background_agent_transition_lock
from .background_agent_store import (
    background_agent_runtime_root,
    ensure_background_agent_runtime_root,
    ensure_private_directory,
    write_private_json,
    write_private_json_atomic,
)
from .background_agent_types import BACKGROUND_AGENT_ID_PATTERN
from .session_approval import SessionApprovalHandler
from .types import ApprovalDecision, ApprovalHandler, ApprovalPolicy, ApprovalRequest


APPROVAL_VERSION = 1
MAX_APPROVAL_BYTES = 32_768
MAX_APPROVAL_TEXT = 8_000


@dataclass(frozen=True)
class BackgroundApproval:
    agent_id: str
    request_id: str
    action_type: str
    target: str
    risk: str
    preview: str | None
    created_at: str


class BackgroundApprovalPrompt:
    def __init__(self, config: BackgroundAgentConfig, *, poll_interval: float = 0.1) -> None:
        self.config = config
        self.poll_interval = poll_interval

    def __call__(self, request: ApprovalRequest) -> ApprovalDecision:
        root = self.config.project_root
        agent_id = self.config.agent_id
        request_id = uuid4().hex
        approval = BackgroundApproval(
            agent_id=agent_id,
            request_id=request_id,
            action_type=request.action_type,
            target=_bounded(request.target),
            risk=_bounded(request.risk),
            preview=_bounded(request.preview) if request.preview is not None else None,
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        request_path = background_approval_request_path(root, agent_id)
        response_path = background_approval_response_path(root, agent_id)
        ensure_background_agent_runtime_root(root)
        ensure_private_directory(background_approval_root(root))
        with background_agent_transition_lock(root, agent_id):
            response_path.unlink(missing_ok=True)
            write_private_json_atomic(request_path, _request_payload(approval))
        try:
            while True:
                decision = _read_decision(response_path, approval)
                if decision is not None:
                    return decision
                time.sleep(self.poll_interval)
        finally:
            with background_agent_transition_lock(root, agent_id):
                current = read_background_approval(root, agent_id)
                if current is not None and current.request_id == request_id:
                    request_path.unlink(missing_ok=True)
                response_path.unlink(missing_ok=True)


def background_agent_approval_handler(
    config: BackgroundAgentConfig | None,
    approval_policy: ApprovalPolicy,
) -> ApprovalHandler | None:
    if config is None or approval_policy != "ask":
        return None
    return SessionApprovalHandler(BackgroundApprovalPrompt(config))


def read_background_approval(project_root: Path, agent_id: str) -> BackgroundApproval | None:
    path = background_approval_request_path(project_root.resolve(), agent_id)
    payload = _read_payload(path, label="approval request", agent_id=agent_id)
    if payload is None:
        return None
    return _parse_request(payload, agent_id)


def decide_background_approval(
    project_root: Path,
    agent_id: str,
    *,
    approved: bool,
    scope: Literal["once", "session"] = "once",
) -> BackgroundApproval:
    root = project_root.resolve()
    with background_agent_transition_lock(root, agent_id):
        approval = read_background_approval(root, agent_id)
        if approval is None:
            raise ValueError(f"Background agent is not waiting for approval: {agent_id}")
        try:
            write_private_json(
                background_approval_response_path(root, agent_id),
                {
                    "schemaVersion": APPROVAL_VERSION,
                    "agentId": agent_id,
                    "requestId": approval.request_id,
                    "approved": approved,
                    "scope": scope,
                    "message": "Approved from Agent View." if approved else "Denied from Agent View.",
                },
                exclusive=True,
            )
        except FileExistsError as error:
            raise ValueError(f"Background approval was already decided: {agent_id}") from error
    return approval


def remove_background_approval(project_root: Path, agent_id: str) -> None:
    background_approval_request_path(project_root, agent_id).unlink(missing_ok=True)
    background_approval_response_path(project_root, agent_id).unlink(missing_ok=True)


def background_approval_root(project_root: Path) -> Path:
    return background_agent_runtime_root(project_root) / "approvals"


def background_approval_request_path(project_root: Path, agent_id: str) -> Path:
    _require_agent_id(agent_id)
    return background_approval_root(project_root.resolve()) / f"{agent_id}.request.json"


def background_approval_response_path(project_root: Path, agent_id: str) -> Path:
    _require_agent_id(agent_id)
    return background_approval_root(project_root.resolve()) / f"{agent_id}.response.json"


def _request_payload(approval: BackgroundApproval) -> dict[str, object]:
    return {
        "schemaVersion": APPROVAL_VERSION,
        "agentId": approval.agent_id,
        "requestId": approval.request_id,
        "actionType": approval.action_type,
        "target": approval.target,
        "risk": approval.risk,
        "preview": approval.preview,
        "createdAt": approval.created_at,
    }


def _parse_request(payload: object, agent_id: str) -> BackgroundApproval:
    if not isinstance(payload, dict) or payload.get("schemaVersion") != APPROVAL_VERSION:
        raise ValueError(f"Invalid background approval request: {agent_id}")
    request_id = payload.get("requestId")
    action_type = payload.get("actionType")
    target = payload.get("target")
    risk = payload.get("risk")
    preview = payload.get("preview")
    created_at = payload.get("createdAt")
    if (
        payload.get("agentId") != agent_id
        or not isinstance(request_id, str)
        or len(request_id) != 32
        or any(character not in "0123456789abcdef" for character in request_id)
        or not isinstance(action_type, str)
        or not action_type
        or not isinstance(target, str)
        or not isinstance(risk, str)
        or (preview is not None and not isinstance(preview, str))
        or not isinstance(created_at, str)
        or any(len(value) > MAX_APPROVAL_TEXT for value in (action_type, target, risk, preview or "", created_at))
    ):
        raise ValueError(f"Invalid background approval request: {agent_id}")
    return BackgroundApproval(agent_id, request_id, action_type, target, risk, preview, created_at)


def _read_decision(path: Path, approval: BackgroundApproval) -> ApprovalDecision | None:
    payload = _read_payload(path, label="approval response", agent_id=approval.agent_id)
    if payload is None:
        return None
    if (
        not isinstance(payload, dict)
        or payload.get("schemaVersion") != APPROVAL_VERSION
        or payload.get("agentId") != approval.agent_id
        or payload.get("requestId") != approval.request_id
        or not isinstance(payload.get("approved"), bool)
        or payload.get("scope") not in {"once", "session"}
        or not isinstance(payload.get("message"), str)
        or len(payload["message"]) > MAX_APPROVAL_TEXT
    ):
        raise ValueError(f"Invalid background approval response: {approval.agent_id}")
    return ApprovalDecision(
        approved=payload["approved"],
        scope=payload["scope"],
        message=payload["message"],
    )


def _read_payload(path: Path, *, label: str, agent_id: str) -> object | None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Background {label} is not a regular file: {path}")
    if not path.is_file():
        return None
    try:
        if path.stat().st_size > MAX_APPROVAL_BYTES:
            raise ValueError(f"Background {label} is too large: {agent_id}")
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid background {label}: {agent_id}") from error


def _bounded(value: str) -> str:
    return value[:MAX_APPROVAL_TEXT]


def _require_agent_id(agent_id: str) -> None:
    if BACKGROUND_AGENT_ID_PATTERN.fullmatch(agent_id) is None:
        raise ValueError(f"Invalid background agent id: {agent_id}")


__all__ = [
    "BackgroundApproval",
    "BackgroundApprovalPrompt",
    "background_agent_approval_handler",
    "decide_background_approval",
    "read_background_approval",
    "remove_background_approval",
]
