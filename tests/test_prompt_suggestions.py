from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from vibeagent.prompt_suggestions import (
    MAX_PROMPT_SUGGESTION_CHARS,
    PROMPT_SUGGESTION_MAX_TOKENS,
    generate_prompt_suggestion,
    normalize_prompt_suggestion,
    try_generate_prompt_suggestion,
)
from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.session import summarize_session
from vibeagent.session_timeline_reports import format_session_event_timeline_item
from vibeagent.session_types import SessionEvent
from vibeagent.types import AssistantResponse, ChatMessage, ModelUsage


class PromptSuggestionTests(unittest.TestCase):
    def test_generates_tool_free_bounded_suggestion_and_records_usage(self) -> None:
        calls: list[tuple[list[ChatMessage], dict[str, object]]] = []

        def complete(client, messages, **kwargs):
            calls.append((list(messages), dict(kwargs)))
            return (
                AssistantResponse(
                    content=[{"type": "text", "text": "Run the focused tests.\nThen inspect the diff."}],
                    raw={},
                    usage=ModelUsage(input_tokens=12, output_tokens=6, total_tokens=18),
                ),
                None,
            )

        with tempfile.TemporaryDirectory(prefix="vibeagent-suggestion-") as base:
            session_dir = Path(base) / ".vibeagent" / "sessions" / "session"
            result = generate_prompt_suggestion(
                object(),
                [ChatMessage(role="assistant", content="Implemented the repair.")],
                session_dir=session_dir,
                model_timeout_ms=2_000,
                iteration=4,
                complete_func=complete,
            )
            events = [json.loads(line) for line in (session_dir / "events.jsonl").read_text().splitlines()]
            summary = summarize_session(Path(base), "session")

        self.assertTrue(result.success)
        self.assertEqual(result.suggestion, "Run the focused tests. Then inspect the diff.")
        self.assertIsNone(calls[0][1]["tools"])
        self.assertEqual(calls[0][1]["max_output_tokens"], PROMPT_SUGGESTION_MAX_TOKENS)
        self.assertEqual(calls[0][1]["model_retries"], 0)
        self.assertEqual(calls[0][1]["iteration"], 5)
        self.assertIn("user's language", str(calls[0][0][-1].content))
        self.assertEqual([event["type"] for event in events], [
            "prompt_suggestion_model",
            "prompt_suggestion_result",
        ])
        self.assertEqual(events[0]["usage"]["total_tokens"], 18)
        self.assertTrue(events[1]["success"])
        self.assertEqual(summary.total_tokens, 18)
        timeline = format_session_event_timeline_item(
            SessionEvent(line_number=2, type=events[1]["type"], payload=events[1])
        )
        self.assertIn("success", timeline)
        self.assertIn("Run the focused tests", timeline)

    def test_provider_failure_is_non_throwing_and_durable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-suggestion-") as base:
            session_dir = Path(base) / "session"
            result = generate_prompt_suggestion(
                object(),
                [ChatMessage(role="assistant", content="Done.")],
                session_dir=session_dir,
                model_timeout_ms=1_000,
                iteration=1,
                complete_func=lambda *args, **kwargs: (None, "provider unavailable"),
            )
            event = json.loads((session_dir / "events.jsonl").read_text().splitlines()[-1])

        self.assertFalse(result.success)
        self.assertEqual(result.error, "provider unavailable")
        self.assertFalse(event["success"])
        self.assertEqual(event["error"], "provider unavailable")

    def test_suggestion_model_error_does_not_fail_completed_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-suggestion-") as base:
            session_dir = Path(base) / ".vibeagent" / "sessions" / "session"
            append_session_event(
                session_dir,
                "result",
                {"success": True, "status": "completed", "message": "Done.", "iterations": 1},
            )
            append_session_event(
                session_dir,
                "prompt_suggestion_model_error",
                {
                    "error": "provider unavailable",
                    "usage": {"input_tokens": 3, "output_tokens": 0, "total_tokens": 3},
                },
            )
            summary = summarize_session(Path(base), "session")

        self.assertTrue(summary.completed)
        self.assertFalse(summary.failed)
        self.assertEqual(summary.model_errors, 0)
        self.assertEqual(summary.total_tokens, 3)

    def test_normalization_rejects_empty_controls_and_oversized_text(self) -> None:
        cases = (
            ("", "empty"),
            ("run tests\x1b[31m", "control"),
            ("x" * (MAX_PROMPT_SUGGESTION_CHARS + 1), "exceeded"),
        )
        for value, message in cases:
            with self.subTest(message=message):
                suggestion, error = normalize_prompt_suggestion(value)
                self.assertIsNone(suggestion)
                self.assertIn(message, str(error).lower())

    def test_normalization_redacts_secrets_before_delivery(self) -> None:
        suggestion, error = normalize_prompt_suggestion("Run with api_key=prompt-secret-value")

        self.assertIsNone(error)
        self.assertEqual(suggestion, "Run with api_key=[REDACTED]")

    def test_safe_generation_wrapper_suppresses_unexpected_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-suggestion-") as base:
            session_dir = Path(base) / "session"
            with patch(
                "vibeagent.prompt_suggestions.generate_prompt_suggestion",
                side_effect=RuntimeError("unexpected failure"),
            ):
                result = try_generate_prompt_suggestion(
                    object(),
                    [ChatMessage(role="assistant", content="Done.")],
                    session_dir=session_dir,
                    model_timeout_ms=1_000,
                    iteration=1,
                )

        self.assertFalse(result.success)
        self.assertIn("unexpected failure", str(result.error))


if __name__ == "__main__":
    unittest.main()
