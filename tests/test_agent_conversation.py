import unittest

from vibeagent.agent_conversation import continue_conversation, conversation_for_next_prompt
from vibeagent.types import ChatMessage


class AgentConversationTests(unittest.TestCase):
    def test_continue_uses_fresh_system_and_prior_non_system_messages(self) -> None:
        prior = [
            ChatMessage(role="system", content="old system"),
            ChatMessage(role="user", content="User task:\nfirst"),
            ChatMessage(role="assistant", content="first answer"),
        ]
        fresh = [
            ChatMessage(role="system", content="new system"),
            ChatMessage(role="user", content="User task:\nsecond\n\nProject directory:\n/tmp/project"),
        ]

        continued = continue_conversation(prior, fresh)

        self.assertEqual([message.role for message in continued], ["system", "user", "assistant", "user"])
        self.assertEqual(continued[0].content, "new system")
        self.assertNotIn("old system", str(continued))

    def test_carry_compacts_runtime_envelope_but_preserves_tool_exchange(self) -> None:
        tool_results = ChatMessage(
            role="user",
            content=[{"type": "tool_result", "tool_call_id": "read-1", "content": "result"}],
        )
        messages = [
            ChatMessage(role="system", content="system"),
            tool_results,
            ChatMessage(
                role="user",
                content=[
                    {
                        "type": "text",
                        "text": "User task:\nmultiline task\n\nProject directory:\n/tmp/project",
                    },
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "AA=="}},
                ],
            ),
            ChatMessage(role="assistant", content="done"),
        ]

        carried = conversation_for_next_prompt(messages, "multiline task")

        self.assertEqual(carried[0], tool_results)
        self.assertEqual(carried[1], ChatMessage(role="user", content="User task:\nmultiline task"))
        self.assertEqual(carried[2].content, "done")

    def test_carry_leaves_ordinary_user_feedback_unchanged(self) -> None:
        feedback = ChatMessage(role="user", content="Run the failing test again.")
        self.assertEqual(conversation_for_next_prompt([feedback], "task"), [feedback])

    def test_carry_drops_unpaired_trailing_tool_call(self) -> None:
        messages = [
            ChatMessage(role="user", content="User task:\nfinish"),
            ChatMessage(
                role="assistant",
                content=[{"type": "tool_call", "id": "finish-1", "name": "finish", "input": {}}],
            ),
        ]

        self.assertEqual(
            conversation_for_next_prompt(messages, "finish"),
            [ChatMessage(role="user", content="User task:\nfinish")],
        )


if __name__ == "__main__":
    unittest.main()
