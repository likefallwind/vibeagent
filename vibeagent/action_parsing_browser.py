from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from .action_browser_types import BrowserAction, BrowserActionOperation
from .action_parsing_helpers import ActionParseError, parse_optional_positive_int


BROWSER_ACTION_TYPES = {
    "browser_open",
    "browser_snapshot",
    "browser_act",
    "browser_read",
    "browser_screenshot",
    "browser_close",
}
BROWSER_ACT_OPERATIONS = {
    "reload",
    "back",
    "forward",
    "click",
    "dblclick",
    "fill",
    "type",
    "press",
    "hover",
    "focus",
    "check",
    "uncheck",
    "select",
    "scroll",
    "scroll_into_view",
    "wait",
}
BROWSER_READ_OPERATIONS = {
    "get_text",
    "get_html",
    "get_value",
    "get_attribute",
    "get_title",
    "get_url",
    "get_count",
    "get_box",
    "is_visible",
    "is_enabled",
    "is_checked",
    "console",
    "errors",
}
SELECTOR_OPERATIONS = {
    "click",
    "dblclick",
    "fill",
    "type",
    "hover",
    "focus",
    "check",
    "uncheck",
    "select",
    "scroll_into_view",
    "get_text",
    "get_html",
    "get_value",
    "get_attribute",
    "get_count",
    "get_box",
    "is_visible",
    "is_enabled",
    "is_checked",
}


def parse_browser_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in BROWSER_ACTION_TYPES:
        return None
    if action_type == "browser_open":
        return BrowserAction(type="browser", operation="open", url=_parse_url(value.get("url"), raw))
    if action_type == "browser_snapshot":
        return BrowserAction(
            type="browser",
            operation="snapshot",
            interactive=_boolean(value.get("interactive", False), "interactive", raw),
            compact=_boolean(value.get("compact", False), "compact", raw),
            depth=parse_optional_positive_int(value.get("depth"), "depth", raw, maximum=20),
        )
    if action_type == "browser_act":
        return _parse_browser_act(value, raw)
    if action_type == "browser_read":
        return _parse_browser_read(value, raw)
    if action_type == "browser_screenshot":
        path = _text(value.get("path"), "path", raw, maximum=1_000)
        suffix = Path(path).suffix.lower()
        if suffix and suffix not in {".png", ".jpg", ".jpeg"}:
            raise ActionParseError(
                "browser_screenshot path must have no extension or end in .png, .jpg, or .jpeg.",
                raw,
            )
        return BrowserAction(
            type="browser",
            operation="screenshot",
            path=path,
            full=_boolean(value.get("full", False), "full", raw),
            annotate=_boolean(value.get("annotate", False), "annotate", raw),
        )
    return BrowserAction(type="browser", operation="close")


def _parse_browser_act(value: dict[str, Any], raw: str) -> BrowserAction:
    operation = value.get("operation")
    if operation not in BROWSER_ACT_OPERATIONS:
        raise ActionParseError(f"browser_act operation must be one of {sorted(BROWSER_ACT_OPERATIONS)}.", raw)
    operation = cast(BrowserActionOperation, operation)
    selector = _optional_text(value.get("selector"), "selector", raw, maximum=1_000)
    text = _optional_text(value.get("text"), "text", raw, maximum=8_000, allow_empty=True)
    values = _string_array(value.get("values"), "values", raw)
    direction = _optional_text(value.get("direction"), "direction", raw, maximum=10)
    pixels = parse_optional_positive_int(value.get("pixels"), "pixels", raw, maximum=10_000)
    milliseconds = parse_optional_positive_int(value.get("milliseconds"), "milliseconds", raw, maximum=30_000)

    if operation in SELECTOR_OPERATIONS and selector is None:
        raise ActionParseError(f"browser_act {operation} requires selector.", raw)
    if operation in {"fill", "type"} and text is None:
        raise ActionParseError(f"browser_act {operation} requires text.", raw)
    if operation == "press" and text is None:
        raise ActionParseError("browser_act press requires text containing a key or key combination.", raw)
    if operation == "select" and not values:
        raise ActionParseError("browser_act select requires one or more values.", raw)
    if operation == "scroll" and direction not in {"up", "down", "left", "right"}:
        raise ActionParseError("browser_act scroll direction must be up, down, left, or right.", raw)
    if operation == "wait" and (selector is None) == (milliseconds is None):
        raise ActionParseError("browser_act wait requires exactly one of selector or milliseconds.", raw)
    return BrowserAction(
        type="browser",
        operation=operation,
        selector=selector,
        text=text,
        values=values,
        direction=direction,
        pixels=pixels,
        milliseconds=milliseconds,
    )


def _parse_browser_read(value: dict[str, Any], raw: str) -> BrowserAction:
    operation = value.get("operation")
    if operation not in BROWSER_READ_OPERATIONS:
        raise ActionParseError(f"browser_read operation must be one of {sorted(BROWSER_READ_OPERATIONS)}.", raw)
    operation = cast(BrowserActionOperation, operation)
    selector = _optional_text(value.get("selector"), "selector", raw, maximum=1_000)
    attribute = _optional_text(value.get("attribute"), "attribute", raw, maximum=200)
    if operation in SELECTOR_OPERATIONS and selector is None:
        raise ActionParseError(f"browser_read {operation} requires selector.", raw)
    if operation == "get_attribute" and attribute is None:
        raise ActionParseError("browser_read get_attribute requires attribute.", raw)
    return BrowserAction(
        type="browser",
        operation=operation,
        selector=selector,
        attribute=attribute,
    )


def _parse_url(value: object, raw: str) -> str:
    url = _text(value, "url", raw, maximum=2_048)
    try:
        parsed = urlsplit(url)
        _ = parsed.port
    except ValueError as error:
        raise ActionParseError(f"browser_open URL is invalid: {error}", raw) from error
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ActionParseError("browser_open URL must be an http or https URL with a host.", raw)
    if parsed.username is not None or parsed.password is not None:
        raise ActionParseError("browser_open URL must not contain credentials.", raw)
    return url


def _boolean(value: object, field: str, raw: str) -> bool:
    if not isinstance(value, bool):
        raise ActionParseError(f"browser field {field} must be a boolean.", raw)
    return value


def _text(value: object, field: str, raw: str, *, maximum: int) -> str:
    parsed = _optional_text(value, field, raw, maximum=maximum)
    if parsed is None:
        raise ActionParseError(f"browser field {field} must be non-empty text.", raw)
    return parsed


def _optional_text(
    value: object,
    field: str,
    raw: str,
    *,
    maximum: int,
    allow_empty: bool = False,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or "\x00" in value or len(value) > maximum:
        raise ActionParseError(f"browser field {field} must be text of at most {maximum} characters without NUL bytes.", raw)
    if not allow_empty and not value.strip():
        raise ActionParseError(f"browser field {field} must be non-empty text.", raw)
    return value


def _string_array(value: object, field: str, raw: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not value or len(value) > 20:
        raise ActionParseError(f"browser field {field} must be an array of 1 to 20 strings.", raw)
    parsed = tuple(_text(item, f"{field} item", raw, maximum=1_000) for item in value)
    return parsed


__all__ = ["BROWSER_ACTION_TYPES", "parse_browser_action"]
