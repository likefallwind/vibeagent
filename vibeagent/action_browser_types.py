from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


BrowserActionOperation = Literal[
    "open",
    "snapshot",
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
    "screenshot",
    "close",
]


@dataclass(frozen=True)
class BrowserAction:
    type: Literal["browser"]
    operation: BrowserActionOperation
    url: str | None = None
    selector: str | None = None
    text: str | None = None
    values: tuple[str, ...] = ()
    attribute: str | None = None
    direction: str | None = None
    pixels: int | None = None
    milliseconds: int | None = None
    interactive: bool = False
    compact: bool = False
    depth: int | None = None
    path: str | None = None
    full: bool = False
    annotate: bool = False


__all__ = ["BrowserAction", "BrowserActionOperation"]
