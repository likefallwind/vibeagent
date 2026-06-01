import unittest

from vibeagent.chat import build_chat_messages, run_chat
from vibeagent.types import ChatMessage


class MockClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.messages: list[ChatMessage] = []

    def complete(self, messages: list[ChatMessage]) -> str:
        self.messages = messages
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


if __name__ == "__main__":
    unittest.main()
