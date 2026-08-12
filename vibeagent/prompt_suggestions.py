from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Callable

from .agent_model import complete_with_retries
from .agent_runtime_utils import (
    append_session_event,
    content_blocks_to_text,
    format_exception,
    normalize_assistant_content,
    to_jsonable,
)
from .redaction import redact_sensitive_text
from .types import AgentLogger, ChatClient, ChatMessage


MAX_PROMPT_SUGGESTION_CHARS = 1_000
PROMPT_SUGGESTION_MAX_TOKENS = 256
_UNSAFE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass(frozen=True)
class PromptSuggestionResult:
    suggestion: str | None
    error: str | None

    @property
    def success(self) -> bool:
        return self.suggestion is not None and self.error is None


def generate_prompt_suggestion(
    client: ChatClient,
    conversation: list[ChatMessage],
    *,
    session_dir: Path,
    model_timeout_ms: int,
    iteration: int,
    logger: AgentLogger | None = None,
    complete_func: Callable[..., tuple[Any | None, object | None]] = complete_with_retries,
) -> PromptSuggestionResult:
    if not conversation:
        return _record_result(session_dir, None, "Prompt suggestion requires conversation context.")
    messages = [*conversation, ChatMessage(role="user", content=_suggestion_request())]
    response, model_error = complete_func(
        client,
        messages,
        tools=None,
        max_output_tokens=PROMPT_SUGGESTION_MAX_TOKENS,
        model_retries=0,
        model_retry_delay_ms=0,
        model_timeout_ms=model_timeout_ms,
        iteration=iteration + 1,
        session_dir=session_dir,
        logger=logger,
        error_event_type="prompt_suggestion_model_error",
    )
    if response is None:
        return _record_result(
            session_dir,
            None,
            str(model_error or "Prompt suggestion model request failed."),
        )

    content = normalize_assistant_content(response.content if hasattr(response, "content") else response)
    usage = getattr(response, "usage", None)
    append_session_event(
        session_dir,
        "prompt_suggestion_model",
        {
            "content": content,
            **({"usage": to_jsonable(usage)} if usage is not None else {}),
        },
    )
    suggestion, error = normalize_prompt_suggestion(content_blocks_to_text(content))
    return _record_result(session_dir, suggestion, error)


def try_generate_prompt_suggestion(
    client: ChatClient,
    conversation: list[ChatMessage],
    *,
    session_dir: Path,
    model_timeout_ms: int,
    iteration: int,
    logger: AgentLogger | None = None,
) -> PromptSuggestionResult:
    try:
        return generate_prompt_suggestion(
            client,
            conversation,
            session_dir=session_dir,
            model_timeout_ms=model_timeout_ms,
            iteration=iteration,
            logger=logger,
        )
    except Exception as error:
        message = f"Prompt suggestion generation failed: {format_exception(error)}"
        try:
            return _record_result(session_dir, None, message)
        except Exception:
            return PromptSuggestionResult(suggestion=None, error=message)


def normalize_prompt_suggestion(value: str) -> tuple[str | None, str | None]:
    suggestion = redact_sensitive_text(" ".join(value.strip().splitlines()).strip())
    if not suggestion:
        return None, "Prompt suggestion was empty."
    if _UNSAFE_CONTROL.search(suggestion):
        return None, "Prompt suggestion contained unsafe control characters."
    if len(suggestion) > MAX_PROMPT_SUGGESTION_CHARS:
        return None, f"Prompt suggestion exceeded {MAX_PROMPT_SUGGESTION_CHARS} characters."
    return suggestion, None


def _suggestion_request() -> str:
    return "\n".join(
        [
            "Predict one useful next prompt the user could send after this completed coding turn.",
            "Return only that prompt as plain text, in the user's language.",
            "Keep it concise, concrete, and grounded in the established conversation.",
            "Do not answer the prompt, use tools, add quotation marks, or include commentary.",
        ]
    )


def _record_result(
    session_dir: Path,
    suggestion: str | None,
    error: str | None,
) -> PromptSuggestionResult:
    append_session_event(
        session_dir,
        "prompt_suggestion_result",
        {
            "success": error is None and suggestion is not None,
            **({"suggestion": suggestion} if suggestion is not None else {}),
            **({"error": error} if error is not None else {}),
        },
    )
    return PromptSuggestionResult(suggestion=suggestion, error=error)


__all__ = [
    "MAX_PROMPT_SUGGESTION_CHARS",
    "PROMPT_SUGGESTION_MAX_TOKENS",
    "PromptSuggestionResult",
    "generate_prompt_suggestion",
    "normalize_prompt_suggestion",
    "try_generate_prompt_suggestion",
]
