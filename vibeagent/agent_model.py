from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import time
from typing import Any

from .agent_runtime_utils import append_session_event, format_exception
from .types import AgentLogger, ChatClient, ChatMessage


def complete_with_retries(
    client: ChatClient,
    messages: list[ChatMessage],
    *,
    tools: list[dict[str, Any]] | None,
    max_output_tokens: int,
    model_retries: int,
    model_retry_delay_ms: int,
    model_timeout_ms: int,
    iteration: int,
    session_dir: Path,
    logger: AgentLogger | None,
    sleep: Callable[[float], object] | None = None,
    error_event_type: str = "model_error",
    error_event_extra: dict[str, Any] | None = None,
) -> tuple[Any | None, str | None]:
    attempts = max(0, model_retries) + 1
    sleep_fn = sleep or time.sleep
    last_message: str | None = None
    for attempt in range(1, attempts + 1):
        try:
            return client.complete(messages, tools=tools, max_tokens=max_output_tokens, timeout_ms=model_timeout_ms), None
        except Exception as error:
            will_retry = attempt < attempts
            last_message = f"Model request failed: {format_exception(error)}"
            append_session_event(
                session_dir,
                error_event_type,
                {
                    **(error_event_extra or {}),
                    "iteration": iteration,
                    "attempt": attempt,
                    "attempts": attempts,
                    "will_retry": will_retry,
                    "retry_delay_ms": model_retry_delay_ms if will_retry else 0,
                    "error_type": type(error).__name__,
                    "message": last_message,
                },
            )
            if logger:
                logger("model retry" if will_retry else "model error", last_message)
            if will_retry:
                if model_retry_delay_ms > 0:
                    sleep_fn(model_retry_delay_ms / 1000)
                continue
            return None, last_message
    return None, last_message or "Model request failed."
