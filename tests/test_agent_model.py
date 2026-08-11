from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_model import complete_with_retries, is_context_limit_error
from vibeagent.types import AssistantResponse, ChatMessage


class ContextErrorClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.calls += 1
        raise RuntimeError("context_length_exceeded")


class AgentModelTests(unittest.TestCase):
    def test_stream_events_include_retry_attempt_metadata(self) -> None:
        class StreamingClient:
            def __init__(self) -> None:
                self.calls = 0

            def complete_stream(self, messages, *, on_event, **kwargs):
                self.calls += 1
                on_event({"type": "message_start"})
                if self.calls == 1:
                    raise RuntimeError("temporary failure")
                on_event({"type": "message_stop"})
                return AssistantResponse(content=[{"type": "text", "text": "done"}], raw={})

        observed = []
        client = StreamingClient()
        with tempfile.TemporaryDirectory(prefix="vibeagent-model-stream-") as base:
            session_dir = Path(base)
            response, message = complete_with_retries(
                client,
                [ChatMessage(role="user", content="inspect")],
                tools=None,
                max_output_tokens=1024,
                model_retries=1,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                iteration=3,
                session_dir=session_dir,
                logger=None,
                model_stream_handler=lambda path, iteration, attempt, event: observed.append(
                    (path, iteration, attempt, event["type"])
                ),
            )

        self.assertIsNone(message)
        self.assertEqual(response.content[0]["text"], "done")
        self.assertEqual(
            [(iteration, attempt, event_type) for _path, iteration, attempt, event_type in observed],
            [(3, 1, "message_start"), (3, 2, "message_start"), (3, 2, "message_stop")],
        )
        self.assertTrue(all(path == session_dir for path, *_rest in observed))

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
