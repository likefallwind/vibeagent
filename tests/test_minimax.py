import os
import unittest

from vibeagent.minimax import (
    MiniMaxApiKeyInfo,
    MiniMaxClient,
    MissingMiniMaxApiKeyError,
    build_request_body,
    extract_content,
    get_minimax_api_key_from_env,
    get_minimax_api_key_info_from_env,
    get_minimax_defaults,
)
from vibeagent.types import ChatMessage


class MiniMaxTests(unittest.TestCase):
    def test_get_minimax_api_key_from_env_reads_supported_variables_in_priority_order(self) -> None:
        self.assertEqual(
            get_minimax_api_key_from_env(
                {
                    "MINIMAX_API_KEY": "primary-key",
                    "MINIMAX_API": "alias-key",
                    "minimax_api": "fallback-key",
                }
            ),
            "primary-key",
        )
        self.assertEqual(get_minimax_api_key_from_env({"MINIMAX_API": "alias-key"}), "alias-key")
        self.assertEqual(get_minimax_api_key_from_env({"minimax_api": "fallback-key"}), "fallback-key")

    def test_get_minimax_api_key_from_env_ignores_empty_values(self) -> None:
        self.assertEqual(
            get_minimax_api_key_from_env(
                {
                    "MINIMAX_API_KEY": " ",
                    "MINIMAX_API": "",
                    "minimax_api": "fallback-key",
                }
            ),
            "fallback-key",
        )

    def test_get_minimax_api_key_from_env_normalizes_copied_bearer_tokens(self) -> None:
        self.assertEqual(get_minimax_api_key_from_env({"MINIMAX_API_KEY": " Bearer actual-key "}), "actual-key")
        self.assertEqual(
            get_minimax_api_key_info_from_env({"MINIMAX_API": " alias-key "}),
            MiniMaxApiKeyInfo(name="MINIMAX_API", value="alias-key"),
        )

    def test_minimax_client_throws_when_no_api_key_is_provided(self) -> None:
        original = {
            "MINIMAX_API_KEY": os.environ.get("MINIMAX_API_KEY"),
            "MINIMAX_API": os.environ.get("MINIMAX_API"),
            "minimax_api": os.environ.get("minimax_api"),
        }
        for name in original:
            os.environ.pop(name, None)

        try:
            with self.assertRaises(MissingMiniMaxApiKeyError):
                MiniMaxClient()
        finally:
            for name, value in original.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def test_get_minimax_defaults_uses_official_anthropic_compatible_url(self) -> None:
        self.assertEqual(get_minimax_defaults({})["base_url"], "https://api.minimaxi.com/anthropic")

    def test_build_request_body_uses_anthropic_messages_shape(self) -> None:
        body = build_request_body(
            "MiniMax-M2.7",
            [
                ChatMessage(role="system", content="You are concise."),
                ChatMessage(role="user", content="Hi"),
            ],
        )

        self.assertEqual(body["model"], "MiniMax-M2.7")
        self.assertEqual(body["system"], "You are concise.")
        self.assertEqual(body["max_tokens"], 4096)
        self.assertEqual(body["messages"], [{"role": "user", "content": "Hi"}])

    def test_extract_content_reads_anthropic_text_blocks(self) -> None:
        self.assertEqual(
            extract_content(
                {
                    "content": [
                        {"type": "text", "text": "hello"},
                        {"type": "thinking", "thinking": "..."},
                        {"type": "text", "text": " world"},
                    ]
                }
            ),
            "hello world",
        )


if __name__ == "__main__":
    unittest.main()
