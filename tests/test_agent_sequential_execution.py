from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent.agent import run_agent
from vibeagent.types import AssistantResponse, ChatMessage, ContentBlock


class MockClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.index = 0
        self.messages: list[list[ChatMessage]] = []

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_ms: int = 120_000,
    ) -> AssistantResponse:
        self.messages.append(list(messages))
        response = self.responses[self.index]
        self.index += 1
        return AssistantResponse(content=response, raw={"content": response})


class AgentSequentialExecutionTests(unittest.TestCase):
    def test_run_agent_updates_plan_through_sequential_tool_execution(self) -> None:
        client = MockClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "plan-1",
                        "name": "update_plan",
                        "input": {
                            "plan": [
                                {"step": "inspect", "status": "completed"},
                                {"step": "edit", "status": "in_progress"},
                            ],
                        },
                    }
                ],
                [{"type": "tool_call", "id": "finish-1", "name": "finish", "input": {"message": "done"}}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-sequential-") as base:
            result = run_agent("update plan", client=client, base_dir=Path(base), max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.message, "done")
        self.assertEqual([(item.step, item.status) for item in result.plan], [("inspect", "completed"), ("edit", "in_progress")])
        self.assertEqual([observation.kind for observation in result.observations], ["update_plan", "finish"])


if __name__ == "__main__":
    unittest.main()
