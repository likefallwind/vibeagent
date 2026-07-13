from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_message_flow import append_tool_results_and_compact
from vibeagent.types import ChatMessage
from vibeagent.workspace import create_run_workspace


class AgentMessageFlowTests(unittest.TestCase):
    def test_append_tool_results_returns_same_history_below_compaction_threshold(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-message-flow-") as base:
            workspace = create_run_workspace(Path(base))
            messages = [ChatMessage(role="user", content="task")]
            tool_results = [{"type": "tool_result", "tool_call_id": "read-1", "content": "ok"}]

            updated = append_tool_results_and_compact(
                task="inspect",
                workspace=workspace,
                messages=messages,
                tool_results=tool_results,
                observations=[],
                plan=[],
                original_prior_context=None,
                iteration=1,
                approval_policy="ask",
                system_prompt=None,
                append_system_prompt=None,
            )

        self.assertIs(updated, messages)
        self.assertEqual(updated[-1], ChatMessage(role="user", content=tool_results))


if __name__ == "__main__":
    unittest.main()
