from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.agent import run_agent
from vibeagent.agent_hook_results import HookRunResult
from vibeagent.model_failure import classify_model_failure
from vibeagent.types import AssistantResponse
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_hooks import parse_inline_hooks, read_project_hooks


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, response_text: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.response_text = response_text


class FailingClient:
    def __init__(self, error: Exception, *, failures: int | None = None) -> None:
        self.error = error
        self.failures = failures
        self.calls = 0

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.calls += 1
        if self.failures is None or self.calls <= self.failures:
            raise self.error
        content = [{"type": "text", "text": "Recovered."}]
        return AssistantResponse(content=content, raw={"content": content})


def _write_hooks(root: Path, matcher: str = ".*") -> None:
    path = root / ".vibeagent" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "StopFailure": [
                    {
                        "matcher": matcher,
                        "hooks": [{"type": "command", "command": "audit-failure"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def _blocking_result() -> HookRunResult:
    return HookRunResult(
        event="StopFailure",
        command="audit-failure",
        source="test",
        status="failed",
        ok=False,
        exit_code=2,
        timed_out=False,
        stdout=json.dumps({"decision": "block", "reason": "ignore this"}),
        stderr="hook tried to block",
        message="StopFailure hook exited with code 2.",
    )


class StopFailureClassificationTests(unittest.TestCase):
    def test_classifies_documented_provider_failure_types(self) -> None:
        cases = (
            (ProviderError("too many requests", status=429), "rate_limit"),
            (ProviderError("service overloaded", status=529), "overloaded"),
            (ProviderError("invalid api key", status=401), "authentication_failed"),
            (ProviderError("oauth_org_not_allowed"), "oauth_org_not_allowed"),
            (ProviderError("credit balance exhausted", status=402), "billing_error"),
            (ProviderError("bad request", status=400), "invalid_request"),
            (ProviderError("model_not_found", status=404), "model_not_found"),
            (ProviderError("internal server error", status=500), "server_error"),
            (ProviderError("max_output_tokens reached"), "max_output_tokens"),
            (ProviderError("context_length_exceeded"), "invalid_request"),
            (ProviderError("connection closed"), "unknown"),
        )
        for error, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(classify_model_failure(error), expected)

    def test_classifies_wrapped_provider_error_from_cause(self) -> None:
        outer = RuntimeError("fallback failed")
        outer.__cause__ = ProviderError("rate limited", status=429)
        self.assertEqual(classify_model_failure(outer), "rate_limit")


class StopFailureHookTests(unittest.TestCase):
    def test_config_supports_stop_failure_matchers_but_rejects_model_handlers(self) -> None:
        valid = parse_inline_hooks(
            {
                "StopFailure": [
                    {
                        "matcher": "rate_limit|overloaded",
                        "hooks": [{"type": "command", "command": "audit"}],
                    }
                ]
            },
            "test",
        )
        invalid = parse_inline_hooks(
            {
                "StopFailure": [
                    {"hooks": [{"type": "prompt", "prompt": "decide"}]}
                ]
            },
            "test",
        )
        self.assertIsNone(valid.error)
        self.assertEqual(valid.hooks[0].matcher, "rate_limit|overloaded")
        self.assertIn("do not support prompt handlers", invalid.error or "")

    def test_final_api_error_fires_once_with_documented_input_and_cannot_block(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-stop-failure-") as base:
            root = Path(base)
            _write_hooks(root, "rate_limit")
            client = FailingClient(
                ProviderError(
                    "request rejected",
                    status=429,
                    response_text='{"error":"rate_limit","token":"secret-value"}',
                )
            )
            captured: list[dict[str, object]] = []

            def run_hook(*args, **kwargs):
                captured.append(kwargs["hook_input"])
                return _blocking_result()

            with patch("vibeagent.agent_lifecycle_hooks.run_project_hook", side_effect=run_hook):
                result = run_agent(
                    "inspect",
                    base_dir=root,
                    client=client,
                    max_iterations=1,
                    model_retries=1,
                    model_retry_delay_ms=0,
                )

        self.assertFalse(result.success)
        self.assertIn("request rejected", result.message)
        self.assertNotIn("hook tried to block", result.message)
        self.assertEqual(client.calls, 2)
        self.assertEqual(len(captured), 1)
        hook_input = captured[0]
        self.assertEqual(hook_input["hook_event_name"], "StopFailure")
        self.assertEqual(hook_input["error"], "rate_limit")
        self.assertEqual(hook_input["permission_mode"], "default")
        self.assertIn("request rejected", hook_input["error_details"])
        self.assertIn("Model request failed", hook_input["last_assistant_message"])

    def test_successful_retry_does_not_fire_stop_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-stop-failure-") as base:
            root = Path(base)
            _write_hooks(root)
            client = FailingClient(RuntimeError("temporary outage"), failures=1)

            with patch("vibeagent.agent_lifecycle_hooks.run_project_hook") as run_hook:
                result = run_agent(
                    "inspect",
                    base_dir=root,
                    client=client,
                    max_iterations=1,
                    model_retries=1,
                    model_retry_delay_ms=0,
                )

        self.assertTrue(result.success)
        self.assertEqual(client.calls, 2)
        run_hook.assert_not_called()

    def test_nonmatching_failure_does_not_run_hook(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-stop-failure-") as base:
            root = Path(base)
            _write_hooks(root, "authentication_failed")
            client = FailingClient(ProviderError("too many requests", status=429))

            with patch("vibeagent.agent_lifecycle_hooks.run_project_hook") as run_hook:
                result = run_agent(
                    "inspect",
                    base_dir=root,
                    client=client,
                    max_iterations=1,
                    model_retries=0,
                )

        self.assertFalse(result.success)
        run_hook.assert_not_called()

    def test_hook_runtime_error_does_not_replace_model_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-stop-failure-") as base:
            root = Path(base)
            _write_hooks(root)
            client = FailingClient(RuntimeError("provider unavailable"))

            with patch(
                "vibeagent.agent_lifecycle_hooks.run_project_hook",
                side_effect=RuntimeError("hook runtime broke"),
            ):
                result = run_agent(
                    "inspect",
                    base_dir=root,
                    client=client,
                    max_iterations=1,
                    model_retries=0,
                )
            events = [
                json.loads(line)
                for line in (root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        self.assertFalse(result.success)
        self.assertIn("provider unavailable", result.message)
        self.assertNotIn("hook runtime broke", result.message)
        errors = [event for event in events if event["type"] == "stop_failure_hook_error"]
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error"], "unknown")

    def test_lifecycle_config_loads_stop_failure_without_forcing_sequential_tools(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-stop-failure-") as base:
            root = Path(base)
            _write_hooks(root)
            hooks = read_project_hooks(create_run_workspace(root))

        self.assertEqual([hook.event for hook in hooks.hooks], ["StopFailure"])
        self.assertFalse(hooks.requires_sequential_tools)


if __name__ == "__main__":
    unittest.main()
