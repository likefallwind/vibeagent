from __future__ import annotations

from dataclasses import replace
from typing import Any

from .model_fallback_state import (
    FallbackModelRequestError,
    ModelFallbackState,
    bounded_model_error,
)
from .model_streaming import ProviderStreamHandler, complete_streaming
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


class FallbackChatClient:
    def __init__(
        self,
        primary: ChatClient,
        fallbacks: tuple[ChatClient, ...],
        state: ModelFallbackState,
    ) -> None:
        self.primary = primary
        self.fallbacks = fallbacks
        self.state = state

    @property
    def fallback(self) -> ChatClient:
        index = self.state.current_index()
        return self.fallbacks[index if index is not None else 0]

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_ms: int = 120_000,
    ) -> AssistantResponse:
        return self._complete_request(
            messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_ms=timeout_ms,
            on_event=None,
        )

    def complete_stream(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_ms: int = 120_000,
        *,
        on_event: ProviderStreamHandler,
    ) -> AssistantResponse:
        return self._complete_request(
            messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_ms=timeout_ms,
            on_event=on_event,
        )

    def _complete_request(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolSpec] | None,
        max_tokens: int,
        temperature: float,
        timeout_ms: int,
        on_event: ProviderStreamHandler | None,
    ) -> AssistantResponse:
        active_index = self.state.current_index()
        if active_index is not None:
            return self._complete_fallback(
                messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_ms=timeout_ms,
                activated_now=False,
                reason="sticky",
                start_index=active_index,
                on_event=on_event,
            )
        try:
            return _complete_client(
                self.primary,
                messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_ms=timeout_ms,
                on_event=on_event,
            )
        except Exception as error:
            if not is_model_overload_error(error):
                raise
            start_index, activated_now = self.state.activate(error)
            return self._complete_fallback(
                messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_ms=timeout_ms,
                activated_now=activated_now,
                reason="primary_overloaded",
                start_index=start_index,
                on_event=on_event,
            )

    def with_agent_profile(self, *, model: str | None, effort: str | None) -> FallbackChatClient:
        primary = _configure_client(self.primary, model=model, effort=effort)
        fallbacks = tuple(
            _configure_client(self.primary, model=fallback_model, effort=effort)
            for fallback_model in self.state.fallback_models
        )
        return FallbackChatClient(primary, fallbacks, self.state)

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
        start_index: int,
        on_event: ProviderStreamHandler | None,
    ) -> AssistantResponse:
        index = start_index
        transitions: list[dict[str, object]] = []
        while True:
            use = self.state.record_use(index)
            try:
                response = _complete_client(
                    self.fallbacks[index],
                    messages,
                    tools=tools,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout_ms=timeout_ms,
                    on_event=on_event,
                )
            except Exception as error:
                fallback_overloaded = _is_fallback_overload_error(error)
                if fallback_overloaded:
                    transitions.append(
                        {
                            "fallback_model": self.state.fallback_models[index],
                            "fallback_index": index,
                            "error": bounded_model_error(error),
                        }
                    )
                next_index = self.state.advance(index, error) if fallback_overloaded else None
                if next_index is not None:
                    index = next_index
                    activated_now = True
                    reason = "fallback_overloaded"
                    continue
                raise FallbackModelRequestError(
                    self.state.fallback_models[index],
                    error,
                    fallback_index=index,
                    fallback_models=self.state.fallback_models,
                    fallback_transitions=tuple(transitions),
                    use=use,
                    activated_now=activated_now,
                    reason=reason,
                ) from error
            break
        raw = dict(response.raw)
        raw[FALLBACK_RESPONSE_KEY] = {
            "fallback_model": self.state.fallback_models[index],
            "fallback_index": index,
            "fallback_models": list(self.state.fallback_models),
            **({"fallback_transitions": transitions} if transitions else {}),
            "fallback_use": use,
            "activated_now": activated_now,
            "reason": reason,
        }
        return replace(response, raw=raw)


def create_fallback_chat_client(
    client: ChatClient,
    fallback_model: str,
) -> tuple[FallbackChatClient, ModelFallbackState]:
    normalized = normalize_fallback_models(fallback_model)
    primary_model = getattr(client, "model", None)
    if isinstance(primary_model, str) and primary_model in normalized:
        raise ValueError("--fallback-model must differ from the primary model.")
    fallbacks = tuple(_configure_client(client, model=model, effort=None) for model in normalized)
    state = ModelFallbackState(normalized)
    return FallbackChatClient(client, fallbacks, state), state


def normalize_fallback_models(value: str) -> tuple[str, ...]:
    parts = value.split(",")
    if len(parts) > 10:
        raise ValueError("--fallback-model accepts at most 10 models.")
    normalized = tuple(normalize_fallback_model(part) for part in parts)
    if len(set(normalized)) != len(normalized):
        raise ValueError("--fallback-model cannot contain duplicate models.")
    return normalized


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
    return _has_model_overload_error(error, include_implicit_context=True)


def _is_fallback_overload_error(error: BaseException) -> bool:
    # The primary overload is the implicit context while a fallback request runs;
    # only the fallback error and explicit provider causes should advance the chain.
    return _has_model_overload_error(error, include_implicit_context=False)


def _has_model_overload_error(
    error: BaseException,
    *,
    include_implicit_context: bool,
) -> bool:
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
        current = current.__cause__ or (current.__context__ if include_implicit_context else None)
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
            "fallback_index": error.fallback_index,
            "fallback_models": list(error.fallback_models),
            "fallback_transitions": list(error.fallback_transitions),
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


def _complete_client(
    client: ChatClient,
    messages: list[ChatMessage],
    *,
    tools: list[ToolSpec] | None,
    max_tokens: int,
    temperature: float,
    timeout_ms: int,
    on_event: ProviderStreamHandler | None,
) -> AssistantResponse:
    if on_event is not None:
        return complete_streaming(
            client,
            messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_ms=timeout_ms,
            on_event=on_event,
        )
    return client.complete(
        messages,
        tools=tools,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout_ms=timeout_ms,
    )


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
    "normalize_fallback_models",
]
