from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from decimal import Decimal
from pathlib import Path

from vibeagent.agent_model import complete_with_retries
from vibeagent.config import CostRates
from vibeagent.model_budget import (
    BudgetedChatClient,
    ModelBudgetAccountingError,
    ModelBudgetExceededError,
    ModelCostBudget,
    create_model_cost_budget,
)
from vibeagent.session import summarize_session
from vibeagent.types import AssistantResponse, ChatMessage, ModelUsage


class UsageClient:
    def __init__(self, usages: list[ModelUsage]) -> None:
        self.usages = usages
        self.calls = 0

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        usage = self.usages[self.calls]
        self.calls += 1
        return AssistantResponse(content=[{"type": "text", "text": "done"}], raw={}, usage=usage)


def _rates(**overrides: Decimal | None) -> CostRates:
    values = {
        "input_usd_per_million": Decimal("1"),
        "output_usd_per_million": Decimal("2"),
        "cache_creation_usd_per_million": Decimal("3"),
        "cache_read_usd_per_million": Decimal("0.5"),
    }
    values.update(overrides)
    return CostRates(**values)


class ModelCostBudgetTests(unittest.TestCase):
    def test_report_preserves_sub_microdollar_limit(self) -> None:
        budget = ModelCostBudget(Decimal("0.0000001"), _rates())

        self.assertEqual(budget.report()["maximumUsd"], "0.0000001")

    def test_profile_clients_keep_the_same_shared_budget(self) -> None:
        class ProfileClient(UsageClient):
            def with_agent_profile(self, *, model, effort):
                return self

        inner = ProfileClient([ModelUsage(input_tokens=10, output_tokens=5, total_tokens=15)])
        budget = ModelCostBudget(Decimal("1"), _rates())
        client = BudgetedChatClient(inner, budget)

        configured = client.with_agent_profile(model="other", effort="high")
        configured.complete([])

        self.assertIs(configured.budget, budget)
        self.assertEqual(budget.usage.total_tokens, 15)

    def test_accumulates_provider_cost_below_limit(self) -> None:
        inner = UsageClient(
            [
                ModelUsage(input_tokens=100, output_tokens=20, total_tokens=120),
                ModelUsage(input_tokens=50, output_tokens=10, total_tokens=60),
            ]
        )
        budget = ModelCostBudget(Decimal("0.001"), _rates())
        client = BudgetedChatClient(inner, budget)

        client.complete([])
        client.complete([])

        self.assertIsNone(budget.failure)
        self.assertEqual(budget.estimated_cost_usd(), Decimal("0.000210"))
        self.assertEqual(budget.report()["usage"]["totalTokens"], 180)

    def test_reaching_limit_aborts_response_and_future_calls(self) -> None:
        inner = UsageClient([ModelUsage(input_tokens=100, output_tokens=50, total_tokens=150)])
        budget = ModelCostBudget(Decimal("0.0002"), _rates())
        client = BudgetedChatClient(inner, budget)

        with self.assertRaises(ModelBudgetExceededError):
            client.complete([])
        with self.assertRaises(ModelBudgetExceededError):
            client.complete([])

        self.assertEqual(inner.calls, 1)
        self.assertTrue(budget.report()["exceeded"])
        self.assertEqual(budget.report()["estimatedCostUsd"], "0.000200")

    def test_missing_or_incomplete_usage_fails_closed(self) -> None:
        cases = [
            AssistantResponse(content=[], raw={}, usage=None),
            AssistantResponse(content=[], raw={}, usage=ModelUsage(total_tokens=10)),
        ]
        for response in cases:
            class Client:
                def complete(self, *args, **kwargs):
                    return response

            with self.subTest(usage=response.usage):
                budget = ModelCostBudget(Decimal("1"), _rates())
                with self.assertRaises(ModelBudgetAccountingError):
                    BudgetedChatClient(Client(), budget).complete([])
                self.assertFalse(budget.report()["accountingAvailable"])

    def test_unpriced_reported_cache_usage_fails_closed(self) -> None:
        inner = UsageClient(
            [ModelUsage(input_tokens=10, output_tokens=2, total_tokens=12, cache_read_tokens=5)]
        )
        budget = ModelCostBudget(
            Decimal("1"),
            _rates(cache_read_usd_per_million=None),
        )

        with self.assertRaisesRegex(ModelBudgetAccountingError, "CACHE_READ"):
            BudgetedChatClient(inner, budget).complete([])

    def test_parallel_calls_share_one_strict_gate(self) -> None:
        class SlowClient(UsageClient):
            def complete(self, *args, **kwargs):
                time.sleep(0.02)
                return super().complete(*args, **kwargs)

        inner = SlowClient([ModelUsage(input_tokens=100, output_tokens=50, total_tokens=150)])
        budget = ModelCostBudget(Decimal("0.0002"), _rates())
        client = BudgetedChatClient(inner, budget)
        errors: list[Exception] = []

        def call() -> None:
            try:
                client.complete([])
            except Exception as error:
                errors.append(error)

        threads = [threading.Thread(target=call) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(inner.calls, 1)
        self.assertEqual(len(errors), 2)
        self.assertTrue(all(isinstance(error, ModelBudgetExceededError) for error in errors))

    def test_terminal_budget_error_is_not_retried_and_records_usage(self) -> None:
        inner = UsageClient([ModelUsage(input_tokens=100, output_tokens=50, total_tokens=150)])
        budget = ModelCostBudget(Decimal("0.0002"), _rates())
        with tempfile.TemporaryDirectory(prefix="vibeagent-budget-") as base:
            root = Path(base)
            session_dir = root / ".vibeagent" / "sessions" / "run-1"
            session_dir.mkdir(parents=True)
            response, error = complete_with_retries(
                BudgetedChatClient(inner, budget),
                [ChatMessage(role="user", content="inspect")],
                tools=None,
                max_output_tokens=100,
                model_retries=3,
                model_retry_delay_ms=0,
                model_timeout_ms=1_000,
                iteration=1,
                session_dir=session_dir,
                logger=None,
            )
            events = [json.loads(line) for line in (session_dir / "events.jsonl").read_text().splitlines()]
            summary = summarize_session(root, "run-1")

        self.assertIsNone(response)
        self.assertIn("Maximum model budget", error or "")
        self.assertEqual(inner.calls, 1)
        self.assertFalse(events[0]["will_retry"])
        self.assertTrue(events[0]["terminal"])
        self.assertEqual(summary.total_tokens, 150)

    def test_repeated_terminal_error_does_not_double_count_original_usage(self) -> None:
        inner = UsageClient([ModelUsage(input_tokens=100, output_tokens=50, total_tokens=150)])
        budget = ModelCostBudget(Decimal("0.0002"), _rates())
        with tempfile.TemporaryDirectory(prefix="vibeagent-budget-") as base:
            root = Path(base)
            session_dir = root / ".vibeagent" / "sessions" / "run-1"
            session_dir.mkdir(parents=True)
            client = BudgetedChatClient(inner, budget)
            for iteration in (1, 2):
                complete_with_retries(
                    client,
                    [],
                    tools=None,
                    max_output_tokens=100,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=1_000,
                    iteration=iteration,
                    session_dir=session_dir,
                    logger=None,
                )
            events = [json.loads(line) for line in (session_dir / "events.jsonl").read_text().splitlines()]
            summary = summarize_session(root, "run-1")

        self.assertIn("usage", events[0])
        self.assertNotIn("usage", events[1])
        self.assertEqual(summary.total_tokens, 150)


class ModelCostBudgetConfigTests(unittest.TestCase):
    def test_requires_input_and_output_rates_before_provider_use(self) -> None:
        with self.assertRaisesRegex(ValueError, "OUTPUT_USD"):
            create_model_cost_budget(
                Decimal("1"),
                {"VIBEAGENT_INPUT_USD_PER_MILLION": "1"},
            )

    def test_rejects_invalid_rate_configuration(self) -> None:
        with self.assertRaisesRegex(ValueError, "valid cost rates"):
            create_model_cost_budget(
                Decimal("1"),
                {
                    "VIBEAGENT_INPUT_USD_PER_MILLION": "bad",
                    "VIBEAGENT_OUTPUT_USD_PER_MILLION": "2",
                },
            )


if __name__ == "__main__":
    unittest.main()
