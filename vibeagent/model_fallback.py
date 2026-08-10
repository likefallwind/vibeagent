from __future__ import annotations

from dataclasses import dataclass, field, replace
from threading import Lock
from typing import Any

from .types import AssistantResponse, ChatClient, ChatMessage, ToolSpec


FALLBACK_RESPONSE_KEY = "_vibeagent_model_fallback"
OVERLOAD_HTTP_STATUSES = frozenset({503, 529})
OVERLOAD_MARKERS = (
    "overloaded_error",
    "overloaded",
    "over capacity",
    "service overloaded",
    "server is busy",
    "server busy",
)


@dataclass
class ModelFallbackState:
    fallback_model: str
    activated: bool = False
    uses: int = 0
    primary_overload_count: int = 0
    last_primary_error: str | None = None
    _lock: Lock = field(default_factory=Lock, repr=False)

    def is_activated(self) -> bool:
        with self._lock:
            return self.activated

    def activate(self, error: BaseException) -> bool:
        with self._lock:
            activated_now = not self.activated
            self.activated = True
            self.primary_overload_count += 1
            self.last_primary_error = _bounded_error(error)
            return activated_now

    def record_use(self) -> int:
        with self._lock:
            self.uses += 1
            return self.uses

    def report(self) -> dict[str, object]:
        with self._lock:
            return {
                "fallbackModel": self.fallback_model,
                "activated": self.activated,
                "uses": self.uses,
                "primaryOverloadCount": self.primary_overload_count,
                **({"lastPrimaryError": self.last_primary_error} if self.last_primary_error else {}),
            }


class FallbackModelRequestError(RuntimeError):
    def __init__(
        self,
        fallback_model: str,
        error: BaseException,
        *,
        use: int,
        activated_now: bool,
        reason: str,
    ) -> None:
        self.fallback_model = fallback_model
        self.fallback_error = _bounded_error(error)
        self.use = use
        self.activated_now = activated_now
        self.reason = reason
        super().__init__(f"Fallback model {fallback_model!r} request failed: {self.fallback_error}")

    def event_details(self) -> dict[str, object]:
        return {
            "fallback_model": self.fallback_model,
            "fallback_use": self.use,
            "fallback_error": self.fallback_error,
        }


class FallbackChatClient:
    def __init__(
        self,
        primary: ChatClient,
        fallback: ChatClient,
        state: ModelFallbackState,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.state = state

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_ms: int = 120_000,
    ) -> AssistantResponse:
        if self.state.is_activated():
            return self._complete_fallback(
                messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_ms=timeout_ms,
                activated_now=False,
                reason="sticky",
            )
        try:
            return self.primary.complete(
                messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_ms=timeout_ms,
            )
        except Exception as error:
            if not is_model_overload_error(error):
                raise
            activated_now = self.state.activate(error)
            return self._complete_fallback(
                messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_ms=timeout_ms,
                activated_now=activated_now,
                reason="primary_overloaded",
            )

    def with_agent_profile(self, *, model: str | None, effort: str | None) -> FallbackChatClient:
        primary = _configure_client(self.primary, model=model, effort=effort)
        fallback = _configure_client(
            self.primary,
            model=self.state.fallback_model,
            effort=effort,
        )
        return FallbackChatClient(primary, fallback, self.state)

    def _complete_fallback(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolSpec] | None,
        max_tokens: int,
        temperature: float,
        timeout_ms: int,
        activated_now: bool,
        reason: str,
    ) -> AssistantResponse:
        use = self.state.record_use()
        try:
            response = self.fallback.complete(
                messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_ms=timeout_ms,
            )
        except Exception as error:
            raise FallbackModelRequestError(
                self.state.fallback_model,
                error,
                use=use,
                activated_now=activated_now,
                reason=reason,
            ) from error
        raw = dict(response.raw)
        raw[FALLBACK_RESPONSE_KEY] = {
            "fallback_model": self.state.fallback_model,
            "fallback_use": use,
            "activated_now": activated_now,
            "reason": reason,
        }
        return replace(response, raw=raw)


def create_fallback_chat_client(
    client: ChatClient,
    fallback_model: str,
) -> tuple[FallbackChatClient, ModelFallbackState]:
    normalized = normalize_fallback_model(fallback_model)
    primary_model = getattr(client, "model", None)
    if isinstance(primary_model, str) and primary_model == normalized:
        raise ValueError("--fallback-model must differ from the primary model.")
    fallback = _configure_client(client, model=normalized, effort=None)
    state = ModelFallbackState(normalized)
    return FallbackChatClient(client, fallback, state), state


def normalize_fallback_model(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("--fallback-model cannot be empty.")
    if len(normalized) > 200:
        raise ValueError("--fallback-model must be at most 200 characters.")
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ValueError("--fallback-model cannot contain control characters.")
    return normalized


def is_model_overload_error(error: BaseException) -> bool:
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        status = getattr(current, "status", None)
        if isinstance(status, int) and status in OVERLOAD_HTTP_STATUSES:
            return True
        text = " ".join(
            str(value)
            for value in (
                current,
                getattr(current, "response_text", ""),
            )
            if value
        ).lower()
        if any(marker in text for marker in OVERLOAD_MARKERS):
            return True
        current = current.__cause__ or current.__context__
    return False


def extract_model_fallback_event(response: object) -> dict[str, object] | None:
    raw = getattr(response, "raw", None)
    if not isinstance(raw, dict):
        return None
    event = raw.get(FALLBACK_RESPONSE_KEY)
    return dict(event) if isinstance(event, dict) else None


def fallback_model_error_event_details(error: BaseException) -> dict[str, object]:
    if isinstance(error, FallbackModelRequestError):
        return error.event_details()
    return {}


def extract_model_fallback_error_event(error: BaseException) -> dict[str, object] | None:
    event = getattr(error, "model_fallback_event", None)
    if isinstance(event, dict):
        return dict(event)
    if isinstance(error, FallbackModelRequestError):
        return {
            "fallback_model": error.fallback_model,
            "fallback_use": error.use,
            "activated_now": error.activated_now,
            "reason": error.reason,
            "fallback_error": error.fallback_error,
        }
    return None


def _configure_client(client: ChatClient, *, model: str | None, effort: str | None) -> ChatClient:
    configure = getattr(client, "with_agent_profile", None)
    if not callable(configure):
        raise ValueError("The active chat client does not support --fallback-model.")
    configured: Any = configure(model=model, effort=effort)
    if configured is None or not callable(getattr(configured, "complete", None)):
        raise ValueError("The chat client returned an invalid fallback model client.")
    return configured


def _bounded_error(error: BaseException) -> str:
    text = f"{type(error).__name__}: {error}"
    return text if len(text) <= 1_000 else text[:997] + "..."


__all__ = [
    "FallbackChatClient",
    "FallbackModelRequestError",
    "ModelFallbackState",
    "create_fallback_chat_client",
    "extract_model_fallback_event",
    "extract_model_fallback_error_event",
    "fallback_model_error_event_details",
    "is_model_overload_error",
    "normalize_fallback_model",
]
