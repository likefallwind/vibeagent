from __future__ import annotations

import unittest
from types import SimpleNamespace

from vibeagent import prompt_next_action_runtime, prompt_next_action_runtime_network


class PromptNextActionRuntimeNetworkTests(unittest.TestCase):
    def test_runtime_module_reexports_network_instruction_helpers(self) -> None:
        self.assertIs(
            prompt_next_action_runtime._port_check_next_action_instruction,
            prompt_next_action_runtime_network._port_check_next_action_instruction,
        )
        self.assertIs(
            prompt_next_action_runtime._http_check_next_action_instruction,
            prompt_next_action_runtime_network._http_check_next_action_instruction,
        )
        self.assertIs(
            prompt_next_action_runtime._http_fetch_next_action_instruction,
            prompt_next_action_runtime_network._http_fetch_next_action_instruction,
        )
        self.assertIs(
            prompt_next_action_runtime._web_fetch_next_action_instruction,
            prompt_next_action_runtime_network._web_fetch_next_action_instruction,
        )

    def test_runtime_next_action_routes_network_observations(self) -> None:
        base = "Next:"
        port_instruction = prompt_next_action_runtime.runtime_next_action_instruction(
            base,
            [SimpleNamespace(kind="port_check", host="127.0.0.1", port=5173, reachable=True)],
        )
        http_instruction = prompt_next_action_runtime.runtime_next_action_instruction(
            base,
            [SimpleNamespace(kind="http_check", url="http://127.0.0.1:5173", reachable=False)],
        )
        fetch_instruction = prompt_next_action_runtime.runtime_next_action_instruction(
            base,
            [SimpleNamespace(kind="http_fetch", url="http://127.0.0.1:5173", reachable=True, ok=True)],
        )
        web_instruction = prompt_next_action_runtime.runtime_next_action_instruction(
            base,
            [SimpleNamespace(kind="web_fetch", url="https://docs.python.org/3/", ok=False)],
        )

        self.assertIsNotNone(port_instruction)
        self.assertIn("http_check/http_fetch", port_instruction or "")
        self.assertIsNotNone(http_instruction)
        self.assertIn("read_process", http_instruction or "")
        self.assertIsNotNone(fetch_instruction)
        self.assertIn("HTTP fetch succeeded", fetch_instruction or "")
        self.assertIsNotNone(web_instruction)
        self.assertIn("Public document fetch failed", web_instruction or "")


if __name__ == "__main__":
    unittest.main()
