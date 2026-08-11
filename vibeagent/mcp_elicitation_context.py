from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any


McpElicitationHandler = Callable[[str, dict[str, Any]], dict[str, Any]]
_HANDLER: ContextVar[McpElicitationHandler | None] = ContextVar(
    "vibeagent_mcp_elicitation_handler",
    default=None,
)


def current_mcp_elicitation_handler() -> McpElicitationHandler | None:
    return _HANDLER.get()


@contextmanager
def mcp_elicitation_handler(
    handler: McpElicitationHandler,
) -> Iterator[None]:
    token = _HANDLER.set(handler)
    try:
        yield
    finally:
        _HANDLER.reset(token)


__all__ = [
    "McpElicitationHandler",
    "current_mcp_elicitation_handler",
    "mcp_elicitation_handler",
]
