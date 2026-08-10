from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from vibeagent.cli import main
from vibeagent.runtime_types import AssistantResponse, ModelUsage


class UsageTextClient:
    def __init__(self, usage: ModelUsage) -> None:
        self.usage = usage
        self.calls = 0

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.calls += 1
        return AssistantResponse(
            content=[{"type": "text", "text": "Inspected the project."}],
            raw={},
            usage=self.usage,
        )


class UsageSequenceClient:
    def __init__(self, responses: list[tuple[list[dict[str, object]], ModelUsage]]) -> None:
        self.responses = responses
        self.calls = 0

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        content, usage = self.responses[self.calls]
        self.calls += 1
        return AssistantResponse(content=content, raw={}, usage=usage)


class CliModelBudgetTests(unittest.TestCase):
    def test_max_budget_is_shared_with_structured_output_formatter(self) -> None:
        client = UsageSequenceClient(
            [
                (
                    [{"type": "text", "text": "Inspected the project."}],
                    ModelUsage(input_tokens=50, output_tokens=0, total_tokens=50),
                ),
                (
                    [{"type": "text", "text": '{"summary":"inspected"}'}],
                    ModelUsage(input_tokens=50, output_tokens=50, total_tokens=100),
                ),
            ]
        )
        schema = json.dumps(
            {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            }
        )
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory(prefix="vibeagent-budget-structured-") as base:
            with (
                patch("vibeagent.cli.create_chat_client", return_value=client),
                patch.dict(
                    os.environ,
                    {
                        "VIBEAGENT_INPUT_USD_PER_MILLION": "1",
                        "VIBEAGENT_OUTPUT_USD_PER_MILLION": "2",
                    },
                    clear=True,
                ),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "-p",
                        "--output-format",
                        "json",
                        "--json-schema",
                        schema,
                        "--max-budget-usd",
                        "0.0002",
                        "--cwd",
                        base,
                        "inspect",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(client.calls, 2)
        self.assertEqual(payload["subtype"], "error_max_budget_usd")
        self.assertEqual(payload["totalCostUsd"], "0.000200")
        self.assertNotIn("structured_output", payload)

    def test_max_budget_requires_rates_before_client_creation(self) -> None:
        create_client = Mock()
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory(prefix="vibeagent-budget-rates-") as base:
            with (
                patch("vibeagent.cli.create_chat_client", create_client),
                patch.dict(os.environ, {}, clear=True),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    ["-p", "--output-format", "json", "--max-budget-usd", "1", "--cwd", base, "inspect"]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertIn("requires configured cost rates", payload["error"])
        create_client.assert_not_called()

    def test_max_budget_cli_reports_success_below_limit(self) -> None:
        client = UsageTextClient(ModelUsage(input_tokens=100, output_tokens=50, total_tokens=150))
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory(prefix="vibeagent-budget-cli-") as base:
            with (
                patch("vibeagent.cli.create_chat_client", return_value=client),
                patch.dict(
                    os.environ,
                    {
                        "VIBEAGENT_INPUT_USD_PER_MILLION": "1",
                        "VIBEAGENT_OUTPUT_USD_PER_MILLION": "2",
                    },
                    clear=True,
                ),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    ["-p", "--output-format", "json", "--max-budget-usd", "0.001", "--cwd", base, "inspect"]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["subtype"], "success")
        self.assertEqual(payload["total_cost_usd"], "0.000200")
        self.assertEqual(payload["budget"]["maximumUsd"], "0.001000")
        self.assertFalse(payload["budget"]["exceeded"])

    def test_max_budget_cli_stops_without_retrying_or_returning_result(self) -> None:
        client = UsageTextClient(ModelUsage(input_tokens=100, output_tokens=50, total_tokens=150))
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory(prefix="vibeagent-budget-cli-") as base:
            with (
                patch("vibeagent.cli.create_chat_client", return_value=client),
                patch.dict(
                    os.environ,
                    {
                        "VIBEAGENT_INPUT_USD_PER_MILLION": "1",
                        "VIBEAGENT_OUTPUT_USD_PER_MILLION": "2",
                    },
                    clear=True,
                ),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "-p",
                        "--output-format",
                        "stream-json",
                        "--max-budget-usd",
                        "0.0002",
                        "--model-retries",
                        "3",
                        "--cwd",
                        base,
                        "inspect",
                    ]
                )

        records = [json.loads(line) for line in stdout.getvalue().splitlines()]
        model_error = next(
            record["event"]
            for record in records
            if record["type"] == "event" and record["event"]["type"] == "model_error"
        )
        payload = records[-1]
        self.assertEqual(exit_code, 1)
        self.assertEqual(client.calls, 1)
        self.assertFalse(model_error["will_retry"])
        self.assertTrue(model_error["terminal"])
        self.assertEqual(payload["subtype"], "error_max_budget_usd")
        self.assertEqual(payload["stopReason"], "error_max_budget_usd")
        self.assertEqual(payload["totalCostUsd"], "0.000200")
        self.assertNotIn("result", payload)


if __name__ == "__main__":
    unittest.main()
