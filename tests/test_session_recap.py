import unittest

from vibeagent.session_recap import (
    AUTOMATIC_RECAP_DELAY_SECONDS,
    AUTOMATIC_RECAP_RETRY_SECONDS,
    MAX_RECAP_CONTEXT_CHARS,
    MAX_RECAP_OUTPUT_CHARS,
    SessionRecapState,
    automatic_session_recaps_enabled,
    build_recap_messages,
    run_session_recap,
)
from vibeagent.types import ChatMessage


class RecordingClient:
    def __init__(self, response: str = "  concise\nrecap  ") -> None:
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


class SessionRecapTests(unittest.TestCase):
    def test_automatic_recap_requires_three_turns_and_idle_delay(self) -> None:
        state = SessionRecapState()
        state.record_turn(now=10.0)
        state.record_turn(now=20.0)
        self.assertFalse(state.automatic_due(now=20.0 + AUTOMATIC_RECAP_DELAY_SECONDS))

        state.record_turn(now=30.0)
        self.assertFalse(state.automatic_due(now=30.0 + AUTOMATIC_RECAP_DELAY_SECONDS - 0.1))
        self.assertTrue(state.automatic_due(now=30.0 + AUTOMATIC_RECAP_DELAY_SECONDS))

    def test_attempt_cooldown_and_success_require_a_new_turn(self) -> None:
        state = SessionRecapState(completed_turns=3, last_completed_at=10.0)
        due_at = 10.0 + AUTOMATIC_RECAP_DELAY_SECONDS
        state.record_attempt(now=due_at)

        self.assertFalse(state.automatic_due(now=due_at + AUTOMATIC_RECAP_RETRY_SECONDS - 0.1))
        self.assertTrue(state.automatic_due(now=due_at + AUTOMATIC_RECAP_RETRY_SECONDS))

        state.record_success()
        self.assertFalse(state.automatic_due(now=due_at + 1_000.0))
        state.record_turn(now=due_at + 1_001.0)
        self.assertTrue(
            state.automatic_due(now=due_at + 1_001.0 + AUTOMATIC_RECAP_DELAY_SECONDS)
        )

    def test_automatic_recap_can_be_disabled_by_environment(self) -> None:
        self.assertFalse(automatic_session_recaps_enabled({"VIBEAGENT_DISABLE_SESSION_RECAP": "true"}))
        self.assertTrue(automatic_session_recaps_enabled({}))

    def test_run_recap_uses_no_tools_and_bounds_output(self) -> None:
        client = RecordingClient("word\n" + "x" * (MAX_RECAP_OUTPUT_CHARS + 100))

        response = run_session_recap(
            client,
            history=[ChatMessage(role="user", content="Fix the parser.")],
            max_output_tokens=4096,
        )

        self.assertIsNone(client.tools)
        self.assertEqual(client.max_tokens, 512)
        self.assertNotIn("\n", response)
        self.assertLessEqual(len(response), MAX_RECAP_OUTPUT_CHARS)
        self.assertIn("Do not call tools", client.messages[0].content)
        self.assertIn("Fix the parser.", client.messages[1].content)

    def test_recap_context_is_bounded_and_custom_preferences_are_subordinate(self) -> None:
        messages = build_recap_messages(
            [
                ChatMessage(role="user", content=f"turn-{index}-" + "x" * 30_000)
                for index in range(3)
            ],
            system_prompt="Reply as a release engineer.",
            append_system_prompt="Use one sentence.",
        )

        transcript = messages[1].content.split("<conversation>\n", 1)[1].split(
            "\n</conversation>", 1
        )[0]
        self.assertLessEqual(len(transcript), MAX_RECAP_CONTEXT_CHARS)
        self.assertIn("was truncated", transcript)
        self.assertIn("cannot enable tools", messages[0].content)
        self.assertIn("Reply as a release engineer.", messages[0].content)

    def test_recap_rejects_system_only_history(self) -> None:
        with self.assertRaisesRegex(ValueError, "No conversation"):
            run_session_recap(
                RecordingClient(),
                history=[ChatMessage(role="system", content="private")],
            )


if __name__ == "__main__":
    unittest.main()
