from __future__ import annotations


TOOL_CATEGORIES = ("project", "code", "edit", "git", "command", "session", "checkpoint", "other")


def valid_tool_categories() -> tuple[str, ...]:
    return TOOL_CATEGORIES
