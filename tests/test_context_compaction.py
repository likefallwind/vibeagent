from __future__ import annotations

import argparse
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from vibeagent.action_parsing import parse_tool_action
from vibeagent.agent_delegate_context import compact_delegate_message_history
from vibeagent.agent_runtime_utils import compact_agent_message_history
from vibeagent.context_compaction import (
    autocompact_char_threshold,
    estimate_message_tokens,
    format_autocompact_setting,
    parse_autocompact_tokens,
    resolve_autocompact_tokens,
)
from vibeagent.types import ChatMessage
from vibeagent.workspace import create_run_workspace


class ContextCompactionTests(unittest.TestCase):
    def test_parser_accepts_claude_compatible_values(self) -> None:
        expected = {
            "auto": 0,
            "100k": 100_000,
            "200": 200_000,
            "200000": 200_000,
            "1m": 1_000_000,
        }

        for value, tokens in expected.items():
            with self.subTest(value=value):
                self.assertEqual(parse_autocompact_tokens(value), tokens)

    def test_parser_rejects_values_outside_supported_range(self) -> None:
        for value in ("99", "99k", "1000001", "2m", "bad"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                parse_autocompact_tokens(value)

    def test_threshold_reserves_output_capacity_and_formats_status(self) -> None:
        self.assertEqual(autocompact_char_threshold(None, 96_000), 96_000)
        self.assertEqual(autocompact_char_threshold(100_000, 96_000), 320_000)
        self.assertEqual(estimate_message_tokens(9), 3)
        self.assertIsNone(resolve_autocompact_tokens(0))
        self.assertEqual(format_autocompact_setting(None), "auto")
        self.assertEqual(format_autocompact_setting(200_000), "200k")
        self.assertEqual(format_autocompact_setting(1_000_000), "1m")

    def test_explicit_threshold_replaces_main_message_count_trigger(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-autocompact-main-") as base:
            workspace = replace(create_run_workspace(Path(base)), autocompact_tokens=100_000)
            messages = [ChatMessage(role="user", content=f"message {index}") for index in range(20)]

            compacted = compact_agent_message_history("inspect", workspace, messages, [], [], None, 1)

        self.assertIs(compacted, messages)

    def test_explicit_threshold_compacts_main_and_delegate_large_histories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-autocompact-large-") as base:
            workspace = replace(create_run_workspace(Path(base)), autocompact_tokens=100_000)
            large_messages = [
                ChatMessage(role="system", content="system"),
                ChatMessage(role="user", content="x" * 330_000),
            ]
            main = compact_agent_message_history("inspect", workspace, large_messages, [], [], None, 1)
            action = parse_tool_action("delegate_task", {"task": "inspect"})
            delegate = compact_delegate_message_history(
                workspace,
                action,
                large_messages,
                [],
                parent_iteration=1,
                child_iteration=1,
                subagent_id="delegate-1-1",
            )

        self.assertLess(len(str(main[1].content)), 330_000)
        self.assertLess(len(str(delegate[1].content)), 330_000)


if __name__ == "__main__":
    unittest.main()
