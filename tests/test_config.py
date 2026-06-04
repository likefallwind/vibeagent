import unittest

from vibeagent.config import normalize_api_key, resolve_provider_config
from vibeagent.providers import get_model_text


class ConfigTests(unittest.TestCase):
    def test_resolve_provider_config_defaults_to_minimax(self) -> None:
        config = resolve_provider_config({"MINIMAX_API_KEY": "key"})

        self.assertEqual(config.provider, "minimax")
        self.assertEqual(config.model, "MiniMax-M2.7")
        self.assertEqual(config.base_url, "https://api.minimaxi.com/anthropic")
        self.assertEqual(config.api_key, "key")
        self.assertEqual(config.api_key_source, "MINIMAX_API_KEY")

    def test_minimax_key_priority_and_bearer_normalization(self) -> None:
        config = resolve_provider_config(
            {
                "VIBEAGENT_PROVIDER": "minimax",
                "MINIMAX_API_KEY": " Bearer primary ",
                "MINIMAX_API": "alias",
                "minimax_api": "fallback",
            }
        )

        self.assertEqual(config.api_key, "primary")
        self.assertEqual(config.api_key_source, "MINIMAX_API_KEY")
        self.assertEqual(normalize_api_key(" Bearer copied-key "), "copied-key")

    def test_openai_compatible_defaults_and_key_priority(self) -> None:
        config = resolve_provider_config(
            {
                "VIBEAGENT_PROVIDER": "deepseek",
                "OPENAI_COMPAT_API_KEY": "openai-key",
                "DEEPSEEK_API_KEY": "deepseek-key",
            }
        )

        self.assertEqual(config.provider, "deepseek")
        self.assertEqual(config.model, "deepseek-chat")
        self.assertEqual(config.base_url, "https://api.deepseek.com")
        self.assertEqual(config.api_key, "openai-key")
        self.assertEqual(config.api_key_source, "OPENAI_COMPAT_API_KEY")

    def test_openai_compatible_deepseek_fallbacks(self) -> None:
        config = resolve_provider_config(
            {
                "VIBEAGENT_PROVIDER": "openai-compatible",
                "DEEPSEEK_API_KEY": "deepseek-key",
                "DEEPSEEK_MODEL": "deepseek-reasoner",
                "DEEPSEEK_BASE_URL": "https://deepseek.example/",
            }
        )

        self.assertEqual(config.model, "deepseek-reasoner")
        self.assertEqual(config.base_url, "https://deepseek.example")
        self.assertEqual(config.api_key_source, "DEEPSEEK_API_KEY")

    def test_model_text_never_exposes_key_values(self) -> None:
        text = get_model_text(
            {
                "VIBEAGENT_PROVIDER": "deepseek",
                "OPENAI_COMPAT_API_KEY": "secret-value",
                "OPENAI_COMPAT_BASE_URL": "https://api.example",
                "OPENAI_COMPAT_MODEL": "custom-model",
            }
        )

        self.assertIn("Model provider: deepseek", text)
        self.assertIn("model: custom-model", text)
        self.assertIn("baseUrl: https://api.example", text)
        self.assertIn("apiKey: configured via OPENAI_COMPAT_API_KEY", text)
        self.assertNotIn("secret-value", text)

    def test_unsupported_provider_is_clear(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported VIBEAGENT_PROVIDER: unknown"):
            resolve_provider_config({"VIBEAGENT_PROVIDER": "unknown"})

        self.assertEqual(
            get_model_text({"VIBEAGENT_PROVIDER": "unknown"}),
            "Unsupported VIBEAGENT_PROVIDER: unknown",
        )


if __name__ == "__main__":
    unittest.main()
