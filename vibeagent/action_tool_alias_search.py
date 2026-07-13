from __future__ import annotations

from typing import Any

from .action_tool_alias_utils import rename_fields


def normalize_search_input(value: dict[str, Any]) -> dict[str, Any]:
    normalized = rename_fields(value, {"pattern": "query", "head_limit": "max_matches", "glob": "file_glob"})
    if normalized.pop("-i", False) is True and "case_sensitive" not in normalized:
        normalized["case_sensitive"] = False
    _normalize_search_context_aliases(normalized)
    if normalized.get("output_mode") == "content" and "context_lines" not in normalized:
        normalized["context_lines"] = 2
    return normalized


def _normalize_search_context_aliases(value: dict[str, Any]) -> None:
    context = value.pop("-C", None)
    after = value.pop("-A", None)
    before = value.pop("-B", None)
    if "context_lines" in value:
        return
    if type(context) is int:
        value["context_lines"] = context
        return
    directional = [item for item in (after, before) if type(item) is int]
    if directional:
        value["context_lines"] = max(directional)
