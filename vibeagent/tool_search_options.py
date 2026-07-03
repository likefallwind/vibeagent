from __future__ import annotations


TOOL_SEARCH_APPROVAL_CHOICES = ("any", "yes", "no")


def tool_search_approval_choices() -> tuple[str, ...]:
    return TOOL_SEARCH_APPROVAL_CHOICES


def tool_search_approval_filter(value: str) -> bool | None:
    if value == "yes":
        return True
    if value == "no":
        return False
    return None
