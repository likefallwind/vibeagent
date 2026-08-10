from __future__ import annotations

import re
from typing import Any

from .action_parsing_scalars import ActionParseError
from .action_team_types import TeamCreateAction, TeamDeleteAction


TEAM_ACTION_TYPES = frozenset({"team_create", "team_delete"})
TEAM_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def parse_team_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in TEAM_ACTION_TYPES:
        return None
    if action_type == "team_delete":
        return TeamDeleteAction(type="team_delete")

    team_name = value.get("team_name")
    if not isinstance(team_name, str) or not TEAM_NAME_PATTERN.fullmatch(team_name.strip()):
        raise ActionParseError(
            "TeamCreate team_name must use 1 to 64 letters, digits, dots, underscores, or hyphens.",
            raw,
        )
    description = value.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ActionParseError("TeamCreate description must be a non-empty string.", raw)
    description = description.strip()
    if len(description) > 1_000:
        raise ActionParseError("TeamCreate description must contain at most 1000 characters.", raw)
    return TeamCreateAction(
        type="team_create",
        team_name=team_name.strip(),
        description=description,
    )


__all__ = ["TEAM_ACTION_TYPES", "TEAM_NAME_PATTERN", "parse_team_action"]
