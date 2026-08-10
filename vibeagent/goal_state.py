from __future__ import annotations

from dataclasses import dataclass, replace
import json
import math
from pathlib import Path
import time
from typing import Literal
from uuid import uuid4

from .session_id import is_valid_session_id
from .workspace_core import RunWorkspace, create_local_workspace


GOAL_FILE = "goal.json"
GOAL_VERSION = 1
MAX_GOAL_CHARS = 4_000
MAX_GOAL_FILE_BYTES = 32_000
GoalStatus = Literal["active", "achieved", "cleared"]


class GoalStateError(ValueError):
    pass


@dataclass(frozen=True)
class GoalState:
    condition: str
    status: GoalStatus = "active"
    started_at: float = 0.0
    evaluated_turns: int = 0
    total_tokens: int = 0
    last_reason: str | None = None


def new_goal(condition: str, *, now: float | None = None) -> GoalState:
    normalized = condition.strip()
    if not normalized:
        raise GoalStateError("Goal condition must not be empty.")
    if len(normalized) > MAX_GOAL_CHARS:
        raise GoalStateError(f"Goal condition must not exceed {MAX_GOAL_CHARS} characters.")
    return GoalState(condition=normalized, started_at=time.time() if now is None else now)


def reset_restored_goal(state: GoalState, *, now: float | None = None) -> GoalState | None:
    if state.status != "active":
        return None
    return replace(
        state,
        started_at=time.time() if now is None else now,
        evaluated_turns=0,
        total_tokens=0,
        last_reason=None,
    )


def record_goal_evaluation(
    state: GoalState,
    *,
    achieved: bool,
    reason: str,
    total_tokens: int = 0,
) -> GoalState:
    if state.status != "active":
        raise GoalStateError("Only an active goal can be evaluated.")
    return replace(
        state,
        status="achieved" if achieved else "active",
        evaluated_turns=state.evaluated_turns + 1,
        total_tokens=state.total_tokens + max(0, total_tokens),
        last_reason=reason.strip()[:4_000] or "Evaluator returned no reason.",
    )


def clear_goal(state: GoalState) -> GoalState:
    return replace(state, status="cleared")


def format_goal_status(state: GoalState | None, *, now: float | None = None) -> str:
    if state is None:
        return "No goal is set."
    elapsed = max(0, int((time.time() if now is None else now) - state.started_at))
    lines = [
        f"Goal ({state.status}): {state.condition}",
        f"  elapsed: {elapsed}s",
        f"  evaluatedTurns: {state.evaluated_turns}",
        f"  totalTokens: {state.total_tokens}",
    ]
    if state.last_reason:
        lines.append(f"  lastReason: {state.last_reason}")
    return "\n".join(lines)


def goal_path(workspace: RunWorkspace) -> Path:
    return workspace.session_dir / GOAL_FILE


def read_goal(workspace: RunWorkspace) -> GoalState | None:
    path = goal_path(workspace)
    _validate_path(workspace, path)
    if not path.exists():
        return None
    if not path.is_file():
        raise GoalStateError(f"Goal state is not a regular file: {path}")
    if path.stat().st_size > MAX_GOAL_FILE_BYTES:
        raise GoalStateError(f"Goal state exceeds {MAX_GOAL_FILE_BYTES} bytes.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise GoalStateError(f"Invalid goal state: {error.msg}") from error
    return _parse_goal(payload)


def write_goal(workspace: RunWorkspace, state: GoalState) -> None:
    path = goal_path(workspace)
    _validate_path(workspace, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _validate_path(workspace, path)
    encoded = json.dumps(
        {
            "version": GOAL_VERSION,
            "condition": state.condition,
            "status": state.status,
            "startedAt": state.started_at,
            "evaluatedTurns": state.evaluated_turns,
            "totalTokens": state.total_tokens,
            "lastReason": state.last_reason,
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if len(encoded.encode("utf-8")) > MAX_GOAL_FILE_BYTES:
        raise GoalStateError(f"Goal state exceeds {MAX_GOAL_FILE_BYTES} bytes.")
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def read_session_goal(project_root: str | Path, run_id: str | None) -> GoalState | None:
    if run_id is None:
        return None
    if not is_valid_session_id(run_id):
        raise GoalStateError(f"Invalid session id for goal restore: {run_id}")
    return read_goal(create_local_workspace(project_root, run_id))


def _parse_goal(payload: object) -> GoalState:
    if not isinstance(payload, dict) or payload.get("version") != GOAL_VERSION:
        raise GoalStateError("Unsupported or malformed goal state.")
    condition = payload.get("condition")
    status = payload.get("status")
    started_at = payload.get("startedAt")
    evaluated_turns = payload.get("evaluatedTurns")
    total_tokens = payload.get("totalTokens")
    last_reason = payload.get("lastReason")
    if not isinstance(condition, str) or not condition.strip() or len(condition) > MAX_GOAL_CHARS:
        raise GoalStateError("Goal state has an invalid condition.")
    if status not in {"active", "achieved", "cleared"}:
        raise GoalStateError("Goal state has an invalid status.")
    if not _valid_timestamp(started_at):
        raise GoalStateError("Goal state has an invalid start time.")
    if not isinstance(evaluated_turns, int) or isinstance(evaluated_turns, bool) or evaluated_turns < 0:
        raise GoalStateError("Goal state has an invalid evaluated turn count.")
    if not isinstance(total_tokens, int) or isinstance(total_tokens, bool) or total_tokens < 0:
        raise GoalStateError("Goal state has an invalid token count.")
    if last_reason is not None and (not isinstance(last_reason, str) or len(last_reason) > 4_000):
        raise GoalStateError("Goal state has an invalid evaluator reason.")
    return GoalState(condition, status, float(started_at), evaluated_turns, total_tokens, last_reason)


def _valid_timestamp(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def _validate_path(workspace: RunWorkspace, path: Path) -> None:
    for candidate in (
        workspace.root / ".vibeagent",
        workspace.root / ".vibeagent" / "sessions",
        workspace.session_dir,
        path,
    ):
        if candidate.is_symlink():
            raise GoalStateError(f"Goal state path must not be a symlink: {candidate}")
