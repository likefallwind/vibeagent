import json
import unittest
from unittest.mock import patch

from vibeagent.anthropic import ANTHROPIC_API_VERSION, AnthropicClient
from vibeagent.types import ChatMessage


class _FakeResponse:
    def __init__(self, payload: dict | bytes) -> None:
        self.payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def read(self):
        return self.payload

    def __iter__(self):
        return iter(self.payload.splitlines(keepends=True))


class AnthropicClientTests(unittest.TestCase):
    def test_complete_stream_accumulates_events_and_usage(self) -> None:
        payload = b"".join(
            b"data: " + json.dumps(event).encode() + b"\n\n"
            for event in (
                {"type": "message_start", "message": {"usage": {"input_tokens": 3}}},
                {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
                {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "hello"}},
                {"type": "content_block_stop", "index": 0},
                {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 2}},
                {"type": "message_stop"},
            )
        )
        events = []
        with patch("vibeagent.anthropic.urlopen", return_value=_FakeResponse(payload)) as urlopen:
            result = AnthropicClient(api_key="key").complete_stream(
                [ChatMessage(role="user", content="Hi")],
                on_event=events.append,
            )

        body = json.loads(urlopen.call_args.args[0].data)
        self.assertTrue(body["stream"])
        self.assertEqual(result.content, [{"type": "text", "text": "hello"}])
        self.assertEqual(result.usage.total_tokens, 5)
        self.assertEqual(events[-1]["type"], "message_stop")

    def test_complete_uses_messages_api_headers_tools_and_usage(self) -> None:
        response = _FakeResponse(
            {
                "content": [{"type": "tool_use", "id": "toolu_1", "name": "read_file", "input": {"path": "app.py"}}],
                "usage": {"input_tokens": 12, "output_tokens": 4},
            }
        )
        client = AnthropicClient(api_key="anthropic-key", model="claude-sonnet-5")

        with patch("vibeagent.anthropic.urlopen", return_value=response) as urlopen:
            result = client.complete(
                [ChatMessage(role="system", content="Code carefully."), ChatMessage(role="user", content="Inspect")],
                tools=[{"name": "read_file", "input_schema": {"type": "object"}}],
                timeout_ms=45_000,
            )

        request = urlopen.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(request.get_header("X-api-key"), "anthropic-key")
        self.assertEqual(request.get_header("Anthropic-version"), ANTHROPIC_API_VERSION)
        self.assertNotIn("Authorization", request.headers)
        self.assertEqual(body["model"], "claude-sonnet-5")
        self.assertEqual(body["system"], "Code carefully.")
        self.assertEqual(body["tools"][0]["name"], "read_file")
        self.assertNotIn("temperature", body)
        self.assertEqual(result.content[0]["type"], "tool_call")
        self.assertEqual(result.usage.total_tokens, 16)
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 45.0)

    def test_auth_token_uses_bearer_header_for_gateway(self) -> None:
        client = AnthropicClient(
            api_key="gateway-token",
            base_url="https://gateway.example/anthropic/",
            model="claude-sonnet-4-6",
            use_auth_token=True,
        )
        with patch("vibeagent.anthropic.urlopen", return_value=_FakeResponse({"content": [{"type": "text", "text": "ok"}]})) as urlopen:
            client.complete([ChatMessage(role="user", content="Hi")], temperature=0.3)

        request = urlopen.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "https://gateway.example/anthropic/v1/messages")
        self.assertEqual(request.get_header("Authorization"), "Bearer gateway-token")
        self.assertIsNone(request.get_header("X-api-key"))
        self.assertEqual(body["temperature"], 0.3)

    def test_agent_profile_overrides_model_and_sends_output_effort(self) -> None:
        client = AnthropicClient(
            api_key="anthropic-key",
            model="parent-model",
            betas=("interleaved-thinking", "files-api-2025-04-14"),
        )
        profiled = client.with_agent_profile(model="claude-opus-5", effort="medium")
        with patch(
            "vibeagent.anthropic.urlopen",
            return_value=_FakeResponse({"content": [{"type": "text", "text": "ok"}]}),
        ) as urlopen:
            profiled.complete([ChatMessage(role="user", content="Hi")])

        body = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(body["model"], "claude-opus-5")
        self.assertEqual(body["output_config"], {"effort": "medium"})
        self.assertEqual(
            urlopen.call_args.args[0].get_header("Anthropic-beta"),
            "interleaved-thinking,files-api-2025-04-14",
        )
        self.assertEqual(profiled.betas, client.betas)
        self.assertEqual(client.model, "parent-model")
        self.assertIsNone(client.effort)

    def test_streaming_request_includes_beta_header(self) -> None:
        payload = b"".join(
            [
                b'data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":"ok"}}\n\n',
                b'data: {"type":"message_stop"}\n\n',
            ]
        )
        client = AnthropicClient(api_key="key", betas=("interleaved-thinking",))
        with patch("vibeagent.anthropic.urlopen", return_value=_FakeResponse(payload)) as urlopen:
            client.complete_stream(
                [ChatMessage(role="user", content="Hi")],
                on_event=lambda event: None,
            )

        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Anthropic-beta"), "interleaved-thinking")
        self.assertEqual(request.get_header("Accept"), "text/event-stream")


if __name__ == "__main__":
    unittest.main()
