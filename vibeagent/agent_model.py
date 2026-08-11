from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import time
from typing import Any

from .agent_runtime_utils import append_session_event, format_exception
from .model_budget import is_terminal_model_request_error, terminal_model_error_event_details
from .model_fallback import (
    extract_model_fallback_error_event,
    extract_model_fallback_event,
    fallback_model_error_event_details,
)
from .model_failure import ModelFailureMessage, model_failure_message
from .types import AgentLogger, ChatClient, ChatMessage


ContextRecovery = Callable[[], bool]
CONTEXT_LIMIT_ERROR_MARKERS = (
    "context_length_exceeded",
    "maximum context length",
    "context window",
    "prompt is too long",
    "too many input tokens",
    "input tokens exceed",
    "input token count exceeds",
)


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
    recover_context: ContextRecovery | None = None,
) -> tuple[Any | None, ModelFailureMessage | None]:
    attempt_budget = max(0, model_retries) + 1
    remaining_retries = max(0, model_retries)
    context_recovery_available = recover_context is not None
    sleep_fn = sleep or time.sleep
    last_message: ModelFailureMessage | None = None
    attempt = 0
    while attempt < attempt_budget:
        attempt += 1
        try:
            response = client.complete(messages, tools=tools, max_tokens=max_output_tokens, timeout_ms=model_timeout_ms)
            fallback_event = extract_model_fallback_event(response)
            if fallback_event is not None:
                append_session_event(
                    session_dir,
                    "model_fallback",
                    {"iteration": iteration, "attempt": attempt, **fallback_event},
                )
            return response, None
        except Exception as error:
            fallback_error_event = extract_model_fallback_error_event(error)
            if fallback_error_event is not None:
                append_session_event(
                    session_dir,
                    "model_fallback",
                    {"iteration": iteration, "attempt": attempt, **fallback_error_event},
                )
            recovered_context = False
            context_recovery_error: str | None = None
            terminal_error = is_terminal_model_request_error(error)
            if not terminal_error and context_recovery_available and is_context_limit_error(error):
                context_recovery_available = False
                try:
                    recovered_context = bool(recover_context and recover_context())
                except Exception as recovery_error:
                    context_recovery_error = format_exception(recovery_error)
                if recovered_context:
                    attempt_budget += 1
            use_regular_retry = not terminal_error and not recovered_context and remaining_retries > 0
            if use_regular_retry:
                remaining_retries -= 1
            will_retry = recovered_context or use_regular_retry
            retry_reason = "context_compaction" if recovered_context else ("transient_error" if use_regular_retry else None)
            last_message = model_failure_message(error)
            append_session_event(
                session_dir,
                error_event_type,
                {
                    **(error_event_extra or {}),
                    "iteration": iteration,
                    "attempt": attempt,
                    "attempts": attempt_budget,
                    "will_retry": will_retry,
                    "retry_delay_ms": model_retry_delay_ms if use_regular_retry else 0,
                    **({"retry_reason": retry_reason} if retry_reason else {}),
                    **({"context_recovery_error": context_recovery_error} if context_recovery_error else {}),
                    "error_type": type(error).__name__,
                    "message": last_message,
                    **terminal_model_error_event_details(error),
                    **fallback_model_error_event_details(error),
                },
            )
            if logger:
                logger("model retry" if will_retry else "model error", last_message)
            if will_retry:
                if use_regular_retry and model_retry_delay_ms > 0:
                    sleep_fn(model_retry_delay_ms / 1000)
                continue
            return None, last_message
    return None, last_message or ModelFailureMessage(
        "Model request failed.",
        error="unknown",
        details="Model request failed.",
    )


def is_context_limit_error(error: Exception) -> bool:
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        text = str(current).lower()
        if any(marker in text for marker in CONTEXT_LIMIT_ERROR_MARKERS):
            return True
        current = current.__cause__ or current.__context__
    return False
