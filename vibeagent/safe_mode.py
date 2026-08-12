from __future__ import annotations

from collections.abc import Mapping
import os


_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def resolve_safe_mode(explicit: bool = False, env: Mapping[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return explicit or str(source.get("CLAUDE_CODE_SAFE_MODE", "")).strip().lower() in _TRUE_VALUES


__all__ = ["resolve_safe_mode"]
