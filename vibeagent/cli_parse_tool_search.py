from __future__ import annotations

import shlex

from .cli_parse_core import parse_interactive_positive_option
from .tool_categories import valid_tool_categories


def parse_interactive_tool_search_argument(argument: str | None) -> tuple[str | None, dict[str, object], str | None]:
    usage = "Usage: /tool-search [--max N] [--category CATEGORY] [--approval any|yes|no] <query>"
    if not argument or not argument.strip():
        return None, {}, usage
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, {}, f"{usage}\n{error}"

    kwargs: dict[str, object] = {}
    query_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part in {"--max", "--category", "--approval"}:
            index += 1
            raw_value = parts[index] if index < len(parts) else None
            error = _apply_tool_search_option(part, raw_value, kwargs)
            if error:
                return None, {}, f"{usage}\n{error}"
        elif part.startswith("--max="):
            error = _apply_tool_search_option("--max", part.split("=", 1)[1], kwargs)
            if error:
                return None, {}, f"{usage}\n{error}"
        elif part.startswith("--category="):
            error = _apply_tool_search_option("--category", part.split("=", 1)[1], kwargs)
            if error:
                return None, {}, f"{usage}\n{error}"
        elif part.startswith("--approval="):
            error = _apply_tool_search_option("--approval", part.split("=", 1)[1], kwargs)
            if error:
                return None, {}, f"{usage}\n{error}"
        elif part.startswith("--"):
            return None, {}, f"{usage}\nUnknown option: {part}"
        else:
            query_parts.append(part)
        index += 1

    query = " ".join(query_parts).strip()
    if not query:
        return None, {}, usage
    return query, kwargs, None


def _apply_tool_search_option(flag: str, raw_value: str | None, kwargs: dict[str, object]) -> str | None:
    if flag == "--max":
        value, error = parse_interactive_positive_option(flag, raw_value)
        if error:
            return error
        kwargs["max_matches"] = value
        return None
    if flag == "--category":
        if raw_value is None:
            return f"{flag} requires a value."
        category = raw_value.strip()
        valid_categories = valid_tool_categories()
        if category not in valid_categories:
            return f"{flag} must be one of: {', '.join(sorted(valid_categories))}."
        kwargs["category"] = category
        return None
    if flag == "--approval":
        if raw_value is None:
            return f"{flag} requires a value."
        approval = raw_value.strip()
        if approval not in {"any", "yes", "no"}:
            return f"{flag} must be one of: any, yes, no."
        kwargs["approval_required"] = _tool_search_approval_filter(approval)
        return None
    return f"Unknown option: {flag}"


def _tool_search_approval_filter(value: str) -> bool | None:
    if value == "yes":
        return True
    if value == "no":
        return False
    return None
