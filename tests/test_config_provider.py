import unittest

from vibeagent import config
from vibeagent import config_provider


class ConfigProviderTests(unittest.TestCase):
    def test_config_reexports_provider_helpers(self) -> None:
        names = [
            "MINIMAX_PROVIDER",
            "ANTHROPIC_PROVIDER",
            "OPENAI_COMPATIBLE_PROVIDERS",
            "ApiKeyInfo",
            "ProviderConfig",
            "resolve_provider_config",
            "get_provider_name",
            "get_first_api_key",
            "normalize_api_key",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(config, name), getattr(config_provider, name))

    def test_provider_helpers_keep_existing_behavior(self) -> None:
        self.assertEqual(config_provider.get_provider_name({}), "minimax")
        self.assertEqual(config_provider.normalize_api_key(" Bearer copied-key "), "copied-key")
        key = config_provider.get_first_api_key(
            {"MINIMAX_API_KEY": "", "MINIMAX_API": " alias-key "},
            ("MINIMAX_API_KEY", "MINIMAX_API"),
        )
        self.assertEqual(key, config_provider.ApiKeyInfo(name="MINIMAX_API", value="alias-key"))

        provider = config_provider.resolve_provider_config(
            {
                "VIBEAGENT_PROVIDER": "deepseek",
                "OPENAI_COMPAT_API_KEY": "key",
                "VIBEAGENT_MODEL": "model",
                "VIBEAGENT_BASE_URL": "https://example.test/",
            }
        )
        self.assertEqual(provider.provider, "deepseek")
        self.assertEqual(provider.model, "model")
        self.assertEqual(provider.base_url, "https://example.test")
        self.assertEqual(provider.api_key, "key")

        anthropic = config_provider.resolve_provider_config(
            {"VIBEAGENT_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "claude-key"}
        )
        self.assertEqual(anthropic.model, "claude-sonnet-5")
        self.assertEqual(anthropic.base_url, "https://api.anthropic.com")
        self.assertEqual(anthropic.api_key_source, "ANTHROPIC_API_KEY")


if __name__ == "__main__":
    unittest.main()
