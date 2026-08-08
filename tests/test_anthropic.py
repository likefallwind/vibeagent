import json
import unittest
from unittest.mock import patch

from vibeagent.anthropic import ANTHROPIC_API_VERSION, AnthropicClient
from vibeagent.types import ChatMessage


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def read(self):
        return self.payload


class AnthropicClientTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
