from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from vibeagent.cli import main
from vibeagent.types import AssistantResponse, ModelUsage


class OverloadError(RuntimeError):
    status = 529


class SequenceClient:
    def __init__(self, model: str, responses: list[AssistantResponse | Exception]) -> None:
        self.model = model
        self.responses = responses
        self.calls = 0
        self.fallback: SequenceClient | None = None
        self.configured_models: dict[str, SequenceClient] = {}

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        result = self.responses[self.calls]
        self.calls += 1
        if isinstance(result, Exception):
            raise result
        return result

    def with_agent_profile(self, *, model: str | None, effort: str | None):
        if model in self.configured_models:
            return self.configured_models[model]
        if self.fallback is None or model != self.fallback.model:
            raise AssertionError(f"unexpected configured model: {model}")
        return self.fallback


def _response(text: str, usage: ModelUsage | None = None) -> AssistantResponse:
    return AssistantResponse(content=[{"type": "text", "text": text}], raw={}, usage=usage)


class CliModelFallbackTests(unittest.TestCase):
    def test_cli_fallback_chain_reports_selected_model_and_usage(self) -> None:
        primary = SequenceClient("primary", [OverloadError("overloaded")])
        first = SequenceClient("backup-a", [OverloadError("still overloaded")])
        second = SequenceClient("backup-b", [_response("Inspected with second backup.")])
        primary.configured_models = {"backup-a": first, "backup-b": second}
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory(prefix="vibeagent-fallback-chain-") as base:
            with (
                patch("vibeagent.cli.create_chat_client", return_value=primary),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "-p",
                        "--output-format",
                        "stream-json",
                        "--fallback-model",
                        "backup-a,backup-b",
                        "--cwd",
                        base,
                        "inspect",
                    ]
                )

        records = [json.loads(line) for line in stdout.getvalue().splitlines()]
        event = next(
            record["event"]
            for record in records
            if record["type"] == "event" and record["event"]["type"] == "model_fallback"
        )
        report = records[-1]["modelFallback"]
        self.assertEqual(exit_code, 0)
        self.assertEqual(event["fallback_model"], "backup-b")
        self.assertEqual(event["fallback_models"], ["backup-a", "backup-b"])
        self.assertEqual(event["fallback_index"], 1)
        self.assertEqual(event["fallback_transitions"][0]["fallback_model"], "backup-a")
        self.assertEqual(report["activeFallbackModel"], "backup-b")
        self.assertEqual(report["modelUses"], {"backup-a": 1, "backup-b": 1})

    def test_budget_terminal_error_preserves_fallback_event(self) -> None:
        primary = SequenceClient("primary", [OverloadError("overloaded")])
        fallback = SequenceClient(
            "backup",
            [_response("discarded", ModelUsage(input_tokens=100, output_tokens=50, total_tokens=150))],
        )
        primary.fallback = fallback
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory(prefix="vibeagent-fallback-budget-") as base:
            with (
                patch("vibeagent.cli.create_chat_client", return_value=primary),
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
                        "--fallback-model",
                        "backup",
                        "--max-budget-usd",
                        "0.0002",
                        "--cwd",
                        base,
                        "inspect",
                    ]
                )

        records = [json.loads(line) for line in stdout.getvalue().splitlines()]
        event_types = [record["event"]["type"] for record in records if record["type"] == "event"]
        payload = records[-1]
        self.assertEqual(exit_code, 1)
        self.assertIn("model_fallback", event_types)
        self.assertIn("model_error", event_types)
        self.assertEqual(payload["subtype"], "error_max_budget_usd")
        self.assertTrue(payload["modelFallback"]["activated"])
        self.assertTrue(payload["budget"]["exceeded"])

    def test_cli_switches_on_overload_streams_event_and_reports_fallback(self) -> None:
        primary = SequenceClient("primary", [OverloadError("overloaded")])
        fallback = SequenceClient("backup", [_response("Inspected with backup.")])
        primary.fallback = fallback
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory(prefix="vibeagent-fallback-cli-") as base:
            with (
                patch("vibeagent.cli.create_chat_client", return_value=primary),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "-p",
                        "--output-format",
                        "stream-json",
                        "--fallback-model",
                        "backup",
                        "--cwd",
                        base,
                        "inspect",
                    ]
                )

        records = [json.loads(line) for line in stdout.getvalue().splitlines()]
        fallback_event = next(
            record["event"]
            for record in records
            if record["type"] == "event" and record["event"]["type"] == "model_fallback"
        )
        payload = records[-1]
        self.assertEqual(exit_code, 0)
        self.assertEqual(primary.calls, 1)
        self.assertEqual(fallback.calls, 1)
        self.assertTrue(fallback_event["activated_now"])
        self.assertEqual(fallback_event["fallback_model"], "backup")
        self.assertEqual(payload["subtype"], "success")
        self.assertTrue(payload["modelFallback"]["activated"])
        self.assertEqual(payload["model_fallback"]["uses"], 1)

    def test_cli_keeps_primary_when_it_is_healthy(self) -> None:
        primary = SequenceClient("primary", [_response("Primary worked.")])
        fallback = SequenceClient("backup", [_response("unused")])
        primary.fallback = fallback
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory(prefix="vibeagent-fallback-cli-") as base:
            with (
                patch("vibeagent.cli.create_chat_client", return_value=primary),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    ["-p", "--output-format", "json", "--fallback-model", "backup", "--cwd", base, "inspect"]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(primary.calls, 1)
        self.assertEqual(fallback.calls, 0)
        self.assertFalse(payload["modelFallback"]["activated"])
        self.assertEqual(payload["modelFallback"]["uses"], 0)
        self.assertEqual(payload["modelFallback"]["modelUses"], {"backup": 0})

    def test_structured_output_uses_sticky_fallback_without_rechecking_primary(self) -> None:
        primary = SequenceClient("primary", [OverloadError("overloaded"), _response("unused")])
        fallback = SequenceClient(
            "backup",
            [_response("Inspected with backup."), _response('{"summary":"inspected"}')],
        )
        primary.fallback = fallback
        schema = json.dumps(
            {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            }
        )
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory(prefix="vibeagent-fallback-structured-") as base:
            with (
                patch("vibeagent.cli.create_chat_client", return_value=primary),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "-p",
                        "--output-format",
                        "json",
                        "--json-schema",
                        schema,
                        "--fallback-model",
                        "backup",
                        "--cwd",
                        base,
                        "inspect",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(primary.calls, 1)
        self.assertEqual(fallback.calls, 2)
        self.assertEqual(payload["modelFallback"]["uses"], 2)
        self.assertEqual(payload["structured_output"], {"summary": "inspected"})

    def test_unsupported_client_fails_before_agent_run(self) -> None:
        class UnsupportedClient:
            model = "primary"

            def complete(self, *args, **kwargs):
                return _response("unused")

        run_agent = Mock()
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory(prefix="vibeagent-fallback-cli-") as base:
            with (
                patch("vibeagent.cli.create_chat_client", return_value=UnsupportedClient()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    ["-p", "--output-format", "json", "--fallback-model", "backup", "--cwd", base, "inspect"]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertIn("does not support --fallback-model", payload["error"])
        run_agent.assert_not_called()


if __name__ == "__main__":
    unittest.main()
