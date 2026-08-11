from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_model import complete_with_retries
from vibeagent.anthropic import AnthropicClient
from vibeagent.minimax import MiniMaxClient
from vibeagent.model_fallback import (
    create_fallback_chat_client,
    extract_model_fallback_error_event,
    is_model_overload_error,
    normalize_fallback_model,
    normalize_fallback_models,
)
from vibeagent.openai_compat import OpenAICompatibleClient
from vibeagent.types import AssistantResponse, ChatMessage


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        self.status = status
        self.response_text = message
        super().__init__(message)


class SequenceClient:
    def __init__(
        self,
        model: str,
        responses: list[AssistantResponse | Exception],
        registry: dict[str, "SequenceClient"] | None = None,
    ) -> None:
        self.model = model
        self.responses = responses
        self.registry = registry if registry is not None else {}
        self.calls = 0
        self.profile_calls: list[tuple[str | None, str | None]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        result = self.responses[self.calls]
        self.calls += 1
        if isinstance(result, Exception):
            raise result
        return result

    def complete_stream(
        self,
        messages,
        tools=None,
        max_tokens=4096,
        temperature=0.2,
        timeout_ms=120_000,
        *,
        on_event,
    ):
        on_event({"type": "message_start", "message": {"model": self.model}})
        return self.complete(messages, tools, max_tokens, temperature, timeout_ms)

    def with_agent_profile(self, *, model: str | None, effort: str | None):
        self.profile_calls.append((model, effort))
        return self.registry[model or self.model]


def _response(text: str) -> AssistantResponse:
    return AssistantResponse(content=[{"type": "text", "text": text}], raw={})


class ModelFallbackTests(unittest.TestCase):
    def test_streaming_overload_uses_fallback_and_preserves_events(self) -> None:
        fallback = SequenceClient("backup", [_response("streamed")])
        primary = SequenceClient(
            "primary",
            [ProviderError("overloaded", status=529)],
            {"backup": fallback},
        )
        client, _state = create_fallback_chat_client(primary, "backup")
        events = []

        response = client.complete_stream([], on_event=events.append)

        self.assertEqual(response.content[0]["text"], "streamed")
        self.assertEqual([event["message"]["model"] for event in events], ["primary", "backup"])
        self.assertEqual(response.raw["_vibeagent_model_fallback"]["fallback_model"], "backup")

    def test_all_builtin_providers_create_scoped_fallback_clients(self) -> None:
        clients = [
            AnthropicClient("key", model="primary"),
            MiniMaxClient("key", model="primary"),
            OpenAICompatibleClient("key", model="primary"),
        ]

        for client in clients:
            with self.subTest(client=type(client).__name__):
                wrapped, state = create_fallback_chat_client(client, "backup")
                self.assertEqual(wrapped.fallback.model, "backup")
                self.assertEqual(state.fallback_model, "backup")

    def test_anthropic_profile_keeps_effort_on_primary_and_fallback(self) -> None:
        wrapped, state = create_fallback_chat_client(
            AnthropicClient("key", model="primary"),
            "backup",
        )

        profiled = wrapped.with_agent_profile(model="reviewer", effort="high")

        self.assertIs(profiled.state, state)
        self.assertEqual(profiled.primary.model, "reviewer")
        self.assertEqual(profiled.primary.effort, "high")
        self.assertEqual(profiled.fallback.model, "backup")
        self.assertEqual(profiled.fallback.effort, "high")

    def test_profile_configures_every_fallback_model_with_effort(self) -> None:
        wrapped, state = create_fallback_chat_client(
            AnthropicClient("key", model="primary"),
            "backup-a,backup-b",
        )

        profiled = wrapped.with_agent_profile(model="reviewer", effort="high")

        self.assertIs(profiled.state, state)
        self.assertEqual(
            [(client.model, client.effort) for client in profiled.fallbacks],
            [("backup-a", "high"), ("backup-b", "high")],
        )

    def test_status_529_activates_fallback_and_stays_sticky(self) -> None:
        fallback = SequenceClient("backup", [_response("first"), _response("second")])
        registry = {"backup": fallback}
        primary = SequenceClient(
            "primary",
            [ProviderError("capacity", status=529), _response("unused")],
            registry,
        )
        client, state = create_fallback_chat_client(primary, "backup")

        first = client.complete([])
        second = client.complete([])

        self.assertEqual(first.content[0]["text"], "first")
        self.assertEqual(second.content[0]["text"], "second")
        self.assertEqual(primary.calls, 1)
        self.assertEqual(fallback.calls, 2)
        self.assertEqual(state.report()["uses"], 2)
        self.assertTrue(state.report()["activated"])
        self.assertTrue(first.raw["_vibeagent_model_fallback"]["activated_now"])
        self.assertEqual(second.raw["_vibeagent_model_fallback"]["reason"], "sticky")

    def test_non_overload_error_does_not_use_fallback(self) -> None:
        fallback = SequenceClient("backup", [_response("unused")])
        primary = SequenceClient(
            "primary",
            [ProviderError("invalid API key", status=401)],
            {"backup": fallback},
        )
        client, state = create_fallback_chat_client(primary, "backup")

        with self.assertRaisesRegex(ProviderError, "invalid API key"):
            client.complete([])

        self.assertEqual(fallback.calls, 0)
        self.assertFalse(state.report()["activated"])

    def test_overloaded_fallback_advances_chain_and_stays_on_successful_model(self) -> None:
        first = SequenceClient("backup-a", [ProviderError("busy", status=503)])
        second = SequenceClient("backup-b", [_response("first"), _response("second")])
        registry = {"backup-a": first, "backup-b": second}
        primary = SequenceClient("primary", [ProviderError("overloaded", status=529)], registry)
        client, state = create_fallback_chat_client(primary, "backup-a, backup-b")

        first_response = client.complete([])
        second_response = client.complete([])

        event = first_response.raw["_vibeagent_model_fallback"]
        self.assertEqual(first_response.content[0]["text"], "first")
        self.assertEqual(second_response.content[0]["text"], "second")
        self.assertEqual((primary.calls, first.calls, second.calls), (1, 1, 2))
        self.assertEqual(event["fallback_model"], "backup-b")
        self.assertEqual(event["fallback_index"], 1)
        self.assertEqual(event["reason"], "fallback_overloaded")
        self.assertEqual(
            event["fallback_transitions"],
            [
                {
                    "fallback_model": "backup-a",
                    "fallback_index": 0,
                    "error": "ProviderError: busy",
                }
            ],
        )
        self.assertEqual(
            state.report(),
            {
                "fallbackModel": "backup-b",
                "fallbackModels": ["backup-a", "backup-b"],
                "activated": True,
                "uses": 3,
                "primaryOverloadCount": 1,
                "fallbackOverloadCount": 1,
                "modelUses": {"backup-a": 1, "backup-b": 2},
                "activeFallbackModel": "backup-b",
                "activeFallbackIndex": 1,
                "lastPrimaryError": "ProviderError: overloaded",
                "lastFallbackError": "ProviderError: busy",
            },
        )

    def test_non_overload_fallback_failure_does_not_skip_to_next_model(self) -> None:
        first = SequenceClient("backup-a", [RuntimeError("bad response")])
        second = SequenceClient("backup-b", [_response("unused")])
        primary = SequenceClient(
            "primary",
            [ProviderError("overloaded", status=529)],
            {"backup-a": first, "backup-b": second},
        )
        client, _state = create_fallback_chat_client(primary, "backup-a,backup-b")

        with self.assertRaisesRegex(RuntimeError, "Fallback model 'backup-a'") as caught:
            client.complete([])

        self.assertEqual(second.calls, 0)
        self.assertEqual(caught.exception.fallback_index, 0)

    def test_exhausted_chain_reports_every_overload_transition(self) -> None:
        first = SequenceClient("backup-a", [ProviderError("first busy", status=503)])
        second = SequenceClient("backup-b", [ProviderError("second busy", status=529)])
        primary = SequenceClient(
            "primary",
            [ProviderError("primary busy", status=529)],
            {"backup-a": first, "backup-b": second},
        )
        client, state = create_fallback_chat_client(primary, "backup-a,backup-b")

        with self.assertRaisesRegex(RuntimeError, "backup-b") as caught:
            client.complete([])

        event = extract_model_fallback_error_event(caught.exception)
        self.assertEqual(event["fallback_model"], "backup-b")
        self.assertEqual(event["fallback_index"], 1)
        self.assertEqual(
            [transition["fallback_model"] for transition in event["fallback_transitions"]],
            ["backup-a", "backup-b"],
        )
        self.assertEqual(state.report()["fallbackOverloadCount"], 2)

    def test_concurrent_stale_advance_does_not_skip_a_fallback(self) -> None:
        state = create_fallback_chat_client(
            AnthropicClient("key", model="primary"),
            "backup-a,backup-b,backup-c",
        )[1]
        state.activate(ProviderError("primary busy", status=529))

        first_advance = state.advance(0, ProviderError("first busy", status=503))
        stale_advance = state.advance(0, ProviderError("same first busy", status=503))

        self.assertEqual(first_advance, 1)
        self.assertEqual(stale_advance, 1)
        self.assertEqual(state.report()["activeFallbackModel"], "backup-b")

    def test_overload_detection_follows_typed_status_text_and_causes(self) -> None:
        caused = RuntimeError("outer")
        caused.__cause__ = ProviderError("overloaded_error")

        self.assertTrue(is_model_overload_error(ProviderError("busy", status=503)))
        self.assertTrue(is_model_overload_error(caused))
        self.assertFalse(is_model_overload_error(ProviderError("rate limited", status=429)))

    def test_fallback_failure_retries_only_the_sticky_fallback(self) -> None:
        fallback = SequenceClient(
            "backup",
            [RuntimeError("temporary backup failure"), _response("recovered")],
        )
        primary = SequenceClient(
            "primary",
            [ProviderError("overloaded", status=529), _response("unused")],
            {"backup": fallback},
        )
        client, state = create_fallback_chat_client(primary, "backup")
        with tempfile.TemporaryDirectory(prefix="vibeagent-fallback-") as base:
            session_dir = Path(base) / "session"
            session_dir.mkdir()
            response, error = complete_with_retries(
                client,
                [ChatMessage(role="user", content="inspect")],
                tools=None,
                max_output_tokens=100,
                model_retries=1,
                model_retry_delay_ms=0,
                model_timeout_ms=1_000,
                iteration=1,
                session_dir=session_dir,
                logger=None,
            )
            events = [json.loads(line) for line in (session_dir / "events.jsonl").read_text().splitlines()]

        self.assertIsNone(error)
        self.assertEqual(response.content[0]["text"], "recovered")
        self.assertEqual(primary.calls, 1)
        self.assertEqual(fallback.calls, 2)
        self.assertEqual(state.report()["uses"], 2)
        self.assertEqual(events[0]["type"], "model_fallback")
        self.assertEqual(events[0]["fallback_model"], "backup")
        model_error = next(event for event in events if event["type"] == "model_error")
        self.assertTrue(model_error["will_retry"])
        self.assertEqual(events[-1]["type"], "model_fallback")

    def test_profile_clients_share_activated_fallback_state(self) -> None:
        fallback = SequenceClient("backup", [_response("main"), _response("profile")])
        reviewer = SequenceClient("reviewer", [_response("unused")])
        registry = {"backup": fallback, "reviewer": reviewer}
        primary = SequenceClient("primary", [ProviderError("overloaded", status=529)], registry)
        client, state = create_fallback_chat_client(primary, "backup")

        client.complete([])
        profiled = client.with_agent_profile(model="reviewer", effort=None)
        profiled.complete([])

        self.assertTrue(state.report()["activated"])
        self.assertEqual(reviewer.calls, 0)
        self.assertEqual(fallback.calls, 2)

    def test_rejects_same_invalid_or_unsupported_fallback_model(self) -> None:
        client = SequenceClient("primary", [], {"primary": SequenceClient("primary", [])})
        with self.assertRaisesRegex(ValueError, "differ"):
            create_fallback_chat_client(client, "primary")
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            normalize_fallback_model("  ")
        with self.assertRaisesRegex(ValueError, "control"):
            normalize_fallback_model("bad\nmodel")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            normalize_fallback_models("backup, backup")
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            normalize_fallback_models("backup,,last")
        with self.assertRaisesRegex(ValueError, "at most 10"):
            normalize_fallback_models(",".join(f"model-{index}" for index in range(11)))

        class UnsupportedClient:
            def complete(self, *args, **kwargs):
                return _response("ok")

        with self.assertRaisesRegex(ValueError, "does not support"):
            create_fallback_chat_client(UnsupportedClient(), "backup")


if __name__ == "__main__":
    unittest.main()
