from __future__ import annotations

import unittest

from vibeagent.cli_one_shot_chat import run_one_shot_chat
from vibeagent.config import ExecutionConfig


class CliOneShotChatTests(unittest.TestCase):
    def test_run_one_shot_chat_creates_client_runs_chat_and_emits_payload(self) -> None:
        provider_env: dict[str, str | None] = {"VIBEAGENT_PROVIDER": "minimax"}
        emitted: list[dict[str, object]] = []
        clients: list[dict[str, str | None]] = []
        chat_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        def create_client(env: dict[str, str | None]) -> object:
            clients.append(env)
            return "client"

        def run_chat(*args, **kwargs) -> str:
            chat_calls.append((args, kwargs))
            return "hello"

        class Stream:
            def result(self, value):
                emitted.append(value)

        exit_code = run_one_shot_chat(
            "explain repo",
            provider_env=provider_env,
            execution_config=ExecutionConfig(
                max_iterations=9,
                command_timeout_ms=100,
                max_output_tokens=2048,
                model_retries=2,
                model_retry_delay_ms=50,
                model_timeout_ms=30000,
            ),
            system_prompt="You are terse.",
            append_system_prompt="Prefer bullets.",
            machine_output=True,
            output_json=False,
            elapsed_ms=123,
            stream=Stream(),
            create_chat_client_func=create_client,
            run_chat_func=run_chat,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(clients, [provider_env])
        self.assertEqual(chat_calls[0][0], ("explain repo",))
        self.assertEqual(
            chat_calls[0][1],
            {
                "client": "client",
                "history": [],
                "max_output_tokens": 2048,
                "model_retries": 2,
                "model_retry_delay_ms": 50,
                "model_timeout_ms": 30000,
                "system_prompt": "You are terse.",
                "append_system_prompt": "Prefer bullets.",
            },
        )
        self.assertEqual(emitted[0]["kind"], "chat")
        self.assertEqual(emitted[0]["message"], "hello")
        self.assertEqual(emitted[0]["durationMs"], 123)
        self.assertEqual(emitted[0]["numTurns"], 1)


if __name__ == "__main__":
    unittest.main()
