from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class ModelFallbackState:
    fallback_models: tuple[str, ...]
    active_index: int | None = None
    uses: int = 0
    primary_overload_count: int = 0
    fallback_overload_count: int = 0
    last_primary_error: str | None = None
    last_fallback_error: str | None = None
    model_uses: dict[str, int] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    @property
    def fallback_model(self) -> str:
        with self._lock:
            index = self.active_index if self.active_index is not None else 0
            return self.fallback_models[index]

    def current_index(self) -> int | None:
        with self._lock:
            return self.active_index

    def activate(self, error: BaseException) -> tuple[int, bool]:
        with self._lock:
            activated_now = self.active_index is None
            if self.active_index is None:
                self.active_index = 0
            self.primary_overload_count += 1
            self.last_primary_error = bounded_model_error(error)
            return self.active_index, activated_now

    def advance(self, index: int, error: BaseException) -> int | None:
        with self._lock:
            self.fallback_overload_count += 1
            self.last_fallback_error = bounded_model_error(error)
            current = self.active_index if self.active_index is not None else index
            if current > index:
                return current
            next_index = index + 1
            if next_index >= len(self.fallback_models):
                return None
            self.active_index = next_index
            return next_index

    def record_use(self, index: int) -> int:
        with self._lock:
            self.uses += 1
            model = self.fallback_models[index]
            self.model_uses[model] = self.model_uses.get(model, 0) + 1
            return self.uses

    def report(self) -> dict[str, object]:
        with self._lock:
            active_model = (
                self.fallback_models[self.active_index]
                if self.active_index is not None
                else None
            )
            return {
                "fallbackModel": active_model or self.fallback_models[0],
                "fallbackModels": list(self.fallback_models),
                "activated": self.active_index is not None,
                "uses": self.uses,
                "primaryOverloadCount": self.primary_overload_count,
                "fallbackOverloadCount": self.fallback_overload_count,
                "modelUses": {
                    model: self.model_uses.get(model, 0)
                    for model in self.fallback_models
                },
                **({"activeFallbackModel": active_model} if active_model else {}),
                **({"activeFallbackIndex": self.active_index} if self.active_index is not None else {}),
                **({"lastPrimaryError": self.last_primary_error} if self.last_primary_error else {}),
                **({"lastFallbackError": self.last_fallback_error} if self.last_fallback_error else {}),
            }


class FallbackModelRequestError(RuntimeError):
    def __init__(
        self,
        fallback_model: str,
        error: BaseException,
        *,
        fallback_index: int,
        fallback_models: tuple[str, ...],
        fallback_transitions: tuple[dict[str, object], ...],
        use: int,
        activated_now: bool,
        reason: str,
    ) -> None:
        self.fallback_model = fallback_model
        self.fallback_error = bounded_model_error(error)
        self.fallback_index = fallback_index
        self.fallback_models = fallback_models
        self.fallback_transitions = fallback_transitions
        self.use = use
        self.activated_now = activated_now
        self.reason = reason
        super().__init__(f"Fallback model {fallback_model!r} request failed: {self.fallback_error}")

    def event_details(self) -> dict[str, object]:
        return {
            "fallback_model": self.fallback_model,
            "fallback_index": self.fallback_index,
            "fallback_models": list(self.fallback_models),
            "fallback_transitions": list(self.fallback_transitions),
            "fallback_use": self.use,
            "fallback_error": self.fallback_error,
        }


def bounded_model_error(error: BaseException) -> str:
    text = f"{type(error).__name__}: {error}"
    return text if len(text) <= 1_000 else text[:997] + "..."


__all__ = ["FallbackModelRequestError", "ModelFallbackState", "bounded_model_error"]
