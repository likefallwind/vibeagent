from __future__ import annotations

import unittest

from vibeagent.types import AssistantResponse

from vibeagent.model_effort import (
    EnvironmentEffortChatClient,
    ModelEffortSetting,
    configure_model_effort,
    resolve_model_effort_setting,
)


class ProfileClient:
    def __init__(self, model: str = "base", effort: str | None = None) -> None:
        self.model = model
        self.effort = effort

    def complete(self, *args, **kwargs):
        return AssistantResponse(content=[{"type": "text", "text": "done"}], raw={})

    def complete_stream(self, *args, on_event, **kwargs):
        on_event({"type": "message_stop"})
        return self.complete(*args, **kwargs)

    def with_agent_profile(self, *, model: str | None, effort: str | None) -> ProfileClient:
        return ProfileClient(model or self.model, self.effort if effort is None else effort)


class ModelEffortTests(unittest.TestCase):
    def test_locked_effort_wrapper_preserves_streaming(self) -> None:
        configured = configure_model_effort(
            ProfileClient(),
            ModelEffortSetting("high", locked=True),
        )
        events = []

        response = configured.complete_stream([], on_event=events.append)

        self.assertEqual(response.content[0]["text"], "done")
        self.assertEqual(events, [{"type": "message_stop"}])

    def test_environment_takes_precedence_and_locks_setting(self) -> None:
        setting = resolve_model_effort_setting(
            "low",
            {"CLAUDE_CODE_EFFORT_LEVEL": " HIGH "},
        )

        self.assertEqual(setting, ModelEffortSetting("high", locked=True))

    def test_invalid_environment_value_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "CLAUDE_CODE_EFFORT_LEVEL"):
            resolve_model_effort_setting(
                None,
                {"CLAUDE_CODE_EFFORT_LEVEL": "ultracode"},
            )

    def test_environment_setting_cannot_be_overridden_by_agent_profile(self) -> None:
        configured = configure_model_effort(
            ProfileClient(),
            ModelEffortSetting("high", locked=True),
        )
        profiled = configured.with_agent_profile(model="profile", effort="low")

        self.assertIsInstance(profiled, EnvironmentEffortChatClient)
        self.assertEqual(profiled.client.model, "profile")
        self.assertEqual(profiled.client.effort, "high")


if __name__ == "__main__":
    unittest.main()
