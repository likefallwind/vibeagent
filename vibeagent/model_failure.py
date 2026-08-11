from __future__ import annotations

from typing import Literal

from .agent_runtime_utils import format_exception
from .model_fallback import is_model_overload_error
from .redaction import redact_sensitive_text


StopFailureError = Literal[
    "rate_limit",
    "overloaded",
    "authentication_failed",
    "oauth_org_not_allowed",
    "billing_error",
    "invalid_request",
    "model_not_found",
    "server_error",
    "max_output_tokens",
    "unknown",
]


class ModelFailureMessage(str):
    error: StopFailureError
    details: str

    def __new__(
        cls,
        value: str,
        *,
        error: StopFailureError,
        details: str,
    ) -> ModelFailureMessage:
        instance = super().__new__(cls, value)
        instance.error = error
        instance.details = details
        return instance


def model_failure_message(error: Exception) -> ModelFailureMessage:
    details = redact_sensitive_text(format_exception(error))[:2_000]
    return ModelFailureMessage(
        f"Model request failed: {details}",
        error=classify_model_failure(error),
        details=details,
    )


def model_failure_fields(message: str) -> tuple[StopFailureError, str]:
    if isinstance(message, ModelFailureMessage):
        return message.error, message.details
    details = redact_sensitive_text(str(message).strip())[:2_000]
    return classify_model_failure_text(details), details


def classify_model_failure(error: BaseException) -> StopFailureError:
    statuses, text = _error_evidence(error)
    if _contains(text, "max_output_tokens", "maximum output tokens", "max output tokens"):
        return "max_output_tokens"
    if _contains(text, "oauth_org_not_allowed", "oauth organization not allowed"):
        return "oauth_org_not_allowed"
    if 401 in statuses or _contains(
        text,
        "authentication_failed",
        "authentication failed",
        "invalid api key",
        "invalid_api_key",
        "unauthorized",
    ):
        return "authentication_failed"
    if 402 in statuses or _contains(
        text,
        "billing_error",
        "billing error",
        "insufficient quota",
        "credit balance",
    ):
        return "billing_error"
    if 429 in statuses or _contains(
        text,
        "rate_limit",
        "rate limit",
        "too many requests",
    ):
        return "rate_limit"
    if _contains(text, "model_not_found", "model not found", "unknown model"):
        return "model_not_found"
    if is_model_overload_error(error):
        return "overloaded"
    if any(status >= 500 for status in statuses) or _contains(
        text,
        "server_error",
        "internal server error",
    ):
        return "server_error"
    if 400 in statuses or _contains(
        text,
        "invalid_request",
        "invalid request",
        "bad request",
        "context_length_exceeded",
        "maximum context length",
        "prompt is too long",
    ):
        return "invalid_request"
    return "unknown"


def classify_model_failure_text(value: str) -> StopFailureError:
    return classify_model_failure(RuntimeError(value))


def _error_evidence(error: BaseException) -> tuple[set[int], str]:
    statuses: set[int] = set()
    fragments: list[str] = []
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        for attribute in ("status", "status_code"):
            status = getattr(current, attribute, None)
            if isinstance(status, int):
                statuses.add(status)
        fragments.extend(
            str(value).lower()
            for value in (current, getattr(current, "response_text", ""))
            if value
        )
        current = current.__cause__ or current.__context__
    return statuses, " ".join(fragments)


def _contains(value: str, *markers: str) -> bool:
    return any(marker in value for marker in markers)


__all__ = [
    "ModelFailureMessage",
    "StopFailureError",
    "classify_model_failure",
    "classify_model_failure_text",
    "model_failure_fields",
    "model_failure_message",
]
