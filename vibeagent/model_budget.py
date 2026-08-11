from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from threading import Lock
from typing import Any, Mapping

from .config import CostRates, resolve_cost_rates
from .model_fallback import extract_model_fallback_event
from .model_streaming import ProviderStreamHandler, complete_streaming
from .session_costs import decimal_usd_string, estimate_token_costs
from .types import AssistantResponse, ChatClient, ChatMessage, ModelUsage, ToolSpec


@dataclass
class BudgetUsage:
    sessions: int = 1
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    def add(self, usage: ModelUsage) -> None:
        input_tokens = _nonnegative(usage.input_tokens)
        output_tokens = _nonnegative(usage.output_tokens)
        total_tokens = _nonnegative(usage.total_tokens)
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens += total_tokens or input_tokens + output_tokens
        self.cache_creation_tokens += _nonnegative(usage.cache_creation_tokens)
        self.cache_read_tokens += _nonnegative(usage.cache_read_tokens)

    def to_json(self) -> dict[str, int]:
        return {
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "totalTokens": self.total_tokens,
            "cacheCreationTokens": self.cache_creation_tokens,
            "cacheReadTokens": self.cache_read_tokens,
        }


class TerminalModelRequestError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        usage: ModelUsage | None = None,
        model_fallback_event: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.usage = usage
        self.model_fallback_event = model_fallback_event

    def event_details(self) -> dict[str, object]:
        return {"terminal": True, **({"usage": _usage_payload(self.usage)} if self.usage else {})}


class ModelBudgetExceededError(TerminalModelRequestError):
    def __init__(
        self,
        *,
        maximum_usd: Decimal,
        estimated_cost_usd: Decimal,
        usage: ModelUsage | None = None,
        model_fallback_event: dict[str, object] | None = None,
    ) -> None:
        self.maximum_usd = maximum_usd
        self.estimated_cost_usd = estimated_cost_usd
        super().__init__(
            "Maximum model budget reached: estimated cost "
            f"${_budget_usd_string(estimated_cost_usd)} is at least the "
            f"${_budget_usd_string(maximum_usd)} limit.",
            usage=usage,
            model_fallback_event=model_fallback_event,
        )

    def event_details(self) -> dict[str, object]:
        return {
            **super().event_details(),
            "budget_maximum_usd": _budget_usd_string(self.maximum_usd),
            "estimated_cost_usd": _budget_usd_string(self.estimated_cost_usd),
            "budget_exceeded": True,
        }


class ModelBudgetAccountingError(TerminalModelRequestError):
    pass


class ModelCostBudget:
    def __init__(self, maximum_usd: Decimal, rates: CostRates) -> None:
        if not maximum_usd.is_finite() or maximum_usd <= 0:
            raise ValueError("--max-budget-usd must be a positive finite decimal.")
        self.maximum_usd = maximum_usd
        self.rates = rates
        self.usage = BudgetUsage()
        self._lock = Lock()
        self._failure: TerminalModelRequestError | None = None

    @property
    def failure(self) -> TerminalModelRequestError | None:
        return self._failure

    def call(
        self,
        client: ChatClient,
        messages: list[ChatMessage],
        *,
        tools: list[ToolSpec] | None,
        max_tokens: int,
        temperature: float,
        timeout_ms: int,
    ) -> AssistantResponse:
        return self._call_response(
            lambda: client.complete(
                messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_ms=timeout_ms,
            )
        )

    def call_stream(
        self,
        client: ChatClient,
        messages: list[ChatMessage],
        *,
        tools: list[ToolSpec] | None,
        max_tokens: int,
        temperature: float,
        timeout_ms: int,
        on_event: ProviderStreamHandler,
    ) -> AssistantResponse:
        return self._call_response(
            lambda: complete_streaming(
                client,
                messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_ms=timeout_ms,
                on_event=on_event,
            )
        )

    def _call_response(self, request: Callable[[], AssistantResponse]) -> AssistantResponse:
        # Strict budgets serialize provider calls so parallel subagents cannot all
        # pass a stale pre-call budget check.
        with self._lock:
            if self._failure is not None:
                raise _repeat_failure(self._failure)
            if self.estimated_cost_usd() >= self.maximum_usd:
                self._failure = ModelBudgetExceededError(
                    maximum_usd=self.maximum_usd,
                    estimated_cost_usd=self.estimated_cost_usd(),
                )
                raise self._failure
            response = request()
            usage = response.usage
            fallback_event = extract_model_fallback_event(response)
            if usage is None or not _usage_has_tokens(usage):
                self._failure = ModelBudgetAccountingError(
                    "Cannot enforce --max-budget-usd because the provider response did not include token usage.",
                    usage=usage,
                    model_fallback_event=fallback_event,
                )
                raise self._failure
            self.usage.add(usage)
            if _usage_is_incomplete(usage):
                self._failure = ModelBudgetAccountingError(
                    "Cannot enforce --max-budget-usd because provider token usage cannot be split into input and output cost.",
                    usage=usage,
                    model_fallback_event=fallback_event,
                )
                raise self._failure
            missing = _missing_reported_rates(usage, self.rates)
            if missing:
                self._failure = ModelBudgetAccountingError(
                    "Cannot enforce --max-budget-usd because reported token usage requires "
                    + ", ".join(missing)
                    + ".",
                    usage=usage,
                    model_fallback_event=fallback_event,
                )
                raise self._failure
            estimated = self.estimated_cost_usd()
            if estimated >= self.maximum_usd:
                self._failure = ModelBudgetExceededError(
                    maximum_usd=self.maximum_usd,
                    estimated_cost_usd=estimated,
                    usage=usage,
                    model_fallback_event=fallback_event,
                )
                raise self._failure
            return response

    def estimated_cost_usd(self) -> Decimal:
        return estimate_token_costs(self.usage, self.rates)["total_cost"]

    def report(self) -> dict[str, object]:
        failure = self._failure
        return {
            "maximumUsd": _budget_usd_string(self.maximum_usd),
            "estimatedCostUsd": _budget_usd_string(self.estimated_cost_usd()),
            "exceeded": isinstance(failure, ModelBudgetExceededError),
            "accountingAvailable": not isinstance(failure, ModelBudgetAccountingError),
            "usage": self.usage.to_json(),
            **({"error": str(failure)} if failure is not None else {}),
        }


class BudgetedChatClient:
    def __init__(self, client: ChatClient, budget: ModelCostBudget) -> None:
        self.client = client
        self.budget = budget

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_ms: int = 120_000,
    ) -> AssistantResponse:
        return self.budget.call(
            self.client,
            messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_ms=timeout_ms,
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
        return self.budget.call_stream(
            self.client,
            messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_ms=timeout_ms,
            on_event=on_event,
        )

    def with_agent_profile(self, *, model: str | None, effort: str | None) -> BudgetedChatClient:
        configure = getattr(self.client, "with_agent_profile", None)
        if not callable(configure):
            raise ValueError("The active chat client does not support agent profile model or effort overrides.")
        configured: Any = configure(model=model, effort=effort)
        if configured is None or not callable(getattr(configured, "complete", None)):
            raise ValueError("The chat client returned an invalid configured profile client.")
        return BudgetedChatClient(configured, self.budget)


def create_model_cost_budget(
    maximum_usd: Decimal,
    env: Mapping[str, str | None],
) -> ModelCostBudget:
    rates, errors = resolve_cost_rates(env)
    if errors:
        raise ValueError("--max-budget-usd requires valid cost rates: " + "; ".join(errors))
    missing = [
        name
        for name, value in (
            ("VIBEAGENT_INPUT_USD_PER_MILLION", rates.input_usd_per_million),
            ("VIBEAGENT_OUTPUT_USD_PER_MILLION", rates.output_usd_per_million),
        )
        if value is None
    ]
    if missing:
        raise ValueError("--max-budget-usd requires configured cost rates: " + ", ".join(missing) + ".")
    return ModelCostBudget(maximum_usd, rates)


def is_terminal_model_request_error(error: BaseException) -> bool:
    return isinstance(error, TerminalModelRequestError)


def terminal_model_error_event_details(error: BaseException) -> dict[str, object]:
    if isinstance(error, TerminalModelRequestError):
        return error.event_details()
    return {}


def _missing_reported_rates(usage: ModelUsage, rates: CostRates) -> list[str]:
    missing: list[str] = []
    if _nonnegative(usage.input_tokens) and rates.input_usd_per_million is None:
        missing.append("VIBEAGENT_INPUT_USD_PER_MILLION")
    if _nonnegative(usage.output_tokens) and rates.output_usd_per_million is None:
        missing.append("VIBEAGENT_OUTPUT_USD_PER_MILLION")
    if _nonnegative(usage.cache_creation_tokens) and rates.cache_creation_usd_per_million is None:
        missing.append("VIBEAGENT_CACHE_CREATION_USD_PER_MILLION")
    if _nonnegative(usage.cache_read_tokens) and rates.cache_read_usd_per_million is None:
        missing.append("VIBEAGENT_CACHE_READ_USD_PER_MILLION")
    return missing


def _repeat_failure(error: TerminalModelRequestError) -> TerminalModelRequestError:
    if isinstance(error, ModelBudgetExceededError):
        return ModelBudgetExceededError(
            maximum_usd=error.maximum_usd,
            estimated_cost_usd=error.estimated_cost_usd,
        )
    return ModelBudgetAccountingError(str(error))


def _usage_has_tokens(usage: ModelUsage) -> bool:
    return any(
        _nonnegative(value)
        for value in (
            usage.input_tokens,
            usage.output_tokens,
            usage.total_tokens,
            usage.cache_creation_tokens,
            usage.cache_read_tokens,
        )
    )


def _usage_is_incomplete(usage: ModelUsage) -> bool:
    total = _nonnegative(usage.total_tokens)
    if total == 0:
        return False
    input_tokens = _nonnegative(usage.input_tokens)
    output_tokens = _nonnegative(usage.output_tokens)
    return total > input_tokens + output_tokens and (
        usage.input_tokens is None or usage.output_tokens is None
    )


def _usage_payload(usage: ModelUsage) -> dict[str, int]:
    return {
        "input_tokens": _nonnegative(usage.input_tokens),
        "output_tokens": _nonnegative(usage.output_tokens),
        "total_tokens": _nonnegative(usage.total_tokens),
        "cache_creation_tokens": _nonnegative(usage.cache_creation_tokens),
        "cache_read_tokens": _nonnegative(usage.cache_read_tokens),
    }


def _nonnegative(value: int | None) -> int:
    return max(0, int(value or 0))


def _budget_usd_string(value: Decimal) -> str:
    try:
        rounded = decimal_usd_string(value)
    except InvalidOperation:
        return str(value)
    if value and rounded == "0.000000":
        return format(value, "f")
    return rounded


__all__ = [
    "BudgetedChatClient",
    "ModelBudgetAccountingError",
    "ModelBudgetExceededError",
    "ModelCostBudget",
    "TerminalModelRequestError",
    "create_model_cost_budget",
    "is_terminal_model_request_error",
    "terminal_model_error_event_details",
]
