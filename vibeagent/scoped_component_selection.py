from __future__ import annotations

from collections.abc import Callable


Component = dict[str, object]


def select_preferred_components(
    discovered: list[Component],
    *,
    source_priority: Callable[[str], int],
    duplicate_message: Callable[[str], str],
) -> list[Component]:
    selected: list[Component] = []
    names = sorted({str(component["name"]) for component in discovered})
    for name in names:
        matches = [component for component in discovered if str(component["name"]) == name]
        priority = min(source_priority(str(component["source"])) for component in matches)
        preferred = [
            component
            for component in matches
            if source_priority(str(component["source"])) == priority
        ]
        if len(preferred) > 1:
            for component in preferred:
                component["available"] = False
                component["message"] = duplicate_message(name)
        selected.extend(preferred)
    return selected


__all__ = ["select_preferred_components"]
