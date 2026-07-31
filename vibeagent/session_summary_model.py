from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .session_utils import has_tool_call_content, model_text, parse_usage_payload


@dataclass
class SessionModelUsageTotals:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    def add_payload(self, value: Any) -> None:
        usage = parse_usage_payload(value)
        self.input_tokens += usage["input_tokens"]
        self.output_tokens += usage["output_tokens"]
        self.total_tokens += usage["total_tokens"]
        self.cache_creation_tokens += usage["cache_creation_tokens"]
        self.cache_read_tokens += usage["cache_read_tokens"]


def model_final_message(content: Any) -> str | None:
    text = model_text(content)
    if text and not has_tool_call_content(content):
        return text
    return None


def model_error_message(payload: dict[object, object]) -> str | None:
    message = payload.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()
    return None
