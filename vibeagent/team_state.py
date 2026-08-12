from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from uuid import uuid4

from .action_parsing_team import TEAM_NAME_PATTERN
from .workspace_core import RunWorkspace


TEAM_STATE_FILE = "team.json"
TEAM_STATE_VERSION = 1
TEAM_STATE_MAX_BYTES = 8_192


class TeamStateError(ValueError):
    pass


@dataclass(frozen=True)
class TeamState:
    name: str
    description: str
    explicit: bool
    created_at: str


def team_state_path(workspace: RunWorkspace) -> Path:
    return workspace.session_dir / TEAM_STATE_FILE


def read_team_state(workspace: RunWorkspace) -> TeamState | None:
    path = team_state_path(workspace)
    if path.is_symlink():
        raise TeamStateError(f"Team state must not be a symlink: {path}")
    if not path.exists():
        return None
    if not path.is_file():
        raise TeamStateError(f"Team state is not a regular file: {path}")
    if path.stat().st_size > TEAM_STATE_MAX_BYTES:
        raise TeamStateError(f"Team state exceeds {TEAM_STATE_MAX_BYTES} bytes.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise TeamStateError(f"Invalid team state: {error}") from error
    return _parse_team_state(value)


def create_team_state(
    workspace: RunWorkspace,
    name: str,
    description: str,
    *,
    explicit: bool,
) -> TeamState:
    existing = read_team_state(workspace)
    if existing is not None:
        raise TeamStateError(f"Session already has team {existing.name}; delete it before creating another.")
    state = TeamState(
        name=name,
        description=description,
        explicit=explicit,
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    _write_team_state(workspace, state)
    return state


def ensure_implicit_team_state(workspace: RunWorkspace) -> tuple[TeamState, bool]:
    existing = read_team_state(workspace)
    if existing is not None:
        return existing, False
    return (
        create_team_state(
            workspace,
            implicit_team_name(workspace),
            "Session team created automatically for named Agent teammates.",
            explicit=False,
        ),
        True,
    )


def implicit_team_name(workspace: RunWorkspace) -> str:
    prefix = "".join(
        character if character.isalnum() else "-"
        for character in workspace.run_id[:8]
    ).strip("-")
    return f"session-{prefix or 'agent'}"


def delete_team_state(workspace: RunWorkspace) -> TeamState | None:
    state = read_team_state(workspace)
    if state is None:
        return None
    try:
        team_state_path(workspace).unlink()
    except OSError as error:
        raise TeamStateError(f"Could not delete team state: {error}") from error
    return state


def _write_team_state(workspace: RunWorkspace, state: TeamState) -> None:
    path = team_state_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise TeamStateError(f"Team state must not be a symlink: {path}")
    payload = {
        "version": TEAM_STATE_VERSION,
        "name": state.name,
        "description": state.description,
        "explicit": state.explicit,
        "createdAt": state.created_at,
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(encoded.encode("utf-8")) > TEAM_STATE_MAX_BYTES:
        raise TeamStateError(f"Team state exceeds {TEAM_STATE_MAX_BYTES} bytes.")
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(encoded, encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _parse_team_state(value: object) -> TeamState:
    if not isinstance(value, dict) or value.get("version") != TEAM_STATE_VERSION:
        raise TeamStateError("Unsupported or malformed team state.")
    name = value.get("name")
    description = value.get("description")
    explicit = value.get("explicit")
    created_at = value.get("createdAt")
    if not isinstance(name, str) or TEAM_NAME_PATTERN.fullmatch(name) is None:
        raise TeamStateError("Team state has an invalid name.")
    if not isinstance(description, str) or not description or len(description) > 1_000:
        raise TeamStateError("Team state has an invalid description.")
    if not isinstance(explicit, bool):
        raise TeamStateError("Team state has an invalid explicit flag.")
    if not isinstance(created_at, str) or not created_at or len(created_at) > 100:
        raise TeamStateError("Team state has an invalid creation time.")
    return TeamState(name=name, description=description, explicit=explicit, created_at=created_at)


__all__ = [
    "implicit_team_name",
    "TeamState",
    "TeamStateError",
    "create_team_state",
    "delete_team_state",
    "ensure_implicit_team_state",
    "read_team_state",
    "team_state_path",
]
