import unittest

from vibeagent.btw import (
    MAX_BTW_CONTEXT_CHARS,
    MAX_BTW_QUESTION_CHARS,
    build_btw_messages,
    render_btw_context,
    run_btw,
)
from vibeagent.types import ChatMessage


class RecordingClient:
    def __init__(self, response: str = "  concise answer  ") -> None:
        self.response = response
        self.messages: list[ChatMessage] = []
        self.tools: list[dict] | None = [{"unexpected": True}]
        self.max_tokens: int | None = None

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_ms: int = 120_000,
    ) -> str:
        self.messages = messages
        self.tools = tools
        self.max_tokens = max_tokens
        return self.response


class BtwTests(unittest.TestCase):
    def test_run_btw_uses_current_conversation_without_tools(self) -> None:
        client = RecordingClient()
        history = [
            ChatMessage(role="user", content="Fix the parser."),
            ChatMessage(
                role="assistant",
                content=[
                    {"type": "text", "text": "I inspected it."},
                    {"type": "tool_call", "id": "call-1", "name": "Read", "input": {"file_path": "parser.py"}},
                ],
            ),
            ChatMessage(
                role="user",
                content=[
                    {"type": "tool_result", "tool_call_id": "call-1", "content": "line 7 fails"},
                ],
            ),
        ]

        response = run_btw("What failed?", client, history=history, max_output_tokens=1234)

        self.assertEqual(response, "concise answer")
        self.assertIsNone(client.tools)
        self.assertEqual(client.max_tokens, 1234)
        self.assertEqual(len(client.messages), 2)
        self.assertIn("Do not call tools", client.messages[0].content)
        prompt = client.messages[1].content
        self.assertIn("Fix the parser.", prompt)
        self.assertIn("[Tool call Read]", prompt)
        self.assertIn("line 7 fails", prompt)
        self.assertIn("Side question:\nWhat failed?", prompt)

    def test_build_btw_messages_keeps_operational_prompt_with_custom_preferences(self) -> None:
        messages = build_btw_messages(
            "Summarize it.",
            system_prompt="Reply as a release engineer.",
            append_system_prompt="Use one sentence.",
        )

        system = messages[0].content
        self.assertIn("Do not continue the main task", system)
        self.assertIn("Reply as a release engineer.", system)
        self.assertIn("Use one sentence.", system)

    def test_render_btw_context_omits_binary_content_and_bounds_recent_history(self) -> None:
        history = [
            ChatMessage(role="system", content="private runtime prompt"),
            *[
                ChatMessage(role="user", content=f"old-{index}-" + "x" * 30_000)
                for index in range(5)
            ],
            ChatMessage(
                role="assistant",
                content=[
                    {"type": "image", "source": {"data": "secret-image-bytes"}},
                    {"type": "text", "text": "recent answer"},
                ],
            ),
        ]

        rendered = render_btw_context(history)

        self.assertLessEqual(len(rendered), MAX_BTW_CONTEXT_CHARS)
        self.assertNotIn("private runtime prompt", rendered)
        self.assertNotIn("secret-image-bytes", rendered)
        self.assertIn("[image content omitted]", rendered)
        self.assertIn("recent answer", rendered)
        self.assertIn("[Earlier conversation omitted:", rendered)

    def test_build_btw_messages_rejects_empty_and_oversized_questions(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            build_btw_messages("  ")
        with self.assertRaisesRegex(ValueError, "exceeds"):
            build_btw_messages("x" * (MAX_BTW_QUESTION_CHARS + 1))


if __name__ == "__main__":
    unittest.main()
