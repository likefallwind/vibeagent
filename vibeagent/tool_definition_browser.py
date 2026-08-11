from __future__ import annotations

from typing import Any


_SELECTOR = {
    "type": "string",
    "maxLength": 1000,
    "description": "Element reference from browser_snapshot such as @e3, or a CSS selector.",
}


BROWSER_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "browser_open",
        "description": (
            "Open an HTTP(S) URL in the isolated browser for this coding session. "
            "Requires approval and limits later browser navigation to the approved host."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string", "maxLength": 2048}},
            "required": ["url"],
            "additionalProperties": False,
        },
    },
    {
        "name": "browser_snapshot",
        "description": (
            "Read a bounded accessibility snapshot from the current page. Use returned @eN references "
            "for later browser_act or browser_read calls."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "interactive": {"type": "boolean", "description": "Return interactive elements only."},
                "compact": {"type": "boolean", "description": "Remove empty structural elements."},
                "depth": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "browser_act",
        "description": (
            "Perform one bounded browser interaction. Use browser_snapshot again after navigation or a "
            "substantial DOM change. Page-changing actions require approval."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "reload", "back", "forward", "click", "dblclick", "fill", "type", "press", "hover", "focus",
                        "check", "uncheck", "select", "scroll", "scroll_into_view", "wait",
                    ],
                },
                "selector": _SELECTOR,
                "text": {"type": "string", "maxLength": 8000},
                "values": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1, "maxLength": 1000},
                    "minItems": 1,
                    "maxItems": 20,
                },
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                "pixels": {"type": "integer", "minimum": 1, "maximum": 10000},
                "milliseconds": {"type": "integer", "minimum": 1, "maximum": 30000},
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    },
    {
        "name": "browser_read",
        "description": (
            "Read bounded page or element state from the isolated browser, including console and page errors. "
            "This cannot evaluate arbitrary JavaScript or access cookies and credentials."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "console", "errors", "get_text", "get_html", "get_value", "get_attribute",
                        "get_title", "get_url", "get_count", "get_box", "is_visible", "is_enabled",
                        "is_checked",
                    ],
                },
                "selector": _SELECTOR,
                "attribute": {"type": "string", "minLength": 1, "maxLength": 200},
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    },
    {
        "name": "browser_screenshot",
        "description": (
            "Capture the current page to a PNG or JPEG inside the active workspace. Requires approval, "
            "rejects protected or symlinked paths, and writes atomically."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1, "maxLength": 1000},
                "full": {"type": "boolean"},
                "annotate": {"type": "boolean"},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "browser_close",
        "description": "Close the isolated browser session and release its browser process.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


__all__ = ["BROWSER_TOOL_DEFINITIONS"]
