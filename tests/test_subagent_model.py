from __future__ import annotations

import unittest

from vibeagent.subagent_model import resolve_subagent_model


class SubagentModelTests(unittest.TestCase):
    def test_resolves_parent_environment_and_native_precedence(self) -> None:
        self.assertEqual(resolve_subagent_model(None, {}).source, "parent")
        compatible = resolve_subagent_model(
            None,
            {"CLAUDE_CODE_SUBAGENT_MODEL": "claude-haiku"},
        )
        native = resolve_subagent_model(
            None,
            {
                "VIBEAGENT_SUBAGENT_MODEL": "native-model",
                "CLAUDE_CODE_SUBAGENT_MODEL": "claude-haiku",
            },
        )

        self.assertEqual(compatible.model, "claude-haiku")
        self.assertEqual(compatible.source, "CLAUDE_CODE_SUBAGENT_MODEL")
        self.assertEqual(native.model, "native-model")
        self.assertEqual(native.source, "VIBEAGENT_SUBAGENT_MODEL")

    def test_profile_model_and_inherit_override_environment(self) -> None:
        environment = {"CLAUDE_CODE_SUBAGENT_MODEL": "environment-model"}

        explicit = resolve_subagent_model("profile-model", environment)
        inherited = resolve_subagent_model("inherit", environment)

        self.assertEqual(explicit.model, "profile-model")
        self.assertEqual(explicit.source, "profile")
        self.assertIsNone(inherited.model)
        self.assertEqual(inherited.source, "profile")

    def test_rejects_invalid_environment_model(self) -> None:
        for value in ("bad model", "../model", "x" * 129):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "valid model ID"):
                    resolve_subagent_model(
                        None,
                        {"CLAUDE_CODE_SUBAGENT_MODEL": value},
                    )


if __name__ == "__main__":
    unittest.main()
