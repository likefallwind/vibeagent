import unittest

from vibeagent.minimax import MiniMaxClient
from vibeagent.openai_compat import OpenAICompatibleClient
from vibeagent.providers import create_chat_client, get_provider_name


class ProviderTests(unittest.TestCase):
    def test_get_provider_name_defaults_to_minimax(self) -> None:
        self.assertEqual(get_provider_name({}), "minimax")

    def test_create_chat_client_builds_minimax_client_from_env_mapping(self) -> None:
        client = create_chat_client(
            {
                "VIBEAGENT_PROVIDER": "minimax",
                "MINIMAX_API_KEY": "minimax-key",
                "MINIMAX_MODEL": "model-a",
                "MINIMAX_BASE_URL": "https://minimax.example",
            }
        )

        self.assertIsInstance(client, MiniMaxClient)
        self.assertEqual(client.model, "model-a")
        self.assertEqual(client.base_url, "https://minimax.example")

    def test_create_chat_client_builds_deepseek_client_from_env_mapping(self) -> None:
        client = create_chat_client(
            {
                "VIBEAGENT_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "deepseek-key",
                "DEEPSEEK_MODEL": "deepseek-reasoner",
                "DEEPSEEK_BASE_URL": "https://deepseek.example",
            }
        )

        self.assertIsInstance(client, OpenAICompatibleClient)
        self.assertEqual(client.model, "deepseek-reasoner")
        self.assertEqual(client.base_url, "https://deepseek.example")


if __name__ == "__main__":
    unittest.main()
