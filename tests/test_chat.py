import unittest
from unittest.mock import patch

from vibeagent.chat import build_chat_messages, run_chat
from vibeagent.types import ChatMessage


class MockClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.messages: list[ChatMessage] = []
        self.max_tokens: int | None = None
        self.timeout_ms: int | None = None

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_ms: int = 120_000,
    ) -> str:
        self.messages = messages
        self.max_tokens = max_tokens
        self.timeout_ms = timeout_ms
        return self.response


class FlakyClient:
    def __init__(self, failures: int, response: str = "  好  ") -> None:
        self.failures = failures
        self.response = response
        self.calls = 0

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_ms: int = 120_000,
    ) -> str:
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("temporary provider failure")
        return self.response


class ChatTests(unittest.TestCase):
    def test_build_chat_messages_uses_plain_conversation_prompt(self) -> None:
        messages = build_chat_messages(
            "你好",
            [
                ChatMessage(role="user", content="上一句"),
                ChatMessage(role="assistant", content="上一答"),
            ],
        )

        self.assertEqual(messages[0].role, "system")
        self.assertIn("daily conversation mode", messages[0].content)
        self.assertIn("Do not use the coding-agent JSON action protocol", messages[0].content)
        self.assertEqual(messages[-1], ChatMessage(role="user", content="你好"))

    def test_build_chat_messages_bounds_history(self) -> None:
        history = [ChatMessage(role="user", content=str(index)) for index in range(20)]

        messages = build_chat_messages("now", history, max_history=3)

        self.assertEqual([message.content for message in messages[1:]], ["17", "18", "19", "now"])

    def test_run_chat_returns_trimmed_plain_response(self) -> None:
        client = MockClient("  你好，有什么想聊的？  ")

        response = run_chat("你好", client)

        self.assertEqual(response, "你好，有什么想聊的？")
        self.assertEqual(client.messages[-1], ChatMessage(role="user", content="你好"))
        self.assertEqual(client.max_tokens, 4096)

    def test_run_chat_passes_max_output_tokens_to_client(self) -> None:
        client = MockClient("  好  ")

        response = run_chat("你好", client, max_output_tokens=8192, model_timeout_ms=45_000)

        self.assertEqual(response, "好")
        self.assertEqual(client.max_tokens, 8192)
        self.assertEqual(client.timeout_ms, 45_000)

    def test_run_chat_retries_transient_model_failures(self) -> None:
        client = FlakyClient(failures=1)

        with patch("vibeagent.chat.time.sleep") as sleep:
            response = run_chat("你好", client, model_retries=1, model_retry_delay_ms=25)

        self.assertEqual(response, "好")
        self.assertEqual(client.calls, 2)
        sleep.assert_called_once_with(0.025)

    def test_run_chat_model_retries_zero_disables_retry(self) -> None:
        client = FlakyClient(failures=1)

        with self.assertRaisesRegex(RuntimeError, "temporary provider failure"):
            run_chat("你好", client, model_retries=0, model_retry_delay_ms=0)

        self.assertEqual(client.calls, 1)


if __name__ == "__main__":
    unittest.main()
