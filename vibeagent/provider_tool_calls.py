from __future__ import annotations

import json
from typing import Any

from .types import ContentBlock


def parse_function_tool_call(value: Any) -> ContentBlock | None:
    if not isinstance(value, dict) or not isinstance(value.get("id"), str):
        return None
    function = value.get("function")
    if not isinstance(function, dict) or not isinstance(function.get("name"), str):
        return None
    return {
        "type": "tool_call",
        "id": value["id"],
        "name": function["name"],
        "input": parse_function_arguments(function.get("arguments", "{}")),
    }


def parse_function_arguments(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value or "{}")
        except json.JSONDecodeError:
            return value
    return value
