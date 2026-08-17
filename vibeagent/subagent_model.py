from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
import re


SUBAGENT_MODEL_ENVIRONMENT_VARIABLES = (
    "VIBEAGENT_SUBAGENT_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
)
SUBAGENT_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


@dataclass(frozen=True)
class SubagentModelSelection:
    model: str | None
    source: str


def resolve_subagent_model(
    profile_model: str | None,
    environment: Mapping[str, str] | None = None,
) -> SubagentModelSelection:
    if profile_model is not None:
        return SubagentModelSelection(
            model=None if profile_model == "inherit" else profile_model,
            source="profile",
        )
    values = os.environ if environment is None else environment
    for name in SUBAGENT_MODEL_ENVIRONMENT_VARIABLES:
        value = values.get(name, "").strip()
        if not value:
            continue
        if not SUBAGENT_MODEL_PATTERN.fullmatch(value):
            raise ValueError(f"{name} must be a valid model ID or inherit.")
        return SubagentModelSelection(
            model=None if value == "inherit" else value,
            source=name,
        )
    return SubagentModelSelection(model=None, source="parent")


__all__ = [
    "SUBAGENT_MODEL_ENVIRONMENT_VARIABLES",
    "SubagentModelSelection",
    "resolve_subagent_model",
]
