from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_model import complete_with_retries, is_context_limit_error
from vibeagent.types import ChatMessage


class ContextErrorClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.calls += 1
        raise RuntimeError("context_length_exceeded")


class AgentModelTests(unittest.TestCase):
    def test_context_limit_classifier_accepts_provider_markers_only(self) -> None:
        for message in (
            "context_length_exceeded",
            "This model's maximum context length is 128000 tokens",
            "Prompt is too long",
            "Input token count exceeds the model limit",
        ):
            with self.subTest(message=message):
                self.assertTrue(is_context_limit_error(RuntimeError(message)))

        self.assertFalse(is_context_limit_error(RuntimeError("provider unavailable")))
        self.assertFalse(is_context_limit_error(RuntimeError("request timeout")))

    def test_context_recovery_callback_failure_preserves_original_model_error(self) -> None:
        client = ContextErrorClient()

        def fail_recovery() -> bool:
            raise RuntimeError("compaction failed")

        with tempfile.TemporaryDirectory(prefix="vibeagent-model-context-") as base:
            session_dir = Path(base)
            response, message = complete_with_retries(
                client,
                [ChatMessage(role="user", content="inspect")],
                tools=None,
                max_output_tokens=1024,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                iteration=1,
                session_dir=session_dir,
                logger=None,
                recover_context=fail_recovery,
            )
            event = json.loads(session_dir.joinpath("events.jsonl").read_text(encoding="utf-8").splitlines()[0])

        self.assertIsNone(response)
        self.assertIn("context_length_exceeded", message or "")
        self.assertEqual(client.calls, 1)
        self.assertFalse(event["will_retry"])
        self.assertIn("compaction failed", event["context_recovery_error"])


if __name__ == "__main__":
    unittest.main()
