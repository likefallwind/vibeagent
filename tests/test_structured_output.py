from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.structured_output import (
    MAX_STRUCTURED_OUTPUT_ATTEMPTS,
    generate_structured_output,
    parse_structured_output_schema,
)
from vibeagent.session import summarize_session
from vibeagent.types import AssistantResponse, ChatMessage, ModelUsage


class StructuredOutputSchemaTests(unittest.TestCase):
    def test_parses_draft7_schema_and_treats_format_as_annotation(self) -> None:
        schema = parse_structured_output_schema(
            json.dumps(
                {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                    "properties": {"email": {"type": "string", "format": "email"}},
                    "required": ["email"],
                }
            )
        )

        self.assertEqual(schema["required"], ["email"])

    def test_rejects_invalid_non_object_newer_draft_and_external_reference(self) -> None:
        cases = [
            ("{", "Invalid --json-schema JSON"),
            ("[]", "JSON object"),
            (json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema"}), "Draft-07"),
            (json.dumps({"$ref": "https://example.com/schema.json"}), r"external \$ref"),
            (json.dumps({"type": "unknown"}), "Invalid --json-schema"),
            ('{"type":"number","minimum":NaN}', "non-finite JSON number"),
            (json.dumps({"$ref": "#/definitions/missing"}), r"unresolved local \$ref"),
        ]

        for raw, message in cases:
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, message):
                parse_structured_output_schema(raw)


class StructuredOutputGenerationTests(unittest.TestCase):
    def test_reprompts_after_validation_error_and_records_valid_output(self) -> None:
        responses = [
            AssistantResponse(content=[{"type": "text", "text": '{"count":"two"}'}], raw={}),
            AssistantResponse(
                content=[{"type": "text", "text": '{"count":2}'}],
                raw={},
                usage=ModelUsage(input_tokens=10, output_tokens=2, total_tokens=12),
            ),
        ]
        calls: list[list[ChatMessage]] = []

        def complete(client, messages, **kwargs):
            calls.append(list(messages))
            return responses.pop(0), None

        with tempfile.TemporaryDirectory(prefix="vibeagent-structured-") as base:
            root = Path(base)
            session_dir = root / ".vibeagent" / "sessions" / "run-1"
            session_dir.mkdir(parents=True)
            result = generate_structured_output(
                object(),
                [ChatMessage(role="assistant", content="Found two items.")],
                {
                    "type": "object",
                    "properties": {"count": {"type": "integer"}},
                    "required": ["count"],
                    "additionalProperties": False,
                },
                session_dir=session_dir,
                max_output_tokens=100,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=1_000,
                iteration=3,
                complete_func=complete,
            )
            events = [json.loads(line) for line in (session_dir / "events.jsonl").read_text().splitlines()]
            usage_summary = summarize_session(root, "run-1")

        self.assertTrue(result.success)
        self.assertEqual(result.value, {"count": 2})
        self.assertEqual(result.attempts, 2)
        self.assertIn("failed validation", str(calls[1][-1].content))
        self.assertEqual([event["type"] for event in events].count("structured_output_model"), 2)
        self.assertEqual(events[-1]["type"], "structured_output_result")
        self.assertTrue(events[-1]["success"])
        self.assertEqual(usage_summary.total_tokens, 12)

    def test_returns_provider_error_without_validation_retry(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-structured-") as base:
            session_dir = Path(base) / "session"
            session_dir.mkdir()
            result = generate_structured_output(
                object(),
                [],
                {"type": "object"},
                session_dir=session_dir,
                max_output_tokens=100,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=1_000,
                iteration=1,
                complete_func=lambda *args, **kwargs: (None, "provider unavailable"),
            )

        self.assertFalse(result.success)
        self.assertEqual(result.error, "provider unavailable")
        self.assertEqual(result.attempts, 1)

    def test_fails_after_bounded_invalid_json_attempts(self) -> None:
        calls = 0

        def complete(*args, **kwargs):
            nonlocal calls
            calls += 1
            return AssistantResponse(content=[{"type": "text", "text": "not-json"}], raw={}), None

        with tempfile.TemporaryDirectory(prefix="vibeagent-structured-") as base:
            session_dir = Path(base) / "session"
            session_dir.mkdir()
            result = generate_structured_output(
                object(),
                [],
                {"type": "array", "items": {"type": "string"}},
                session_dir=session_dir,
                max_output_tokens=100,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=1_000,
                iteration=1,
                complete_func=complete,
            )

        self.assertFalse(result.success)
        self.assertEqual(calls, MAX_STRUCTURED_OUTPUT_ATTEMPTS)
        self.assertIn("after 3 attempts", result.error or "")


if __name__ == "__main__":
    unittest.main()
