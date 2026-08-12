import unittest
import argparse
import tempfile
from pathlib import Path
from unittest.mock import patch

from vibeagent.anthropic import AnthropicClient, MissingAnthropicApiKeyError
from vibeagent.cli_config import build_provider_env
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

    def test_create_chat_client_builds_anthropic_client_from_env_mapping(self) -> None:
        client = create_chat_client(
            {
                "VIBEAGENT_PROVIDER": "anthropic",
                "ANTHROPIC_AUTH_TOKEN": "gateway-token",
                "ANTHROPIC_MODEL": "claude-sonnet-4-6",
                "ANTHROPIC_BASE_URL": "https://gateway.example/anthropic/",
            }
        )

        self.assertIsInstance(client, AnthropicClient)
        self.assertEqual(client.model, "claude-sonnet-4-6")
        self.assertEqual(client.base_url, "https://gateway.example/anthropic")
        self.assertTrue(client.use_auth_token)

    def test_anthropic_provider_requires_a_key(self) -> None:
        with self.assertRaises(MissingAnthropicApiKeyError):
            create_chat_client({"VIBEAGENT_PROVIDER": "anthropic"})

    def test_anthropic_beta_headers_require_api_key_authentication(self) -> None:
        client = create_chat_client(
            {
                "VIBEAGENT_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "api-key",
                "ANTHROPIC_BETA": "interleaved-thinking,files-api-2025-04-14",
            }
        )

        self.assertEqual(
            client.betas,
            ("interleaved-thinking", "files-api-2025-04-14"),
        )
        with self.assertRaisesRegex(ValueError, "API_KEY"):
            create_chat_client(
                {
                    "VIBEAGENT_PROVIDER": "anthropic",
                    "ANTHROPIC_AUTH_TOKEN": "oauth-token",
                    "ANTHROPIC_BETA": "interleaved-thinking",
                }
            )

    def test_cli_overrides_route_to_anthropic_environment(self) -> None:
        args = argparse.Namespace(
            provider="anthropic",
            model="claude-sonnet-4-6",
            model_name=None,
            base_url="https://gateway.example/anthropic",
            api_key="temporary-key",
            betas=["interleaved-thinking", "files-api-2025-04-14"],
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-anthropic-") as base, patch.dict("os.environ", {}, clear=True):
            env = build_provider_env(args, Path(base))

        self.assertEqual(env["VIBEAGENT_PROVIDER"], "anthropic")
        self.assertEqual(env["ANTHROPIC_MODEL"], "claude-sonnet-4-6")
        self.assertEqual(env["ANTHROPIC_BASE_URL"], "https://gateway.example/anthropic")
        self.assertEqual(env["ANTHROPIC_API_KEY"], "temporary-key")
        self.assertEqual(
            env["ANTHROPIC_BETA"],
            "interleaved-thinking,files-api-2025-04-14",
        )
        self.assertNotIn("OPENAI_COMPAT_API_KEY", env)

    def test_cli_beta_headers_reject_non_anthropic_provider(self) -> None:
        args = argparse.Namespace(
            provider="minimax",
            model=None,
            model_name=None,
            base_url=None,
            api_key=None,
            betas=["interleaved-thinking"],
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-betas-") as base:
            with self.assertRaisesRegex(ValueError, "only with --provider anthropic"):
                build_provider_env(args, Path(base))


if __name__ == "__main__":
    unittest.main()
